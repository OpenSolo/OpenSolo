#include "flightmanager.h"
#include "buttonmanager.h"
#include "lockout.h"
#include "manualoverride.h"
#include "haptic.h"
#include "ui.h"
#include "mavlink.h"
#include "sologimbal.h"

const FlightManager::BatteryState FlightManager::batteryStates[] = {
    { BatteryNormal, Event::None, BatteryLevelLow, BatteryLevelMax},
    { BatteryLow, Event::FlightBatteryLow, BatteryLevelCritical, BatteryLevelLowDismiss},
    { BatteryCritical, Event::FlightBatteryCritical, BatteryLevelFailsafe, BatteryLevelCritical + BatteryLevelDismissBuffer},
    { BatteryFailsafe, Event::FlightBatteryFailsafe, BatteryLevelMin, BatteryLevelFailsafe + BatteryLevelDismissBuffer},
};

const uint8_t FlightManager::numBattStates = arraysize(FlightManager::batteryStates);

FlightManager FlightManager::instance;

FlightManager::FlightManager() :
    mode(STABILIZE),
    systemStatus(MAV_STATE_UNINIT),
    armState(Disarmed),
    modeArmableStatus(0),
    takeoffState(TakeoffNone),
    statusTxt(),
    linkConnCounter(LINK_CONN_DURATION),
    command(),
    telemetryVals(),
    currentLoc(),
    home(),
    goodConnectionToSolo(true),
    flagRCFailsafe(false),
    pendingEkfFlags(Telemetry::EKF_UNINIT),
    currentBatteryPhase(BatteryNormal)
{
}

void FlightManager::init()
{
    command.state = Command::Complete;
    telemetryVals.clear();
}

const char *FlightManager::flightModeStr(FlightMode m)
{
    switch (m) {
    case STABILIZE: return "Stabilize";
    case ACRO:      return "Acro";
    case ALT_HOLD:  return "Alt Hold";
    case AUTO:      return "Auto";
    case GUIDED:    return "Guided";
    case LOITER:    return "Loiter";
    case RTL:       return "Return to Home";
    case CIRCLE:    return "Circle";
    case LAND:      return "Land";
    case OF_LOITER: return "OF Loiter";
    case DRIFT:     return "Drift";
    case SPORT:     return "Sport";
    case FLIP:      return "Flip";
    case AUTOTUNE:  return "Auto Tune";
    case POSHOLD:   return "Pos Hold";
    default:        return "Unknown";
    }
}

void FlightManager::sysHeartbeat()
{
    /*
     * called from heartbeat task.
     * Do any work that requires periodic attention.
     */

    if (linkIsConnected()) {
        if (++linkConnCounter >= LINK_CONN_DURATION) {
            linkDisconnected();
        }
    }
}

void FlightManager::linkConnected()
{
    /*
     * for now, skip straight to 'InFlight' mode,
     * so we show telemetry data as soon as we're connected.
     * eventually, we may kick off the param check sequence here.
     */

    command.state = Command::Complete;
    Ui::instance.pendEvent(Event::VehicleConnectionChanged);
}

void FlightManager::linkDisconnected()
{
    Ui::instance.alertManager.dismiss(); // TODO: a bit heavy handed, could categorize alerts (e.g. dismissed by vehicle) and check whether alert needs to be dismissed
    Ui::instance.pendEvent(Event::VehicleConnectionChanged);

    if (inFlight()) {
        flagRCFailsafe = true;
        if (telemetryVals.hasGpsFix()) {
            Ui::instance.pendEvent(Event::RCFailsafe);
        } else {
            Ui::instance.pendEvent(Event::RCFailsafeNoGPS);
        }
    }

    takeoffState = TakeoffNone;
    systemStatus = MAV_STATE_UNINIT;
    pendingEkfFlags = Telemetry::EKF_UNINIT;
    telemetryVals.clear();

    ButtonManager::button(Io::ButtonLoiter).setLedInactive();
    ButtonManager::button(Io::ButtonFly).setLedInactive();
    ButtonManager::button(Io::ButtonRTL).setLedInactive();
}

void FlightManager::resetLinkConnCount(const mavlink_message_t * msg)
{
    /*
     * Any mavlink msg resets the link count if we're already connected.
     * Otherwise, we require a heartbeat to re-establish connection - this
     * helps ensure we have up to date state info about critical fields like
     * arm state, flight mode, system status, and ekf flags.
     */

    if (linkIsConnected()) {
        linkConnCounter = 0;
    } else {
        if (msg->msgid == MAVLINK_MSG_ID_HEARTBEAT) {
            linkConnected();
            linkConnCounter = 0;
        }
    }

}

void FlightManager::updateRCFailsafeState(uint8_t sysStatus)
{
    // don't need to do anything if we're not in RCFailsafe state
    if (!flagRCFailsafe) {
        return;
    }

    flagRCFailsafe = false;

    // if the vehicle is still in the air, prompt user to be ready to take control // TODO: Hack: do this only when in RTL or LAND mode since there's currently some discrepancy with what triggers an RC failsafe state
    if (inFlight(sysStatus) && (flightMode() == RTL || flightMode() == LAND)) {
        Ui::instance.pendEvent(Event::RCFailsafeRecovery);
    }
}

bool FlightManager::producePacket(HostProtocol::Packet &p)
{
    /*
     * Our opportunity to send a message via the host.
     */

    if (command.state == Command::Pending) {
        mavlink_message_t msg;
        sendCmd(&msg);
        Mavlink::packetizeMsg(p, &msg);
        command.state = Command::Sent;
        return true;
    }

    return false;
}

void FlightManager::requestFlightModeChange(FlightMode m)
{
    /*
     * helper to request flight mode change
     */

    if (mode != m) {
        command.flightMode = m;
        command.set(Command::SetFlightMode);
    }
}

void FlightManager::requestArmStateChange(ArmState as)
{
    if (armState != as) {
        command.arm = as;
        command.set(Command::SetArmState);
    }
}

void FlightManager::requestHomeWaypoint()
{
    /*
     * The vehicle's first waypoint represents its
     * home position, which we use for calculating
     * distance from home.
     */

    command.waypoint = 0;
    command.set(Command::GetHomeWaypoint);
}

void FlightManager::onFlyButtonEvt(Button *b, Button::Event evt)
{
    UNUSED(b);

    if (!Lockout::isUnlocked()) {
        return;
    }

    if (!linkIsConnected()) {
        return;
    }

    // battery too low to try to fly?
    if (!inFlight() && telemetryVals.battLevel < BatteryLevelCritical) {
        return;
    }

    switch (evt) {
    case Button::Hold:
        command.set(Command::FlyButtonHold);
        Haptic::startPattern(Haptic::SingleShort);
        break;

    case Button::ClickRelease:
        // if we're on the ground and not yet armed,
        // FLY button click puts us into FLY (Loiter) mode
        command.set(Command::FlyButtonClick);
        Haptic::startPattern(Haptic::SingleShort);
        break;

    default:
        break;
    }
}

void FlightManager::onRtlButtonEvt(Button *b, Button::Event evt)
{
    UNUSED(b);

    if (!Lockout::isUnlocked()) {
        return;
    }

    if (!linkIsConnected()) {
        return;
    }

    if (evt == Button::Press) {
        if (inFlight()) {
            // request RTL whether we think vehicle has GPS or not.
            // if our sense of vehicle GPS state is stale, we still
            // want to trigger an RTL if at all possible.
            //
            // if we have confidence that our copy of vehicle state is current,
            // we could trigger Event::RTLWithoutGPS to inform user
            // RTL without GPS is not possible.
            requestFlightModeChange(RTL);

            if (!telemetryVals.hasGpsFix()) {
                Ui::instance.pendEvent(Event::RTLWithoutGPS);
            }

            Haptic::startPattern(Haptic::SingleMedium);
        }
    }
}

void FlightManager::onAButtonEvt(Button *b, Button::Event e)
{
    UNUSED(b);

    if (!linkIsConnected()) {
        return;
    }

    if (btnEventShouldForceDisarm(b, e)) {
        forceDisarm();
        return;
    }

    if (e == Button::ClickRelease) {
        if (ManualOverride::isEnabled()) {
            requestFlightModeChange(ALT_HOLD);
        }
    }
}

void FlightManager::onBButtonEvt(Button *b, Button::Event e)
{
    if (btnEventShouldForceDisarm(b, e)) {
        forceDisarm();
        return;
    }
}

void FlightManager::onPowerButtonEvt(Button *b, Button::Event e)
{
    UNUSED(b);
    UNUSED(e);
}

void FlightManager::onPauseButtonEvt(Button *b, Button::Event e)
{
    if (btnEventShouldForceDisarm(b, e)) {
        forceDisarm();
        return;
    }
}

bool FlightManager::btnEventShouldForceDisarm(Button *b, Button::Event e) const
{
    /*
     * Force disarm will kill the motors and disarm the vehicle,
     * even when armed and/or in the air.
     */

    UNUSED(b);

    if (!armed()) {
        return false;
    }

    if (e == Button::Hold) {
        if (ButtonManager::button(Io::ButtonA).isHeld() &&
            ButtonManager::button(Io::ButtonB).isHeld() &&
            ButtonManager::button(Io::ButtonLoiter).isHeld())
        {
            return true;
        }
    }

    return false;
}

void FlightManager::forceDisarm()
{
    /*
     * Request a force disarm (this will drop the vehicle from the air),
     * and alert the user via haptic.
     */

    requestArmStateChange(DisarmForce);
    Haptic::startPattern(Haptic::SingleLong);
}

void FlightManager::beginTakeoff()
{
    /*
     * We want to takeoff in Loiter - if not already there, change flight modes.
     * Otherwise, send the takeoff command to begin ascending.
     */

    if (mode == LOITER) {
        takeoffState = TakeoffSentTakeoffCmd;
        command.set(Command::Takeoff);
    } else {
        takeoffState = TakeoffSetMode;
        requestFlightModeChange(LOITER);
    }
}

void FlightManager::onPixhawkMavlinkMsg(const mavlink_message_t * msg)
{
    // any mavlink msg from pixhawk keeps our link alive
    resetLinkConnCount(msg);

    onSoloMavlinkMsg(msg);
}

void FlightManager::onSoloMavlinkMsg(const mavlink_message_t * msg)
{
    /*
     * Handle a complete msg that has been received from Solo
     */

    switch (msg->msgid) {
    case MAVLINK_MSG_ID_HEARTBEAT:
        ArmState vehicleArmState;
        FlightMode vehicleFlightMode;
        mavlink_heartbeat_t heartbeat;

        mavlink_msg_heartbeat_decode(msg, &heartbeat);

        vehicleArmState = (heartbeat.base_mode & MAV_MODE_FLAG_SAFETY_ARMED) ? Armed : Disarmed;
        if (vehicleArmState != armState) {
            onArmStateChanged(vehicleArmState);
            armState = vehicleArmState;
        }

        vehicleFlightMode = static_cast<FlightMode>(heartbeat.custom_mode);
        if (vehicleFlightMode != mode) {
            onFlightModeChanged(vehicleFlightMode);
            mode = vehicleFlightMode;
        }

        if (heartbeat.system_status != systemStatus) {
            onSystemStatusChanged(heartbeat.system_status);
            systemStatus = heartbeat.system_status;
        }

        // see comment in MAVLINK_MSG_ID_EKF_STATUS_REPORT handling
        if (telemetryVals.ekfFlags != pendingEkfFlags) {
            onEkfChanged(pendingEkfFlags);
            telemetryVals.ekfFlags = pendingEkfFlags;
        }
        break;

    case MAVLINK_MSG_ID_GLOBAL_POSITION_INT: {
        Coord2D c;
        mavlink_global_position_int_t global_pos;
        mavlink_msg_global_position_int_decode(msg, &global_pos);
        // lat and long are degrees * 1E7, so convert back
        c.set(global_pos.lat / 1e7, global_pos.lon / 1e7);
        onGpsPositionChanged(c);
        currentLoc.set(c.lat(), c.lng());
    } break;

    case MAVLINK_MSG_ID_GPS_RAW_INT:
        mavlink_gps_raw_int_t gps_raw_int;
        mavlink_msg_gps_raw_int_decode(msg, &gps_raw_int);
        if (telemetryVals.gpsFix != gps_raw_int.fix_type) {
            onGpsFixChanged(gps_raw_int.fix_type);
            telemetryVals.gpsFix = gps_raw_int.fix_type;
        }

        if (telemetryVals.numSatellites != gps_raw_int.satellites_visible) {
            onGpsNumSatellitesChanged(gps_raw_int.satellites_visible);
            telemetryVals.numSatellites  = gps_raw_int.satellites_visible;
        }
        break;

    case MAVLINK_MSG_ID_VFR_HUD:
        mavlink_vfr_hud_t vfr_hud;
        mavlink_msg_vfr_hud_decode(msg, &vfr_hud);

        /*
         * When taking off, we want to switch to Loiter
         * once we've reached the desired altitude.
         */
        if (takeoffState == TakeoffAscending) {
            if (vfr_hud.alt >= (TakeoffAltitude - 0.2)) {
                takeoffState = TakeoffComplete;
                // we don't actually do much of anything here for now...
                // but presumably at some point we can signal to the user
                // that the system is ready for them to start flying.
            }
        }

        if (!isWithin(telemetryVals.altitude, vfr_hud.alt, 0.1)) {
            onAltitudeChanged(vfr_hud.alt);
            telemetryVals.altitude = vfr_hud.alt;
        }
        telemetryVals.airSpeed = vfr_hud.airspeed;
        telemetryVals.groundSpeed = vfr_hud.groundspeed;
        break;

    case MAVLINK_MSG_ID_SYS_STATUS:
        int8_t battLevel;
        battLevel = mavlink_msg_sys_status_get_battery_remaining(msg);

        if (telemetryVals.battLevel != battLevel) {
            onBatteryChanged(battLevel);
            telemetryVals.battLevel = battLevel;
        }
        break;

    case MAVLINK_MSG_ID_COMMAND_ACK:
        mavlink_command_ack_t ack;
        mavlink_msg_command_ack_decode(msg, &ack);
        if (ack.command == command.id) {
            command.state = Command::Complete;   // completion handlers may update this
        }
        cmdAcknowledged(&ack);
        break;

    case MAVLINK_MSG_ID_STATUSTEXT:
        mavlink_msg_statustext_decode(msg, &statusTxt.mav);
        statusTxt.rxtime = SysTime::now();
        onStatusTextChanged();
        break;

    // 1-3 Hz arm state update, constant rate depending on current flight code
    case MAVLINK_MSG_ID_NAMED_VALUE_INT:{
        mavlink_named_value_int_t namedVal;
        const char * const maskName = "ARMMASK";

        mavlink_msg_named_value_int_decode(msg, &namedVal);
        if (strncmp(namedVal.name, maskName, strlen(maskName)) == 0) { // make sure we have the right message type
            if (modeArmableStatus != namedVal.value) {                 // check to see if status has changed
                onArmableStatusChanged(namedVal.value);
            }
        }
        }break;

    case MAVLINK_MSG_ID_MOUNT_STATUS:
        mavlink_mount_status_t mountStatus;
        mavlink_msg_mount_status_decode(msg, &mountStatus);
        SoloGimbal::instance.onMountStatus(mountStatus);
        break;

    case MAVLINK_MSG_ID_RADIO_STATUS:
        int8_t signedRssi;
        mavlink_radio_status_t radioStatus;
        mavlink_msg_radio_status_decode(msg, &radioStatus);

        /*
         * The mavlink message packs rssi as a uint8_t
         * but SoloLink generates it as an int8_t, typically
         * in the range of -80 to -30.
         */

        signedRssi = static_cast<int8_t>(radioStatus.remrssi);
        if (telemetryVals.rssi != signedRssi) {
            onRssiChanged(signedRssi);
            telemetryVals.rssi = signedRssi;
        }
        break;

    case MAVLINK_MSG_ID_EKF_STATUS_REPORT:
        pendingEkfFlags = mavlink_msg_ekf_status_report_get_flags(msg);
        /*
         * just mark the ekf flags as dirty - we will process
         * them the next time we receive a heartbeat, since
         * the ekf processing depends on an up to date arm state.
         */
        break;

    case MAVLINK_MSG_ID_MISSION_ITEM:
        mavlink_mission_item_t item;
        mavlink_msg_mission_item_decode(msg, &item);

        if (home.update(item)) {
            Ui::instance.pendEvent(Event::HomeLocationChanged);
        }
        break;
    }
}

void FlightManager::onArmStateChanged(ArmState as)
{
    if (as == Armed) {
        requestHomeWaypoint();

    } else if (as == Disarmed) {
        takeoffState = TakeoffNone;

        // return to loiter if in auto mode
        if (flightModeIsAutonomous(mode)) {
            requestFlightModeChange(LOITER);
        }
    }

    Ui::instance.pendEvent(Event::ArmStateUpdated);

//    DBG(("arm status: %d\n", as));
}

void FlightManager::onSystemStatusChanged(uint8_t ss)
{
    Button & btn = ButtonManager::button(Io::ButtonFly);

    if (ss == MAV_STATE_ACTIVE) {
        btn.setLedActive();
    } else {
        btn.setLedInactive();
    }

    updateRCFailsafeState(ss);
//    DBG(("system status: %d\n", ss));
}

void FlightManager::onFlightModeChanged(FlightMode fm)
{
    ButtonManager::onFlightModeChanged(fm);
    Ui::instance.pendEvent(Event::FlightModeChanged);

//    DBG(("flightMode: %s\n", flightModeStr(fm)));
}

void FlightManager::onGpsFixChanged(uint8_t gps)
{
    UNUSED(gps);

#if 0
    // Dismiss lockout alert when GPS is regained
    if (Ui::instance.alertManager.currentAlertWaitingForGps() && Telemetry::isGPSLevelFix(gps)){
        Ui::instance.pendEvent(Event::AlertRecovery);
        return;
    }

    // using EKF to determine GPS availability, rather than reported gps fix
    if (inFlight()) {
        bool prevGpsOk = Telemetry::hasGpsFix();
        bool currGpsOk = Telemetry::isGPSLevelFix(gps);

        // GPS lost
        if (prevGpsOk && !currGpsOk) {
            if (currentFlightModeManual()) {
                Ui::instance.pendEvent(Event::GpsLostManual);
            } else {
                Ui::instance.pendEvent(Event::GpsLost);
            }
            return;
        }

        // GPS regained
        if (!prevGpsOk && currGpsOk) {
            Ui::instance.pendEvent(Event::GpsLostRecovery);
            return;
        }
    }
#endif

//    DBG(("gps fix: %d\n", gps));
}

void FlightManager::onGpsNumSatellitesChanged(uint8_t numsat)
{
    UNUSED(numsat);

    Ui::instance.pendEvent(Event::GpsNumSatellitesChanged);
}

void FlightManager::onAltitudeChanged(float alt)
{
    UNUSED(alt);

    Ui::instance.pendEvent(Event::AltitudeUpdated);
}

void FlightManager::onBatteryChanged(int8_t battLevel)
{   
    // check if we need to dismiss or bring up new battery alerts
    if (batteryPhaseTransition(battLevel)) {
        updateBatteryPhase(battLevel);
    }

    Ui::instance.pendEvent(Event::FlightBatteryChanged);
//    DBG(("batt: %d\n", battLevel));
}

bool FlightManager::batteryPhaseTransition(int8_t battLevel)
{
    if (battLevel == BatteryLevelNotSet) {
        return false; // don't do anything
    }

    const BatteryState & batteryState = batteryStates[currentBatteryPhase];
    battLevel = clamp(battLevel, BatteryLevelMin, BatteryLevelMax);
    return !(battLevel > batteryState.minLevel && battLevel <= batteryState.maxLevel);
}

void FlightManager::updateBatteryPhase(int8_t battLevel)
{
    battLevel = clamp(battLevel, BatteryLevelMin, BatteryLevelMax);
    for (uint8_t i=0; i < numBattStates; ++i) {
        const BatteryState & batteryState = batteryStates[i];
        // update battery phase based on the lowest mininum battery level threshold
        if (battLevel > batteryState.minLevel && currentBatteryPhase != batteryState.phase) {
            currentBatteryPhase = batteryState.phase;
            updateBatteryAlert(batteryState.event);
            return;
        }
    }
}

void FlightManager::updateBatteryAlert(Event::ID id)
{
    // check to see if we need to dismiss any battery alerts
    // note: if battery was messed up and we need to transition from a fullscreen alert
    //       to a banner alert, we would need to first dismiss the fullscreen alert
    switch (Ui::instance.alertManager.currentEvent()) {
    case Event::FlightBatteryLow:
    case Event::FlightBatteryFailsafe:
    case Event::FlightBatteryCritical:
    case Event::FlightBatteryTooLowForTakeoff:
        Ui::instance.alertManager.dismiss();
        break;
    default:
        break;
    }

    if (currentBatteryPhase != BatteryNormal) {
        Ui::instance.pendEvent(id);
    }
}


void FlightManager::onRssiChanged(int8_t rssi)
{
    if (UiTelemetry::rssiBars(telemetryVals.rssi) != UiTelemetry::rssiBars(rssi)) {
        Ui::instance.pendEvent(Event::RssiUpdated);
    }

#if 0 // TODO: disabled until we have better ways to determine poor connection quality
    if (UiTelemetry::rssiBars(rssi) <= RSSI_BARS_POOR_CONNECTION){
        // Connection to Solo is poor, notify user the first time this occurs
        if (goodConnectionToSolo){
            goodConnectionToSolo = false;
            Ui::instance.pendEvent(Event::SoloConnectionPoor);
        }
    }
#endif
    
//    DBG(("rssi: %d\n", rssi));
}

void FlightManager::onGpsPositionChanged(const Coord2D & c)
{
    UNUSED(c);  // not used at the moment

    Ui::instance.pendEvent(Event::GpsPositionChanged);
}

bool FlightManager::modeIsNotArmable(const char * statusString) const
{
    const char * const notArmable = "Arm: Mode not armable";
    return (strncmp(statusString, notArmable, strlen(notArmable)) == 0);
}

void FlightManager::processStatusText(const char * statusString)
{
    const char * const serviceRequiredStrings[] = {
        "PreArm: Accelerometers not healthy",
        "PreArm: Gyros not healthy",
        "PreArm: Compass not healthy",
        "PreArm: Barometer not healthy",
        "PreArm: Barometer not healthy!",
        "PreArm: Check Board Voltage",
    };

    const char * const levelErrorStrings[] = {
        "PreArm: INS not calibrated",
        "PreArm: inconsistent Gyros",
        "PreArm: inconsistent Accelerometers",
    };

    const char * const altDisparityStrings[] = {
        "PreArm: Altitude disparity",
    };

    const char * const waitingForNavChecksStrings[] = {
        "PreArm: Waiting for Nav Checks",
        "Arm: Waiting for Nav Checks",
    };

    const char * const compassCalStrings[] = {
        "PreArm: Compass not calibrated",
        "PreArm: Compass offsets too high",
    };

    const char * const compassInterferenceStrings[] = {
        "PreArm: Check mag field",
        "PreArm: inconsistent compasses",
    };

    const char * const levelCalRunningStrings[] = {
        "Arm: Accelerometer calibration running",
    };

    const char * const compassCalRunningStrings[] = {
        "Arm: Compass calibration running",
    };

    const char * const waitingForSoloCalStrings[] = {
        "Arm: Altitude disparity",
    };

    const char * const calFailedStrings[] = {
        "Arm: Gyro calibration failed",
    };

    const char * const throttleTooHigh[] = {
        "Arm: Throttle too high",
    };

    const char * const leaningStrings[] = {
        "Arm: Leaning",
    };

    struct StatusTextEvent {
        const char * const *strings;
        unsigned count;
        Event::ID event;
    } const statusTextEvents[] = {
        { serviceRequiredStrings, arraysize(serviceRequiredStrings), Event::VehicleRequiresService },
        { levelErrorStrings, arraysize(levelErrorStrings), Event::LevelError },
        { altDisparityStrings, arraysize(altDisparityStrings), Event::AltitudeCalRequired },
        { waitingForNavChecksStrings, arraysize(waitingForNavChecksStrings), Event::WaitingForNavChecks },
        { compassCalStrings, arraysize(compassCalStrings), Event::CompassCalRequired },
        { compassInterferenceStrings, arraysize(compassInterferenceStrings), Event::CompassInterference },
        { compassCalRunningStrings, arraysize(compassCalRunningStrings), Event::CompassCalibrating },
        { levelCalRunningStrings, arraysize(levelCalRunningStrings), Event::LevelCalibrating },
        { waitingForSoloCalStrings, arraysize(waitingForSoloCalStrings), Event::VehicleCalibrating },
        { calFailedStrings, arraysize(calFailedStrings), Event::CalibrationFailed },
        { throttleTooHigh, arraysize(throttleTooHigh), Event::ThrottleError },
        { leaningStrings, arraysize(leaningStrings), Event::CantArmWhileLeaning },
    };

    // if status text matches one of our strings, post the corresponding event
    for (unsigned i = 0; i < arraysize(statusTextEvents); ++i) {
        const StatusTextEvent & ste = statusTextEvents[i];
        for (unsigned j = 0; j < ste.count; ++j) {
            if (strncmp(statusString, ste.strings[j], strlen(ste.strings[j])) == 0) {
                Ui::instance.pendEvent(ste.event);
                return;
            }
        }
    }

    bool unrecognizedPrearm = (strncmp(statusString,"Arm: ",strlen("Arm: ")) == 0) || (strncmp(statusString,"PreArm: ", strlen("PreArm: ")) == 0);
    // if status text is an unrecognized pre-arm failure,
    if (Ui::instance.alertManager.currentAlertVehiclePreArm() && unrecognizedPrearm) {
        Ui::instance.alertManager.dismiss();
        return;
    }
}

void FlightManager::onStatusTextChanged()
{
    /*
     * There are several status text messages that correspond to
     * conditions that we think we can't easily recover from.
     *
     * Unfortunately, these are not enumerated anywhere, we just
     * need to strcmp and hope none of the strings get changed in the flight code...
     */

    if (modeIsNotArmable(statusTxt.mav.text)) {
        requestFlightModeChange(LOITER);
        return;
    }

    processStatusText(statusTxt.mav.text);
}

void FlightManager::onArmableStatusChanged(int32_t statusVal)
{
    modeArmableStatus = statusVal;

    // check to see if we need to dismiss any PreArm alerts, want to be sure we don't dismiss any non-PreArm alerts (e.g. battery warnings, etc.)
    if (readyToArmWithoutGPS() && Ui::instance.alertManager.currentAlertVehiclePreArm()) {
        Ui::instance.alertManager.dismiss();
    }
}

void FlightManager::onEkfChanged(uint16_t ekfFlags)
{
    /*
     * if current gps is ok, and transitioning to not ok, notify ui.
     *
     * XXX: also probably want to request home location again here,
     *      if we've gained gps mid-flight, since it may have been updated.
     *      Not doing this for now, since we need to figure out our
     *      strategy for communicating to the user that when they press
     *      RTL, the vehicle may not actually come back to them...
     */

    Ui::instance.pendEvent(Event::GpsFixChanged);

    // Pend alert if GPS is lost or regained in flight.
    // these checks require a known ekf state, so do not compute
    // if we don't have up to date ekf state.
    if (inFlight() && telemetryVals.ekfFlagsInitialized()) {
        bool prevGpsOk = Telemetry::isEkfGpsOk(telemetryVals.ekfFlags);
        bool currGpsOk = Telemetry::isEkfGpsOk(ekfFlags);

        // GPS lost
        if (prevGpsOk && !currGpsOk) {
            if (currentFlightModeManual()) {
                Ui::instance.pendEvent(Event::GpsLostManual);
            } else {
                Ui::instance.pendEvent(Event::GpsLost);
            }
            return;
        }

        // GPS regained
        if (!prevGpsOk && currGpsOk) {
            Ui::instance.pendEvent(Event::GpsLostRecovery);
            return;
        }
    }

//    DBG(("ekfFlags change: 0x%x\n", ekfFlags));
}

void FlightManager::sendCmd(mavlink_message_t *msg)
{
    /*
     * Produce a mavlink packet for the currently pending command.
     * Called when we have a command ready to be sent to the vehicle.
     */

    switch (command.id) {
    case Command::SetArmState:
        mavlink_msg_command_long_pack(Mavlink::ArtooSysID, Mavlink::ArtooComponentID, msg,
                                      Mavlink::SoloSysID, MAV_COMP_ID_SYSTEM_CONTROL,
                                      MAV_CMD_COMPONENT_ARM_DISARM,
                                      0,                    // confirmation
                                      (command.arm == Armed) ? 1 : 0,  // 1 for arm, 0 for disarm
                                      (command.arm == DisarmForce) ? ForceDisarmMagic : 0,
                                      0, 0, 0, 0, 0);    // params 3-7
        break;

    case Command::Takeoff:
        mavlink_msg_command_long_pack(Mavlink::ArtooSysID, Mavlink::ArtooComponentID, msg,
                                      Mavlink::SoloSysID, 1,
                                      MAV_CMD_NAV_TAKEOFF,
                                      0,                // confirmation
                                      0, 0, 0, 0, 0, 0, // params 1-6
                                      TakeoffAltitude); // param 7 - altitude in meters
        break;

    case Command::SetFlightMode:
        mavlink_msg_set_mode_pack(Mavlink::ArtooSysID, Mavlink::ArtooComponentID, msg, Mavlink::SoloSysID,
                                  MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, command.flightMode);
        break;

    case Command::FlyButtonClick:
        mavlink_msg_command_long_pack(Mavlink::ArtooSysID, Mavlink::ArtooComponentID, msg,
                                      Mavlink::SoloSysID, MAV_COMP_ID_SYSTEM_CONTROL,
                                      MAV_CMD_SOLO_BTN_FLY_CLICK,
                                      0,                    // confirmation
                                      0, 0, 0, 0, 0, 0, 0);    // params 1-7
        break;

    case Command::FlyButtonHold:
        mavlink_msg_command_long_pack(Mavlink::ArtooSysID, Mavlink::ArtooComponentID, msg,
                                      Mavlink::SoloSysID, MAV_COMP_ID_SYSTEM_CONTROL,
                                      MAV_CMD_SOLO_BTN_FLY_HOLD,
                                      0,                    // confirmation
                                      TakeoffAltitude,
                                      0, 0, 0, 0, 0, 0);    // params 2-7
        break;

    case Command::GetHomeWaypoint:
        mavlink_msg_mission_request_pack(Mavlink::ArtooSysID, Mavlink::ArtooComponentID, msg,
                                         Mavlink::SoloSysID, Mavlink::SoloComponentID,
                                         command.waypoint);
        break;

    default:
        break;
    }
}

void FlightManager::cmdAcknowledged(const mavlink_command_ack_t *ack)
{
    /*
     * A command has been acked by the vehicle.
     * Tick along to our next state as appropriate.
     */

    switch (ack->command) {
    case MAV_CMD_COMPONENT_ARM_DISARM:
        if (ack->result != MAV_RESULT_ACCEPTED) {
            Ui::instance.arming.onArmFailed();
        }
        break;

    case MAVLINK_MSG_ID_SET_MODE:
        onFlightModeAck(ack);
        break;

    case MAV_CMD_NAV_TAKEOFF:
        if (ack->result == MAV_RESULT_ACCEPTED) {
            takeoffState = TakeoffAscending;
        } else {
            Ui::instance.arming.onTakeoffFailed();
        }
        break;
    }

    if (ack->result != MAV_RESULT_ACCEPTED) {
        DBG(("mavlink nack. cmd %d, result %d\n", ack->command, ack->result));
    }
}

void FlightManager::onFlightModeAck(const mavlink_command_ack_t *ack)
{
    /*
     * A flight mode request has been acknowledged.
     *
     * Mainly, we're checking to see whether the mode change was a
     * change to LOITER to enable takeoff.
     */

    if (ack->result == MAV_RESULT_ACCEPTED) {
        if (takeoffState == TakeoffSetMode && systemStatus == MAV_STATE_STANDBY) {
            takeoffState = TakeoffSentTakeoffCmd;
            command.set(Command::Takeoff);
            return;
        }
    }

    takeoffState = TakeoffNone;
}
