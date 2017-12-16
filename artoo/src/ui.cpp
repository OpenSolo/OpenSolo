#include "ui.h"
#include "gfx.h"
#include "ili9341parallel.h"
#include "battery.h"
#include "buttonmanager.h"
#include "powermanager.h"
#include "flightmanager.h"
#include "vehicleconnector.h"
#include "cameracontrol.h"
#include "version.h"
#include "lockout.h"
#include "resources-gen.h"

#include <string.h>
#include <stdio.h>
#include "ui_color.h"

Ui Ui::instance;

Ui::Ui() :
    telem(),
    arming(),
    pairing(),
    gimbal(),
    splash(),
    power(),
    updater(),
    alertManager(),
    fullscreenmodal(),
    topBar(),
    events(),
    currentState(PowerDown),
    pendingState(PowerDown),
    stateEnterTimestamp(0),
    lastRender(0)
{
}

void Ui::init()
{
    Gfx::init();
}

void Ui::setBacklightsForState(PowerManager::SysState s)
{
    switch (s) {
    case PowerManager::Boot:
        ButtonManager::setBacklight(0);
        ILI9341Parallel::lcd.enableBacklight();
        break;

    case PowerManager::Idle:
        ButtonManager::setBacklight(0);
        ILI9341Parallel::lcd.disableBacklight();
        break;

    case PowerManager::Running:
        ButtonManager::setBacklight(10);
        ILI9341Parallel::lcd.enableBacklight();
        break;
    }
}

void Ui::update()
{
    SysTime::Ticks now = SysTime::now();
    unsigned dt = (now - lastRender) / SysTime::msTicks(1);
    if (dt < 1000 / MaxFrameRate) {
        return;
    }

    lastRender = now;

    /*
     * Update the display, based on the current state.
     * First, check for transitions into a new state,
     * then do updates for the current state as necessary.
     */

    processEvents();

    // state transition
    if (pendingState != currentState) {
        switch (pendingState) {
        case Splash:
            splash.init();
            setBacklightsForState(PowerManager::state());
            break;

        case Lockout:
            drawLockout();
            break;

        case WaitForSolo:
            drawWaitingForSolo();
            break;

        case Telem:
            telem.init();
            break;

        case Arming:
            arming.init();
            break;

        case Pairing:
            pairing.init();
            break;

        case Gimbal:
            gimbal.init();
            break;

        case Shutdown:
            power.initShutdown();
            break;

        case FullscreenAlert:
            fullscreenmodal.init();

        default:
            break;
        }

        currentState = pendingState;
        stateEnterTimestamp = SysTime::now();
    }

    FlightManager & fm = FlightManager::instance;

    // current state
    switch (currentState) {
    case PowerDown:
        PowerManager::updatePowerDown();
        break;

    case Splash:
        if (splash.update()) {
            if (!Lockout::isUnlocked()) {
                pendingState = Lockout;
            } else if (fm.linkIsConnected()) {
                pendingState = Arming;
            } else {
                pendingState = WaitForSolo;
            }
        }
        break;

    case Updater:
        if (updater.update()) {
            pendingState = determineState();
        }
        break;

    case WaitForSolo:
        if (fm.linkIsConnected()) {
            if (fm.armed()) {
                pendingState = Telem;
            } else {
                pendingState = Arming;
            }
        }
        break;

    case Arming:
        if (!fm.linkIsConnected()) {
            pendingState = WaitForSolo;
        } else {
            if (fm.armed() && fm.inFlight()) {
                pendingState = Telem;
            } else {
                arming.update();
            }
        }
        break;

    case Telem:
        if (fm.linkIsConnected()) {
            if (fm.armed()) {
                telem.update();
            } else {
                pendingState = Arming;
            }
        } else {
            pendingState = WaitForSolo;
        }
        break;

    case Pairing:
        if (!fm.linkIsConnected()) {
            if (pairing.update()) {
                pendingState = determineState();
            }
        } else {
            pendingState = Arming;
        }
        break;

    case Gimbal:
        if (gimbal.update()) {
            stateEnterTimestamp = SysTime::now();

        } else if (SysTime::now() - stateEnterTimestamp > SysTime::sTicks(6)) {
            pendingState = determineState();
        }
        break;

    case FullscreenAlert:
        if (fullscreenmodal.complete()) {
            if (!alertManager.currentAlertNeedsBanner()) {
                alertManager.dismiss();    // dismiss alert if we're finished displaying it, otherwise, UiBottomBox will dismiss it when it's finished displaying
            }

            pendingState = determineState();
        }
        break;

    case Shutdown:
        if (power.updateShutdown()) {
            pendingState = PowerDown;
        }
        break;

    default:
        break;
    }
}

bool Ui::canTransition(State from, State to)
{
    /*
     * Define the set of states we can transition from
     * into another given state.
     */

    uint32_t validFromStates;

    switch (to) {
    case Gimbal:
        if (gimbal.isSuppressed()) {
            validFromStates = 0;
        } else {
            validFromStates = BIT(WaitForSolo) | BIT(Telem) | BIT(Arming);
        }
        break;

    case Pairing:
        validFromStates = BIT(WaitForSolo) | BIT(FullscreenAlert) | BIT(Gimbal) | BIT(Lockout);
        break;

    // add states here as necessary

    default:
        validFromStates = 0;
        break;
    }

    return (BIT(from) & validFromStates) != 0;
}

void Ui::processEvents()
{
    /*
     * Handle any events that may have been occurred,
     * since the last time the UI rendered.
     */

    while (!events.empty()) {
        Event::ID id = static_cast<Event::ID>(events.dequeue());
        if (Event::isAlert(id)) {
            processAlert(id);
        } else {
            processEvent(id);
        }
    }
}

void Ui::processEvent(Event::ID id)
{
    /*
     * We expect that alerts have already been filtered
     * and routed to processAlert()
     */

    switch (id) {
    case Event::SystemEnteredRunningState:
        pendingState = Splash;
        break;

    case Event::SystemUpdateBegin:
    case Event::SystemUpdateComplete:
    case Event::SystemUpdateFail:
        updater.init(id);
        pendingState = Updater;
        break;

    case Event::GimbalInput:
        if (canTransition(currentState, Gimbal)) {
            pendingState = Gimbal;
        }
        break;

    case Event::PairingRequest:
        if (currentState == Pairing) {
            // if a previous pairing sequence is still showing/timing out,
            // make sure we fast forward to display the correct/current state
            pairing.init();
        } else if (canTransition(currentState, Pairing)) {
            pendingState = Pairing;
        }
        break;

    case Event::ChargerConnChanged:
        topBar.onChargerChanged();
        break;

    case Event::VehicleConnectionChanged:
        telem.onVehicleConnChanged();
        topBar.onVehicleConnChanged();
        gimbal.onVehicleConnChanged();
        break;

    case Event::FlightBatteryChanged:
        telem.onFlightBatteryChanged();
        break;

    case Event::ArtooBatteryChanged:
        topBar.onBatteryChanged();
        break;

    case Event::ButtonFunctionUpdated:
        telem.onButtonFunctionsChanged();
        break;

    case Event::AltitudeUpdated:
        telem.onAltitudeChanged();
        break;

    case Event::RssiUpdated:
        topBar.onRssiChanged();
        break;

    case Event::GpsFixChanged:
        topBar.onGpsFixChanged();
        break;

    case Event::GpsNumSatellitesChanged:
        topBar.onGpsNumSatsChanged();
        break;

    case Event::GpsPositionChanged:
        telem.onGpsPositionChanged();
        break;

    case Event::ArmStateUpdated:
        arming.onArmStateChanged();
        break;

    case Event::SystemLockoutStateChanged:
        pendingState = determineState();
        break;

    // not in processAlert() since this isn't actually an alert; only dismisses alerts
    case Event::AlertRecovery:
        alertManager.dismiss();
        pendingState = determineState();
        break;

    case Event::PairingInProgress:
    case Event::PairingCanceled:
    case Event::PairingIncomplete:
    case Event::PairingSucceeded:
        pairing.onPairingEvent(id);
        break;

    case Event::SystemShutdown:
        pendingState = Shutdown;
        break;

    case Event::BatteryThermalLimitExceeded:
        // should alert user here.
        // for now, we just disable charger until it's unplugged
        break;

    case Event::FlightModeChanged:
        // Dismiss recovery alerts if the user changes flight modes
        if (alertManager.currentAlertRecovery()) {
            alertManager.dismiss();
        }

#if 0
        // maybe return gimbal to init position on LAND,
        // see https://3drsolo.atlassian.net/browse/AR-446
        switch (FlightManager::instance.flightMode()) {
        case FlightManager::LAND:
        case FlightManager::RTL:
            CameraControl::instance.returnToInit();
            break;

        default:
            break;
        }
#endif

        break;

    case Event::SoloGimbalAngleChanged:
        CameraControl::instance.onGimbalAngleChanged();
        break;

    default:
        break;
    }
}

void Ui::processAlert(Event::ID id)
{

#if 0
    // TODO: make sure this is disabled and removed after cumulative review of alerts is complete
    // For debugging purposes only, useful for displaying all alerts in series without taking into account the current state
    volatile bool debug_mode = true;
    if (debug_mode) {
        switchToFullscreenAlert(id);
        return;
    }
#endif

    switch (id) {

    /// Pre-flight - PreArm
    case Event::AltitudeCalRequired:
    case Event::CompassCalRequired:
    case Event::CompassInterference:
    case Event::LevelError:
    case Event::CalibrationFailed:
    case Event::WaitingForNavChecks:
        if (Lockout::isUnlocked()) {
            initFullscreenAlert(id);
        }
        break;

    /// Pre-flight - Arm
    case Event::CantArmWhileLeaning:
    case Event::VehicleCalibrating:
    case Event::CompassCalibrating:
    case Event::LevelCalibrating:
    case Event::CompassCalRecovery:
    case Event::ThrottleError:
    case Event::VehicleRequiresService:
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Arming) | BIT(Gimbal))) {
            initFullscreenAlert(id);
        }
        break;

    /// Pre-flight - Artoo
    case Event::FlightBatteryTooLowForTakeoff:
    case Event::UnknownBattery:
    // case Event::WaitingForSolo:           // Special case, handled elsewhere in code
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Arming) | BIT(Gimbal))) {
            initFullscreenAlert(id);
        }
        break;

    case Event::ControllerBatteryTooLowForTakeoff:
    case Event::SystemIdleWarning:
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Arming) | BIT(Gimbal) | BIT(WaitForSolo))) {
            initFullscreenAlert(id);
        }
        break;

    case Event::SoloAppConnected:
    case Event::SoloAppDisconnected:
    case Event::RecordRequiresApp:
    case Event::ControllerValueOutOfRange:
    case Event::CamControlValueOutOfRange:
    case Event::CH7low:
    case Event::CH7high:
    case Event::CH8low:
    case Event::CH8high:
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Arming) | BIT(Gimbal) | BIT(Telem))) {
            initFullscreenAlert(id);
        }
        break;

    /// Pre-flight - Gimbal
    case Event::GimbalConnected:
    case Event::GimbalNotConnected:
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Gimbal))) {
            initFullscreenAlert(id);
        }
        break;

    /// In-flight - RC
    case Event::RCFailsafe:
    case Event::RCFailsafeNoGPS:
    case Event::RCFailsafeRecovery:
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Arming) | BIT(Gimbal) | BIT(Telem) | BIT(WaitForSolo))) {  // more lenient towards RCFailsafe alerts since state information could be out of sync between controller and vehicle
            initFullscreenAlert(id);
        }
        break;

    /// In-flight - Flight battery
    case Event::FlightBatteryLow:
    case Event::FlightBatteryCritical:
    case Event::FlightBatteryFailsafe:
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Gimbal) | BIT(Telem))) {     // these currently contain in-flight specific text (e.g. "returning home") so should only display while in-flight, refer to FlightBatteryTooLowForTakeoff for pre-flight alert
            initFullscreenAlert(id);
        }
        break;

    /// In-flight - Sensors
    case Event::MaximumAltitude:
    case Event::CrashDetected:
    case Event::GpsLost:
    case Event::GpsLostManual:
    case Event::GpsLostRecovery:
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Gimbal) | BIT(Telem))) {
            initFullscreenAlert(id);
        }
        break;

    /// In-flight - Flight modes
    case Event::ShotInfoUpdated:
        /* Alert functionality no longer used, kept for reference in case it is reimplemented */
        // if (BIT(currentState) & (BIT(Arming) | BIT(Telem)  | BIT(Gimbal))) {
            // switchToFullscreenAlert(id);
            // telem.onShotInfoBannerExpired(); // make sure the shot name gets updated after the alert is displayed
            // XXX: banner no longer overlaps shot name.
        // }
        break;
    //case Event::ShotInfoUpdateFail: // TODO: delete if not using
    case Event::RTLWithoutGPS:
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Gimbal) | BIT(Telem))) {
            initFullscreenAlert(id);
        }
        break;

    /// In-flight - Artoo
    case Event::SoloConnectionPoor:
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Arming) | BIT(Gimbal) | BIT(Telem))) {
            initFullscreenAlert(id);
        }
        break;

    case Event::ControllerBatteryCritical:
    case Event::ControllerBatteryFailsafe:
    case Event::ControllerBatteryFailsafeNoGps:
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Gimbal) | BIT(Telem))) {      // these currently contain in-flight specific text (e.g. "land soon") so should only display while in-flight, refer to ControllerBatteryTooLowForTakeoff for pre-flight alert
            initFullscreenAlert(id);
        }
        break;

    case Event::ChargerConnected:
        if (BIT(currentState) & (BIT(FullscreenAlert) | BIT(Arming) | BIT(Gimbal) | BIT(Telem) | BIT(WaitForSolo))) {
            initFullscreenAlert(id);
        }
        break;

    /// Testing
    case Event::TestAlert:
        initFullscreenAlert(id);
        break;

    default:
        DBG(("[ui] Alert with event ID %d cannot be properly displayed.\n", id));
        break;
    }

    return;
}

bool Ui::canProcessAlerts()
{
    return BIT(currentState) & (BIT(Arming) | BIT(Telem) | BIT(Gimbal) | BIT(WaitForSolo) | BIT(FullscreenAlert));
}

void Ui::initFullscreenAlert(Event::ID id)
{
    if (alertManager.init(id)) {
       fullscreenmodal.init();
       pendingState = FullscreenAlert;
    }
}

void Ui::writePrimaryMsg(const char * first, const char * rest, const Gfx::FontAsset & font,
                         uint16_t * color_fg, uint16_t * color_bg,
                         unsigned y)
{
    // helper to draw primary messages with the first word in custom foreground
    // and background colors, and the remainder in the default white on black.

    unsigned x = Gfx::WIDTH/2 - (Gfx::stringWidth(first, font) + Gfx::stringWidth(rest, font))/2;

    x = Gfx::write(x, y, first, font, color_fg, color_bg);
    Gfx::write(x, y, rest, font);
}

void Ui::writeFlyBtnInstructions(const char *pre, const char *post, unsigned y)
{
    /*
     * Helper to draw some text on either side of an image,
     * mainly to provide instructions for "hold to arm/takeoff/land".
     */

    const Gfx::FontAsset & font = UiArming::InstructionFont;
    const Gfx::ImageAsset & img = Icon_Fly_Btn_for22;

    unsigned preWidth = Gfx::stringWidth(pre, font);
    unsigned postWidth = Gfx::stringWidth(post, font);
    unsigned totalWidth = preWidth + img.width + postWidth;

    uint16_t x = Gfx::WIDTH/2 - totalWidth/2;

    // clear from the top of the fly button to the top of the hint box,
    // since UiArming::writeWaitingForGps() writes multiple lines
    Gfx::fillRect(Gfx::Rect(0, y, Gfx::WIDTH, HintBoxY - y), 0x0);

    Gfx::write(x, y + FlyBtnTextOffset, pre, font);
    x += preWidth;

    Gfx::drawImage(x, y, img);
    x += img.width;

    Gfx::write(x, y + FlyBtnTextOffset, post, font);
}

void Ui::writeKillSwitchInstructions(const char *pre, const char *post, unsigned y)
{
    /*
     * Helper to provide instructions for kill switch button hold.
     *
     * 'pre' is rendered on the first line, 'post' is rendered on
     * the second line, before the button icons.
     */

    const Gfx::FontAsset & font = UiArming::InstructionFont;

    const Gfx::ImageAsset & aImg = Icon_A_Btn_for22;
    const Gfx::ImageAsset & bImg = Icon_B_Btn_for22;
    const Gfx::ImageAsset & pauseImg = Icon_Pause_for22;
    const char * plus = " + ";

    const unsigned IconOffsetY = font.height();
    const unsigned TextOffsetY = IconOffsetY + 4;

    // first line
    Gfx::writeCanvasCenterJustified(y, pre, font);

    // second line
    unsigned postWidth = Gfx::stringWidth(post, font);
    unsigned plusWidth = Gfx::stringWidth(plus, font);
    unsigned totalWidth = postWidth + aImg.width + bImg.width + plusWidth + pauseImg.width;

    unsigned x = Gfx::WIDTH/2 - totalWidth/2;

    Gfx::write(x, y+TextOffsetY, post, font);
    x += postWidth;

    Gfx::drawImage(x, y+IconOffsetY, aImg);
    x += aImg.width + 4;    // extra margin between buttons

    Gfx::drawImage(x, y+IconOffsetY, bImg);
    x += bImg.width;

    Gfx::write(x, y+TextOffsetY, plus, font);
    x += plusWidth;

    Gfx::drawImage(x, y+IconOffsetY, pauseImg);

}

void Ui::drawWaitingForSolo()
{
    Gfx::clear(0x00);

    Gfx::drawImageCanvasHCentered(55, Icon_SoloWhite);
    //Ui::writePrimaryMsg("waiting ", HelveticaNeueLTProLightGreen, "for Solo", HelveticaNeueLTProLight);
    uint16_t color_fg = UiColor::Green;
    uint16_t color_bg = UiColor::Black;
    Ui::writePrimaryMsg("waiting ", "for Solo", HelveticaNeueLTProLightLargeWhiteOnBlack, &color_fg, &color_bg);
}

void Ui::drawLockout()
{
    Gfx::clear(0x00);

    Gfx::drawImageCanvasHCentered(63, Icon_Wrench);

    const unsigned y = 126;
    unsigned x = 52;
    //x = Gfx::write(x, y, "preflight ", HelveticaNeueLTProLightGreen);
    uint16_t color_fg = UiColor::Green;
    uint16_t color_bg = UiColor::Black;
    x = Gfx::write(x, y, "Open ", HelveticaNeueLTProLightLargeWhiteOnBlack, &color_fg, &color_bg);

    Gfx::write(x, y, "Solo", HelveticaNeueLTProLightLarge);

    const Gfx::FontAsset & f = HelveticaNeueLTProRoman;
    Gfx::writeCanvasCenterJustified(168, "Solo & Controller Version Mismatch!", f);
    Gfx::writeCanvasCenterJustified(168 + f.height() + 2, "Install Latest Updates", f);
}

Ui::State Ui::determineState()
{
    /*
     * Determine the best state to return to.
     * Handy when a modal is returning, etc.
     */

    FlightManager & fm = FlightManager::instance;
    VehicleConnector & vc = VehicleConnector::instance;

    if (!Lockout::isUnlocked()) {
        return Lockout;
    }

    if (vc.state() == vc.RequestReceived) {
        return Pairing;
    }

    if (CameraControl::instance.isActive() && !gimbal.isSuppressed()) {
        return Gimbal;
    }

    if (!fm.linkIsConnected()) {
        return WaitForSolo;
    }

    if (fm.armed()) {
        return Telem;
    } else {
        return Arming;
    }
}
