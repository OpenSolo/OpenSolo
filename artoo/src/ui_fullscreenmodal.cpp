#include "ui_fullscreenmodal.h"
#include "ui.h"
#include "resources-gen.h"
//#include "string.h"

UiFullScreenModal::UiFullScreenModal() :
    event(Event::None),
    startTimestamp(0),
    timeOut(0)
{
}

void UiFullScreenModal::init()
{
    if (event == Event::None) {                     // This check is not redundant than below hasAlert check since UiFullScreenModal's event will only be set to a smaller subset of all alert events
        return;
    }

    if (!Ui::instance.alertManager.hasAlert()) {
        return;
    }

    const UiAlertManager::Alert & a = Ui::instance.alertManager.currentAlert();

    // Check if this is a fullscreen alert that should be displayed
    if (!a.needsFullscreenDisplay()) {
        event = Event::None;
        return;
    }

    startTimestamp = SysTime::now();
    timeOut = a.durationMillis;

    Gfx::clear(0x0);

    drawIcons(event);
    drawAlertText(a);
}

void UiFullScreenModal::onEvent(Event::ID id)
{
    // already showing this alert? nothing to do
    if (event == id) {
        return;
    }

    event = id;
}

void UiFullScreenModal::drawSingleIcon(const Gfx::ImageAsset & img)
{
    // helper to draw images in the same format, from a common baseline
    static const unsigned iconY = 107;
    Gfx::drawImageCanvasHCentered(iconY - img.height, img);
}

void UiFullScreenModal::drawIcons(Event::ID id)
{
    switch (id) {
    case Event::AltitudeCalRequired:
        drawSingleIcon(Red_Icon_Alt);
        break;

    case Event::CompassCalRequired:
    case Event::CompassInterference:
        drawSingleIcon(Red_Icon_Com);
        break;

    case Event::LevelError:
        drawSingleIcon(Red_Icon_Level);
        break;

    case Event::CalibrationFailed:
        drawSingleIcon(Red_Icon_Exclam);
        break;

    case Event::WaitingForNavChecks:
        drawSingleIcon(Green_Icon_SensorCal);
        break;

    case Event::LevelCalibrating:
    case Event::CantArmWhileLeaning:
        drawSingleIcon(Orng_Icon_Level);
        break;

    case Event::VehicleCalibrating:
        drawSingleIcon(Orng_Icon_Exclam);
        break;

    case Event::CompassCalibrating:                  // Need: compass icon
        drawSingleIcon(Orng_Icon_Com);
        break;

    case Event::CompassCalRecovery:
        drawSingleIcon(Icon_Check);
        break;

    case Event::ThrottleError:
        drawSingleIcon(Orng_Icon_Exclam);
        break;

    case Event::VehicleRequiresService:
        drawSingleIcon(Red_Icon_Ticket);
        break;

    case Event::FlightBatteryTooLowForTakeoff:
        drawSingleIcon(Icon_FlightBattWarning_Level1);
        break;

    case Event::UnknownBattery:
        Gfx::drawImage(106, 62, Icon_ArtooforBatteryAlert);   // controller
        Gfx::drawImage(190, 58, Icon_VertBattAlertFrame);     // battery
        Gfx::drawImage(196, 76, Icon_ArtooBatt_Unkown);       // question mark
        break;

    case Event::ControllerBatteryTooLowForTakeoff:
        Gfx::drawImage(106, 62, Icon_ArtooforBatteryAlert);   // controller
        Gfx::drawImage(190, 58, Icon_VertBattAlertFrame);     // battery
        Gfx::drawImage(192, 101, Icon_VertBattRedBar);        // red bar
        break;

    case Event::SystemIdleWarning:
        Gfx::drawImage(179, 64, Icon_AutoShutdownZ);
        drawSingleIcon(Icon_ArtooNew);
        break;

    // case Event::SoloAppConnected:                    // Doesn't need icon
    // case Event::SoloAppDisconnected:                 // Doesn't need icon
    case Event::ControllerValueOutOfRange:              // Doesn't need icon
        drawSingleIcon(Red_Icon_ConDis);
        break;

    // case Event::RecordRequiresApp:                   // Doesn't need icon
    // case Event::GimbalNotConnected:                  // Doesn't need icon
    case Event::RCFailsafe:
        drawSingleIcon(Red_Icon_ConDis);
        break;

    case Event::RCFailsafeNoGPS:
        drawSingleIcon(Red_Icon_ConDis);
        break;

    case Event::RCFailsafeRecovery:
        drawSingleIcon(Grn_Icon_ConRecon);
        break;

    // case Event::FlightBatteryLow:                    // Doesn't need icon

    case Event::FlightBatteryCritical:
        drawSingleIcon(Icon_FlightBattWarning_Level1);
        break;

    case Event::FlightBatteryFailsafe:
        drawSingleIcon(Icon_FlightBattWarning_Level2);
        break;

    case Event::MaximumAltitude:
        drawSingleIcon(Red_Icon_Alt);
        break;

    case Event::CrashDetected:
        drawSingleIcon(Red_Icon_Crash);
        break;

    case Event::GpsLost:
    case Event::GpsLostManual:
        drawSingleIcon(Red_Icon_GPS);
        break;

    case Event::GpsLostRecovery:
        drawSingleIcon(Grn_Icon_GPS);
        break;

    // case Event::ShotInfoUpdated:                     // Doesn't need icon
    // case Event::ShotInfoUpdateFail:                  // Doesn't need icon
    // case Event::RTLWithoutGPS:                       // Doesn't need icon
    // case Event::SoloConnectionPoor:                  // Doesn't need icon

    case Event::ControllerBatteryCritical:
        Gfx::drawImage(106, 62, Icon_ArtooforBatteryAlert);   // controller
        Gfx::drawImage(190, 58, Icon_VertBattAlertFrame);     // battery
        Gfx::drawImage(192, 101, Icon_VertBattRedBar);        // red bar
        break;

    case Event::ControllerBatteryFailsafe:
    case Event::ControllerBatteryFailsafeNoGps:
        Gfx::drawImage(106, 62, Icon_ArtooforBatteryAlert);   // controller
        Gfx::drawImage(190, 58, Icon_VertBattAlertFrame);     // battery
        break;

    case Event::ChargerConnected:
        Ui::instance.power.drawChargerConnected();
        break; 

    default:
        break;
    }
}

void UiFullScreenModal::drawAlertText(const UiAlertManager::Alert & a)
{
    static const Gfx::FontAsset & ctxtFont = HelveticaNeueLTProRoman;

    static const unsigned warningY = 151 - HelveticaNeueLTProLightLarge.height();
    static const unsigned contextY = 176;
    static const unsigned confirmY = 211;
    static const unsigned line2Yoffset = 5;
    static const unsigned btnADismissX = 113;
    static const unsigned btnFLYDismissX = 98;

    if (a.warningFirst && a.warningRest) {
        uint16_t color_fg = a.severityColor();
        uint16_t color_bg = UiColor::Black;
        // Ui::writePrimaryMsg(a.warningFirst, a.warningFont(), a.warningRest, HelveticaNeueLTProLight, warningY);
        Ui::writePrimaryMsg(a.warningFirst, a.warningRest, HelveticaNeueLTProLightLargeWhiteOnBlack, &color_fg, &color_bg, warningY);
    }

    if (a.contextMsg) {
        Gfx::writeCanvasCenterJustified(contextY - ctxtFont.height(), a.contextMsg, ctxtFont, line2Yoffset);
    }

    switch (a.dismissBtn) {
    case UiAlertManager::DismissNone:
        if (a.confirmation) {
            Gfx::writeCanvasCenterJustified(confirmY, a.confirmation, ctxtFont);
        }
        break;
    case UiAlertManager::DismissA:{
        const char * btnADismissPrompt = "Dismiss";
        const Gfx::ImageAsset & aImg = Icon_New_A_Btn;

        Gfx::drawImage(btnADismissX, confirmY-5, aImg);
        Gfx::write(btnADismissX + aImg.width + 7, confirmY, btnADismissPrompt, ctxtFont);
        }break;
    case UiAlertManager::DismissFly:{
        const char * btnFLYDismissPrompt = "Take control";
        const Gfx::ImageAsset & flyImg = Icon_Fly_Btn_Grey_New;

        Gfx::drawImage(btnFLYDismissX, confirmY-8, flyImg);
        Gfx::write(btnFLYDismissX + flyImg.width + 7, confirmY, btnFLYDismissPrompt, ctxtFont);
        }break;
    default:
        break;
    }
}

bool UiFullScreenModal::complete() const
{
    /*
     * Is this alert done?
     * We may have been dismissed, or may have timed out.
     */

    // dismissed?
    if (event == Event::None) {
        return true;
    }

    if (timeOut == UiAlertManager::NO_TIMEOUT) {
        return false;
    }

    return SysTime::now() - startTimestamp > SysTime::msTicks(timeOut);
}



