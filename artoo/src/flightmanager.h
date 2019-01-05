#ifndef FLIGHTMANAGER_H
#define FLIGHTMANAGER_H

#include "button.h"
#include "hostprotocol.h"
#include "geo.h"
#include "home.h"
#include "telemetry.h"
#include "ui_events.h"
#include "tasks.h"

#include "mavlink/c_library/common/mavlink.h"
#include "mavlink/c_library/ardupilotmega/mavlink.h"

class FlightManager
{
public:
    // in sync with github.com/diydrones/ardupilot/blob/master/ArduCopter/defines.h
    enum FlightMode {
        STABILIZE =     0,  // manual airframe angle with manual throttle
        ACRO =          1,  // manual body-frame angular rate with manual throttle
        ALT_HOLD =      2,  // manual airframe angle with automatic throttle
        AUTO =          3,  // fully automatic waypoint control using mission commands
        GUIDED =        4,  // fully automatic fly to coordinate or fly at velocity/direction using GCS immediate commands
        LOITER =        5,  // automatic horizontal acceleration with automatic throttle
        RTL =           6,  // automatic return to launching point
        CIRCLE =        7,  // automatic circular flight with automatic throttle
        LAND =          9,  // automatic landing with horizontal position control
        DRIFT =        11,  // semi-automous position, yaw and throttle control
        SPORT =        13,  // manual earth-frame angular rate control with manual throttle
        FLIP =         14,  // automatically flip the vehicle on the roll axis
        AUTOTUNE =     15,  // automatically tune the vehicle's roll and pitch gains
        POSHOLD =      16,  // automatic position hold with manual override, with automatic throttle
        BRAKE =        17,  // full-brake using inertial/GPS system, no pilot input
        THROW =        18,  // throw to launch mode using inertial/GPS system, no pilot input
        AVOID_ADSB =   19,  // automatic avoidance of obstacles in the macro scale - e.g. full-sized aircraft
        GUIDED_NOGPS = 20,  // guided mode but only accepts attitude and altitude
        SMART_RTL =    21,  // SMART_RTL returns to home by retracing its steps
        FLOWHOLD =     22,  // FLOWHOLD holds position with optical flow without rangefinder
        FOLLOW    =    23,  // Follow attempts to follow another vehicle or ground station
        ZIGZAG    =    24,  // ZIGZAG mode is able to fly in a zigzag manner with predefined point A and point B
        };   

    /*
     * XXX: the MAVLINK_MSG_ID_STATUSTEXT indicates that the MAV_SEVERITY enum
     *      is used for the severity level, but ardupilot defines and uses its own in
     *      github.com/diydrones/ardupilot/blob/master/libraries/GCS_MAVLink/GCS_MAVLink.h
     */
    enum GcsSeverity {
        SEVERITY_LOW=1,
        SEVERITY_MEDIUM,
        SEVERITY_HIGH,
        SEVERITY_CRITICAL,
        SEVERITY_USER_RESPONSE
    };

    struct StatusText {
        mavlink_statustext_t mav;
        SysTime::Ticks rxtime;
    };

    // int8_t types since battLevel is propagated as int8_t
    static const int8_t BatteryLevelNotSet             = -1;
    static const int8_t BatteryLevelMin                = -100; // should only see values >=0 in real flights but this is to accomodate limited/unity failsafe state value range
    static const int8_t BatteryLevelFailsafe           = 10;
    static const int8_t BatteryLevelCritical           = 15;
    static const int8_t BatteryLevelLow                = 25;
    static const int8_t BatteryLevelLowDismiss         = 35;
    static const int8_t BatteryLevelMax                = 100;
    static const int8_t BatteryLevelDismissBuffer      = 3;    // allows for some inconsistencies with flight battery level

    enum BatteryPhase {
        BatteryNormal,
        BatteryLow,
        BatteryCritical,
        BatteryFailsafe,
    };

    struct BatteryState {
        const BatteryPhase phase;
        const Event::ID event;
        const int8_t minLevel;
        const int8_t maxLevel;
    };

    FlightManager();

    static FlightManager instance;

    void init();
    void sysHeartbeat();
    bool producePacket(HostProtocol::Packet &p);
    void onMavlinkData(const uint8_t *bytes, uint8_t len);
    void onPixhawkMavlinkMsg(const mavlink_message_t *msg);
    void onSoloMavlinkMsg(const mavlink_message_t *msg);

    ALWAYS_INLINE bool linkIsConnected() const {
        return linkConnCounter < LINK_CONN_DURATION;
    }

    ALWAYS_INLINE const Telemetry & telemVals() const {
        return telemetryVals;
    }

    ALWAYS_INLINE FlightMode flightMode() const {
        return mode;
    }
    static const char *flightModeStr(FlightMode m);
    static bool flightModeIsAutonomous(FlightMode m) {
        return (m == AUTO || m == GUIDED || m == LOITER || m == RTL || m == CIRCLE || m == DRIFT || m == POSHOLD || m == BRAKE || m == THROW || m == AVOID_ADSB || m == GUIDED_NOGPS || m == SMART_RTL || m == FLOWHOLD
        || m == FOLLOW || m == ZIGZAG);
    }

    ALWAYS_INLINE bool currentFlightModeManual() const {
        return !flightModeIsAutonomous(mode);
    }

    ALWAYS_INLINE bool currentFlightModeRequiresGPS() const {
        return flightModeIsAutonomous(mode);
    }

    bool periodicHapticRequested() const {
        // provide periodic haptic feedback while landing,
        // intended to happen either as a result of an explicit user-requested
        // land, or an auto land as a result of gps loss
        return inFlight() && mode == LAND;
    }

    bool mustWaitForGpsToArm() const {

        // already armed, nothing to wait for
        if (armed()) {
            return false;
        }

        // don't know yet whether we have gps?
        if (!telemetryVals.ekfFlagsInitialized()) {
            return true;
        }

        return currentFlightModeRequiresGPS() && telemetryVals.hasGpsFix() == false;
    }

    static ALWAYS_INLINE bool sysStatusIsInFlight(uint8_t ss) {
        switch (ss) {
        case MAV_STATE_ACTIVE:      // normal operation
        case MAV_STATE_CRITICAL:    // failsafe
            return true;

        default:
            return false;
        }
    }

    bool inFlight() const {
        return inFlight(systemStatus);
    }

    bool inFlight(uint8_t sysStatus) const {
        if (!armed()) {
            return false;
        }
        return sysStatusIsInFlight(sysStatus);
    }

    ALWAYS_INLINE bool armed() const {
        return armState == Armed;
    }

    ALWAYS_INLINE bool readyToArm() const {
        return ((1 << mode) & modeArmableStatus);
    }

    ALWAYS_INLINE bool readyToArmWithoutGPS() const {
        return ((1 << ALT_HOLD) & modeArmableStatus);   // TODO Hack: ALT_HOLD does not require GPS so use this to dismiss alerts
    }

    bool readyToFly() const {
        // are we on the ground, armed, but have not yet taken off?
        return armed() && !inFlight();
    }

    const StatusText & statusText() const {
        return statusTxt;
    }

    double distanceFromTakeoff() const {
        if (home.loc().isEmpty() || currentLoc.isEmpty()) {
            return 0;
        }
        return geo::distanceInMeters(home.loc(), currentLoc);
    }

    void onFlyButtonEvt(Button *b, Button::Event evt);
    void onRtlButtonEvt(Button *b, Button::Event evt);
    void onAButtonEvt(Button *b, Button::Event e);
    void onBButtonEvt(Button *b, Button::Event e);
    void onPowerButtonEvt(Button *b, Button::Event e);
    void onPauseButtonEvt(Button *b, Button::Event e);
    // shot mgr on SoloLink handles A/B/Loiter button events

private:
    static const unsigned ForceDisarmMagic          = 21196;

    static const unsigned TakeoffAltitude = 3;

    // how many heartbeat ticks (50Hz) before we consider the link dead
    static const unsigned LINK_CONN_DURATION        = Tasks::HEARTBEAT_HZ * 3;  // ~3 seconds

    // XXX: tbd which sensors we care about
    static const uint32_t SensorMask = MAV_SYS_STATUS_SENSOR_3D_GYRO |
                                        MAV_SYS_STATUS_SENSOR_3D_ACCEL |
                                        MAV_SYS_STATUS_SENSOR_3D_MAG;

    static const uint8_t RSSI_BARS_POOR_CONNECTION = 1;  // triggers "Poor Connection" at <= value

    enum ArmState {
        Disarmed    = 0,
        Armed       = 1,
        DisarmForce = 2,
    };

    struct Command {
        enum State {
            Complete,   // complete
            Pending,    // command ready to be sent
            Sent,       // sent, waiting for ack
        };

        // we pend a mix of MAV_CMD and mavlink msg ids,
        // so must map between them to avoid conflicts.
        enum ID {
            None,
            SetFlightMode,
            SetArmState,
            GetHomeWaypoint,
            Takeoff,
            FlyButtonClick,
            FlyButtonHold,
            PauseButtonClick,
        };

        ID id;
        State state;
        // data that must accompany this command
        union {
            FlightMode flightMode;
            uint8_t arm;    // arm, disarm, or force disarm
            uint16_t waypoint;
        };

        void set(ID id_) {
            ASSERT(state != Pending);
            id = id_;
            state = Pending;
            HostProtocol::instance.requestTransaction();
        }
    };

    enum TakeoffState {
        TakeoffNone,
        TakeoffSetMode,
        TakeoffSentTakeoffCmd,
        TakeoffAscending,
        TakeoffComplete
    };

    FlightMode mode;
    uint8_t systemStatus;   // see enum MAV_STATE
    ArmState armState;
    int32_t modeArmableStatus; // bit mask with each bit representing whether the respective mode is armable (0 - not armable, 1 - armable)
    TakeoffState takeoffState;
    StatusText statusTxt;
    unsigned linkConnCounter;
    Command command;
    Telemetry telemetryVals;

    Coord2D currentLoc;
    Home home;

    bool goodConnectionToSolo;  // based on RSSI; deactivated once per flight // TODO: ensure this is reset between flights
    bool flagRCFailsafe;
    uint16_t pendingEkfFlags;

    BatteryPhase currentBatteryPhase;
    static const BatteryState batteryStates[];
    static const uint8_t numBattStates;

    void linkConnected();
    void linkDisconnected();
    void resetLinkConnCount(const mavlink_message_t * msg);
    void updateRCFailsafeState(uint8_t sysStatus);

    bool btnEventShouldForceDisarm(Button *b, Button::Event e) const;
    void cancelTakeoff();

    void beginTakeoff();

    void requestFlightModeChange(FlightMode m);
    void requestArmStateChange(ArmState as);
    void requestHomeWaypoint();

    void forceDisarm();

    void onArmStateChanged(ArmState as);
    void onSystemStatusChanged(uint8_t ss);
    void onFlightModeChanged(FlightMode fm);
    void onGpsFixChanged(uint8_t gps);
    void onGpsNumSatellitesChanged(uint8_t numsat);
    void onAltitudeChanged(float alt);
    void onBatteryChanged(int8_t battLevel);
    void onRssiChanged(int8_t rssi);
    void onGpsPositionChanged(const Coord2D & c);
    bool modeIsNotArmable(const char *statusString) const;
    void processStatusText(const char * statusString);
    void onStatusTextChanged();
    void onArmableStatusChanged(int32_t statusVal);
    void onEkfChanged(uint16_t ekfFlags);

    void sendCmd(mavlink_message_t *msg);
    void cmdAcknowledged(const mavlink_command_ack_t *ack);
    void onFlightModeAck(const mavlink_command_ack_t *ack);

    bool batteryPhaseTransition(int8_t battLevel);
    void updateBatteryPhase(int8_t battLevel);
    void updateBatteryAlert(Event::ID id);
};

#endif // FLIGHTMANAGER_H
