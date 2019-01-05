#include "ui_alert.h"
#include "ui.h"
#include "haptic.h"
#include "resources-gen.h"

// must be in order of Event::ID starting at Event::AlertBegin
const UiAlertManager::Alert UiAlertManager::alerts[] = {

    /// Pre-flight - PreArm

    // AltitudeCalRequired *H
    { Red, NoHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Calibrating ", "altitude", "Please wait", NULL },

    // CompassCalRequired
    { Red, HighHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Compass ", "error", "Please calibrate compass using\nmobile app and reboot solo", NULL },

    // CompassInterference
    { Red, NoHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Magnetic ", "interference", "Move Solo away from metal objects", NULL },

    // LevelError
    { Red, MedHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Level ", "error", "Please calibrate level using\nmobile app and reboot solo", NULL },

    // CalibrationFailed
    { Red, MedHaptic, FullScreenModal, NO_TIMEOUT, DismissA, "Motion ", "detected", "Take off from a steady surface", NULL },

    // WaitingForNavChecks
    { Green, NoHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Calibrating ", "sensors", "Please wait", NULL },

    /// Pre-flight - Arm

    // CantArmWhileLeaning
    { Orange, NoHaptic, FullScreenModal, 5000, DismissNone, "Uneven ", "surface", "Solo must be level for takeoff\nMove Solo to a flat surface", NULL },

    // VehicleCalibrating
    { Orange, NoHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Calibrating ", "Solo", "Please wait", NULL },

    // CompassCalibrating
    { Orange, NoHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Calibrating ", "compass", "Follow app instructions", NULL },

    // LevelCalibrating
    { Orange, NoHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Calibrating ", "level", "Follow app instructions", NULL },

    // CompassCalRecovery
    { Green, NoHaptic, FullScreenModal, NO_TIMEOUT, DismissA, "Calibrated ", "compass", NULL, "Press A to dismiss\nthen reboot solo" },

    // ThrottleError
    { Orange, LowHaptic, FullScreenModal, 5000, DismissNone, "Lower ", "throttle", "This flight mode requires low\nthrottle before starting motors", NULL },

    // VehicleRequiresService // TODO: duplicate of CalibrationFailed, should just change logic in code
    { Red, HighHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Calibration ", "error", "Please restart Solo", NULL },
    //{ Red, HighHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Service ", "required", "Use 3DR Solo app to log a trouble\nticket with customer support", NULL },

    /// Pre-flight - Artoo

    // FlightBatteryTooLowForTakeoff
    { Red, NoHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Charge ", "flight battery", "Battery too low for flight", NULL },

    // UnknownBattery
    { Red, MedHaptic, FullScreenModal, 5000, DismissA, "Unknown ", "battery", "Displayed level may not be accurate", "Press A to dismiss" },

    // (unused, currently hardcoded as a function) WaitingForSolo
    // { Green, NoHaptic, FullScreenThenHintBox, DismissNone, NO_TIMEOUT, "waiting ", "for Solo", NULL, NULL },

    // ControllerBatteryTooLowForTakeoff
    { Red, HighHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Charge ", "controller", "Battery too low for flight", NULL },

    // SystemIdleWarning
    { Green, NoHaptic, FullScreenModal, 7000, DismissNone, "Controller ", "inactive", "Powering off", NULL },

    // SoloAppConnected
    { Green, NoHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, "Mobile app connected", NULL },

    // SoloAppDisconnected
    { Orange, NoHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, "Mobile app disconnected", NULL },

    // ControllerValueOutOfRange
    { Red, NoHaptic, FullScreenThenHintBox, 5000, DismissNone, "Control stick ", "error", "Contact 3DR Support", NULL },

    // CamControlValueOutOfRange
    { Orange, MedHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, NULL, NULL },

    // RecordRequiresApp
    { Orange, MedHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, NULL, NULL },

    /// Pre-flight - Gimbal

    // GimbalConnected
    { Green, NoHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, NULL, NULL },

    // GimbalNotConnected
    { Green, NoHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, NULL, NULL },

    /// Pre-flight - GoPro

    // none yet



    /// In-flight - RC

    // RCFailsafe, XXX: temporarily remove "Returning home" contextMsg since this can be triggered when the vehicle doesn't actually rc failsafe
    { Red, NoHaptic, FullScreenModal, 5000, DismissNone, "Controller ", "signal lost", NULL, NULL },

    // RCFailsafeNoGPS, XXX: temporarily remove "Emergency landing started" contextMsg since this can be triggered when the vehicle doesn't actually rc failsafe
    { Red, LowHaptic, FullScreenModal, 5000, DismissNone, "Controller ", "signal lost", NULL, NULL },

    // RCFailsafeRecovery
    { Green, NoHaptic, FullScreenModal, NO_TIMEOUT, DismissFly, "Signal ", "recovered", NULL, "Press FLY to take control" },

    /// In-flight - Flight battery

    // FlightBatteryLow
    { Orange, MedHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, NULL, NULL },

    // FlightBatteryCritical
    { Red, HighHaptic, FullScreenModal, 5000, DismissNone, "Return home ", "soon", "Flight battery at 15%", NULL },

    // FlightBatteryFailsafe
    { Red, HighHaptic, FullScreenThenHintBox, 5000, DismissNone, "Returning ", "home", "Flight battery failsafe", NULL },

    /// In-flight - Sensors

    // MaximumAltitude
    { Red, LowHaptic, FullScreenModal, 5000, DismissNone, "Maximum ", "altitude", "Solo has reached preset\nmaximum altitude", NULL },

    // CrashDetected
    { Red, HighHaptic, FullScreenModal, NO_TIMEOUT, DismissA, "Crash ", "detected", "Hopefully nothing too\nexpensive broke", "Press A to dismiss" },

    // LandingComplete
    { Green, NoHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, NULL, NULL },

    // GpsLost
    { Red, HighHaptic, FullScreenModal, 5000, DismissFly, "GPS ", "lost", "Switching to manual control", NULL },

    // GpsLostManual
    { Red, HighHaptic, FullScreenModal, 5000, DismissNone, "GPS ", "lost", "Return Home not available", NULL },

    // GpsLostRecovery
    { Green, NoHaptic, FullScreenModal, 3000, DismissNone, "GPS ", "ready", NULL, NULL},

    /// In-flight - Flight modes

    // ShotInfoUpdated
    { Green, NoHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, NULL, NULL }, // TODO: White or Green?

    // ShotInfoUpdateFail
    { Orange, NoHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, NULL, NULL },

    // RTLWithoutGPS            
    { Orange, MedHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, NULL, NULL },

    /// In-flight - Artoo

    // SoloConnectionPoor
    { Orange, LowHaptic, HintBoxBanner, 5000, DismissNone, NULL, NULL, NULL, NULL },

    // ControllerBatteryCritical
    { Red, HighHaptic, FullScreenThenHintBox, 5000, DismissNone, "Land ", "soon", "Controller battery at 5%", NULL },

    // ControllerBatteryFailsafe
    { Red, HighHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Returning ", "home", "Controller battery at 0%", NULL },

    // ControllerBatteryFailsafeNoGps
    { Red, HighHaptic, FullScreenModal, NO_TIMEOUT, DismissNone, "Landing ", "engaged", "Controller battery at 0%", NULL },

    // ChargerConnected
    { White, NoHaptic, FullScreenModal, 3000, DismissNone, NULL, NULL, NULL, NULL },

    // CH-7 & CH-8 RC control
    { Green, LowHaptic, HintBoxBanner, 3000, DismissNone, NULL, NULL, "CH-7 Set Low", NULL },
    { Green, LowHapticMed, HintBoxBanner, 3000, DismissNone, NULL, NULL, "CH-7 Set High", NULL },
    { Green, LowHaptic, HintBoxBanner, 3000, DismissNone, NULL, NULL, "CH-8 Set Low", NULL },
    { Green, LowHapticMed, HintBoxBanner, 3000, DismissNone, NULL, NULL, "CH-8 Set High", NULL },

    /// Testing

    // TestAlert
    { Orange, MedHaptic, FullScreenThenHintBox, 5000, DismissNone, "RTL ", "not available", "(Test test)", NULL },

};

UiAlertManager::UiAlertManager() :
    event(Event::None),
    periodicNotificationCounter()
{
    STATIC_ASSERT(arraysize(alerts) == Event::AlertEnd - Event::AlertBegin);
}

// returns true if the alert needs to be displayed via a fullscreen modal
bool UiAlertManager::init(Event::ID id)
{
    // don't do anything if already showing alert or new alert should not replace previous alert
    if (event == id || !canReplaceCurrentAlert(id)) {
        return false;
    }

    event = id;

    if (!hasAlert()) { // Check is currently redundant with check above but done for consistency
        return false;
    }
    const Alert & a = currentAlert();

    a.startHaptic();

    // notify alert displayers about the change
    if (a.needsBannerDisplay()) {
        Ui::instance.telem.bottomBox.onEvent(id);
    }
    if (a.needsFullscreenDisplay()) {
        Ui::instance.fullscreenmodal.onEvent(id);
        return true;
    }

    return false;
}

bool UiAlertManager::periodicHapticEnabled() const
{
    /*
     * Specify whether to periodically provide haptic feedback.
     */

    if (event == Event::RCFailsafeRecovery) {
        // after a failsafe, users often do not realize they have the opportunity
        // to regain control. give them a gentle reminder.
        return true;
    }

    if (FlightManager::instance.periodicHapticRequested()) {
        return true;
    }

    return false;
}

void UiAlertManager::sysHeartbeat()
{
    /*
     * Called from FiftyHzHeartbeat task.
     * Opportunity to do any periodic work for alerts.
     */

    if (periodicHapticEnabled()) {
        // provide periodic haptic feedback until user notices us
        if (++periodicNotificationCounter >= PERIODIC_NOTIFY_INTERVAL) {
            Haptic::startPattern(Haptic::SingleShort);
            periodicNotificationCounter = 0;
        }
    }
}

void UiAlertManager::Alert::startHaptic() const
{
    // might be redundant between cases but this makes it easy to adapt to changes in desired haptic behavior
    if (needsFullscreenDisplay()) {
        switch (hapticSeverity) {
        case HighHaptic:
            Haptic::startPattern(Haptic::HeavyTriple);
            break;
        case MedHaptic:
            Haptic::startPattern(Haptic::LightTriple);
            break;
        case LowHaptic:
            Haptic::startPattern(Haptic::SingleShort);
            break;
        default:
            break;
        }
    } else {
        switch (hapticSeverity) {
        case HighHaptic:
            Haptic::startPattern(Haptic::HeavyTriple);
            break;
        case MedHaptic:
            Haptic::startPattern(Haptic::LightTriple);
            break;
        case LowHaptic:
            Haptic::startPattern(Haptic::SingleShort);
            break;
        case LowHapticMed:
            Haptic::startPattern(Haptic::SingleMedium);
            break;
        default:
            break;
        }
    }
}

bool UiAlertManager::Alert::buttonWillDismiss(const Button *b, const Button::Event e) const
{
    /*
     * Should this alert be dimissed by the given button event?
     *
     * Only dismiss the event on release, such that all other event types
     * for the matching button are consumed in the meantime,
     * so they aren't forwarded externally (to the vehicle).
     */

    switch (dismissBtn) {
    case DismissA:
        if (b->id() == Io::ButtonA && e == Button::Release) {
            return true;
        }
        break;

    case DismissFly:
        if (b->id() == Io::ButtonFly && e == Button::Release) {
            return true;
        }
        break;

    default:
        break;
    }

    return false;
}

bool UiAlertManager::Alert::shouldConsumeEvent(const Button *b, const Button::Event e) const
{
    /*
     * Should we prevent further propagation of this button event?
     *
     * We consume all button event types for a given dismissal button.
     */

    UNUSED(e);

    switch (dismissBtn) {
    case DismissA:
        if (b->id() == Io::ButtonA) {
            return true;
        }
        break;

    // DismissFly is not consumed, since FLY button events are handled
    // internally by flightmanager. a little crufty but ok for now.

    default:
        break;
    }

    return false;
}

bool UiAlertManager::canReplaceCurrentAlert(Event::ID id) const
{
    if (!hasAlert()) {
        return true;
    }

    if (!alertIsDefinedFor(id)) {
        return false;
    }

    const Alert & curr_alert = currentAlert();
    const Alert & new_alert = getAlert(id);

    // Fullscreen alerts are higher priority than banner-only alerts
    if (curr_alert.needsFullscreenDisplay() && !new_alert.needsFullscreenDisplay()){
        return false;
    }

    return true;
}

bool UiAlertManager::complete(SysTime::Ticks start) const
{
    /*
     * Is this alert done?
     * We may have been dismissed, or may have timed out.
     */

    // dismissed?
    if (!hasAlert()) {
        return true;
    }

    const Alert & a = currentAlert();

    if (a.durationMillis == NO_TIMEOUT) {
        return false;
    }

    return SysTime::now() - start > SysTime::msTicks(a.durationMillis);
}

void UiAlertManager::dismiss()
{
    event = Event::None;

    // notify alert displayers about the change
    Ui::instance.fullscreenmodal.onEvent(Event::None);
    Ui::instance.telem.bottomBox.onEvent(Event::None);
}

bool UiAlertManager::onButtonEvent(Button *b, Button::Event e)
{
    /*
     * Dismiss alerts with a simple push of a button.
     *
     * Return true to prevent further propagation of this button event.
     */

    if (!hasAlert()) {
        return false;
    }

    const Alert & a = currentAlert();

    bool consumed = a.shouldConsumeEvent(b, e);

    if (a.buttonWillDismiss(b, e)) {
        dismiss();
    }

    return consumed;
}

uint16_t UiAlertManager::Alert::severityColor() const
{
    switch (severity) {
    case Red:       return UiColor::Red;
    case Orange:    return UiColor::Orange;
    case Green:     return UiColor::Green;
    case White:     return UiColor::White;
    default:        return UiColor::White;
    }
}

const UiAlertManager::Alert & UiAlertManager::currentAlert() const
{
    return getAlert(event);
}

const UiAlertManager::Alert & UiAlertManager::getAlert(Event::ID id) const {
    ASSERT(alertIsDefinedFor(id));

    unsigned idx = id - Event::AlertBegin;
    return alerts[idx];
}

bool UiAlertManager::alertIsDefinedFor(Event::ID id) const
{
    if (!Event::isAlert(id)) {
        return false;
    }

    unsigned idx = id - Event::AlertBegin;
    return idx < sizeof(alerts);
}

bool UiAlertManager::currentAlertNeedsBanner()
{
    if (!hasAlert()){
        return false;
    }

    return currentAlert().needsBannerDisplay();
}

bool UiAlertManager::currentAlertNeedsFullscreen()
{
    if (!hasAlert()){
        return false;
    }

    return currentAlert().needsFullscreenDisplay();
}

bool UiAlertManager::currentAlertVehiclePreArm()
{
    switch(event) {
    case Event::AltitudeCalRequired:
    case Event::CompassCalRequired:
    case Event::CompassInterference:
    case Event::LevelError:
    case Event::CalibrationFailed:
    case Event::WaitingForNavChecks:
    case Event::CantArmWhileLeaning:
    case Event::VehicleCalibrating:
    case Event::CompassCalibrating:
    case Event::LevelCalibrating:
    case Event::ThrottleError:
    case Event::VehicleRequiresService:
        return true;

    default:
        return false;
    }
}

bool UiAlertManager::currentAlertRecovery()
{   
    switch(event) {
    case Event::CompassCalRecovery:
    case Event::RCFailsafeRecovery:
    case Event::GpsLostRecovery:
        return true;

    default:
        return false;
    }
}

void UiAlertManager::dismissInvalidStickAlerts()
{
    if (event == Event::ControllerValueOutOfRange || event == Event::CamControlValueOutOfRange) {
        dismiss();
    }
}
