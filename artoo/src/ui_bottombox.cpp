#include "ui_bottombox.h"
#include "ui.h"
#include "resources-gen.h"
#include "ui_alert.h"
#include "inputs.h"
#include "sologimbal.h"

#include <stdio.h>

const UiBottomBox::Msg UiBottomBox::msgs[] = {

    /// None

    { Event::None, NoUserInput, UiAlertManager::NO_TIMEOUT, "Invalid message", NULL }, // Invalid message used in case string isn't found

    /// Pre-flight - PreArm


    /// Pre-flight - Arm


    /// Pre-flight - Artoo
    { Event::SoloAppConnected, NoUserInput, 5000, "Mobile app connected", NULL },

    { Event::SoloAppDisconnected, NoUserInput, 5000, "Mobile app disconnected", NULL },

    // Persistent alerts
    { Event::ControllerValueOutOfRange, NoUserInput, 5000, "Control stick error", "Contact 3DR Support"},
    { Event::CamControlValueOutOfRange, NoUserInput, 5000, "Manual camera controls error", "Contact 3DR Support"},

    // Unused
    { Event::RecordRequiresApp, NoUserInput, 5000, "Mobile app required for this action", NULL },

    { Event::UnknownBattery, NoUserInput, 5000, "Unknown controller battery", "Displayed level may not be accurate" },

    /// Pre-flight - Gimbal
    { Event::GimbalConnected, NoUserInput, 5000, "Solo Gimbal connected", NULL },
    { Event::GimbalNotConnected, NoUserInput, 5000, "Solo Gimbal not found", NULL },

    /// Pre-flight - GoPro


    /// In-flight - RC


    /// In-flight - Flight battery
    { Event::FlightBatteryLow, NoUserInput, 5000, "Flight battery at 25%", NULL },

    // XXX banner not shown
    { Event::FlightBatteryCritical, NoUserInput, 5000, "Return home soon", "Flight battery low" },

    { Event::FlightBatteryFailsafe, NoUserInput, UiAlertManager::NO_TIMEOUT, "Flight battery critically low", NULL },

    /// In-flight - Sensors


    /// In-flight - Flight modes
    { Event::ShotInfoUpdated, NoUserInput, 5000, "Switching to ", NULL },

    { Event::ShotInfoUpdateFail, NoUserInput, 5000, "Flight mode not available", NULL },

    { Event::RTLWithoutGPS, NoUserInput, 5000, "Cannot return to home", "without GPS" },

    /// In-flight - Artoo
    { Event::SoloConnectionPoor, NoUserInput, 5000, "Poor connection to Solo", NULL },

    { Event::ControllerBatteryCritical, NoUserInput, UiAlertManager::NO_TIMEOUT, "Controller battery low", "Please land soon" },

    // Unused
    //{ Event::ControllerBatteryFailsafe, NoUserInput, UiAlertManager::NO_TIMEOUT, "Controller battery at 0%", "Auto-landing engaged" },

    /// Misc
    { Event::LandingComplete, NoUserInput, 5000, "Landing complete", NULL },
    
    // RC Channels
    { Event::CH7low, NoUserInput, 5000, "CH-7 Off/Low", NULL },
    { Event::CH7high, NoUserInput, 5000, "CH-7 On/High", NULL },
    { Event::CH8low, NoUserInput, 5000, "CH-8 Off/Low", NULL },
    { Event::CH8high, NoUserInput, 5000, "CH-8 On/High", NULL },

    /// Testing
    { Event::TestAlert, NoUserInput, 5000, "RTL not available without GPS", "(Test test)" },

    //{ Event::WaitingForGps, NoUserInput, 5000, "Waiting for GPS", "Solo requires clear view of the sky" },
};

UiBottomBox::UiBottomBox() :
    alertFunctionsDirty(true),
    buttonFunctionsDirty(true),
    gimbalFunctionsDirty(true),
    persistFunctionsDirty(true),
    event(Event::None),
    alertStateTransition(0),
    alertWaitDurationMillis(0),
    alertNotify(false),
    displayState(DisplayNone),
    defaultDrawFunction(DrawNothing),
    activeDrawFunction(DrawNothing)
{
}

void UiBottomBox::init(DisplayState state)
{
    displayState = state;

    setDefaultDisplay();
    dirtyDisplay();
}

void UiBottomBox::update()
{
    /*
     * Either show the current alert in the bottom box,
     * or draw the button functions.
     *
     * Drawing alerts is higher priority.
     */

    // don't start timer until alert is first shown
    if (alertNotify) {
        dirtyDisplay();
        updateAlertParams();
        alertNotify = false;
    }

    if (activeDrawFunction != DrawNothing) {
        drawFunction(activeDrawFunction);
    }

    // check state again in case active drawing function timed out
    if (activeDrawFunction == DrawNothing) {
        drawFunction(defaultDrawFunction);
    }
}

void UiBottomBox::onEvent(Event::ID id) {
    // already showing this alert? nothing to do
    if (event == id) {
        return;
    }

    event = id;
    alertNotify = true;
}

void UiBottomBox::updateAlertParams()
{
    if (event != Event::None) {
        activeDrawFunction = DrawAlert;
        alertFunctionsDirty = true;
        alertStateTransition = SysTime::now();
        const Msg &msg = findMsg(event);
        ASSERT (isValid(msg));
        alertWaitDurationMillis = msg.durationMillis;
    } else {
        activeDrawFunction = DrawNothing;
    }
}

void UiBottomBox::clear(uint16_t color)
{
    Gfx::fillRect(Gfx::Rect(0, Ui::HintBoxY, Gfx::WIDTH, Gfx::HEIGHT - Ui::HintBoxY), color);
}

const UiBottomBox::Msg & UiBottomBox::findMsg(Event::ID id)
{
    for (unsigned i = 0; i < arraysize(msgs); ++i) {
        if (msgs[i].event == id)
            return msgs[i];
    }

    return msgs[MSG_INVALID];
}

void UiBottomBox::drawFunction(DrawFunction fn)
{
    switch (fn) { // TODO: this could potentially replace the idle() state
    case DrawABButtons:
        if (buttonFunctionsDirty) {
            drawButtons();
            buttonFunctionsDirty = false;
        }
        break;

    case DrawGimbalPresets:
        if (gimbalFunctionsDirty) {
            drawHintBoxAndCamera();
            gimbalFunctionsDirty = false;
        }
        break;

    case DrawGimbalNotConnected:
        if (gimbalFunctionsDirty) {
            drawGimbalNotConnected();
            gimbalFunctionsDirty = false;
        }
        break;

    case DrawAlert:
        // check to see if our alert finished
        if (alertComplete()) {
            //event = Event::None; // TODO: might be redundant
            Ui::instance.alertManager.dismiss();
            setDefaultDisplay();
            switchToDefaultDisplay();
            return;
        }

        if (alertFunctionsDirty) {
            drawBottomBox();
            alertFunctionsDirty = false;
        }
        break;

    case DrawPersistentAlert:
        // TODO: still need to implement
        break;

    case DrawInvalidFlightControls:
        if (persistFunctionsDirty) {
            drawPersistentAlert(Event::ControllerValueOutOfRange);
            persistFunctionsDirty = false;
        }
        break;

    case DrawInvalidCameraControls:
        if (persistFunctionsDirty) {
            drawPersistentAlert(Event::CamControlValueOutOfRange);
            persistFunctionsDirty = false;
        }
        break;

    default:
        // do nothing
        break;
    }
}

void UiBottomBox::setDefaultDisplay()
{
    switch (displayState) {
    case DisplayArming:
    case DisplayTelem:
        if (Inputs::isFlightControlValid()) {
            defaultDrawFunction = DrawABButtons;
        } else {
            defaultDrawFunction = DrawInvalidFlightControls;
        }
        break;

    case DisplayGimbal:
        if (Inputs::isCameraControlValid()) {
            if (SoloGimbal::instance.isConnected()) {
                defaultDrawFunction = DrawGimbalPresets;
            } else {
                defaultDrawFunction = DrawGimbalNotConnected;
            }
        } else {
            defaultDrawFunction = DrawInvalidCameraControls;
        }
        break;

    default:
        defaultDrawFunction = DrawNothing;
        break;
    }
}

void UiBottomBox::dirtyDisplay()
{
    if (activeDrawFunction != DrawNothing) {
        alertFunctionsDirty = true;
        return;
    }

    switch (displayState) {
    case DisplayArming:
    case DisplayTelem:
        buttonFunctionsDirty = true;
        persistFunctionsDirty = true;
        break;

    case DisplayGimbal:
        gimbalFunctionsDirty = true;
        persistFunctionsDirty = true;
        break;

    default:
        break;
    }
}

void UiBottomBox::switchToDefaultDisplay()
{
    activeDrawFunction = DrawNothing;
    dirtyDisplay();
}

void UiBottomBox::defaultDraw()
{
    switch (defaultDrawFunction) {
    case DrawABButtons:
        drawButtons();
        break;

    case DrawGimbalPresets:
        drawHintBoxAndCamera();
        break;

    case DrawGimbalNotConnected:
        drawGimbalNotConnected();
        break;

    case DrawPersistentAlert:
        // TODO: still need to implement
        break;

    default:
        break;
    }
}

void UiBottomBox::drawBottomBox()
{
    if (!Ui::instance.alertManager.hasAlert()) {
        return;
    }

    const UiAlertManager::Alert & alert = Ui::instance.alertManager.currentAlert();
    const Msg & msg = findMsg(event);

    drawAlertMsg(alert,msg);
}

void UiBottomBox::drawPersistentAlert(Event::ID id)
{
    const UiAlertManager::Alert & alert = Ui::instance.alertManager.getAlert(id);
    const Msg & msg = findMsg(id);

    drawAlertMsg(alert,msg);
}

void UiBottomBox::drawGimbalNotConnected()
{
    const Event::ID id = Event::GimbalNotConnected;
    const UiAlertManager::Alert & alert = Ui::instance.alertManager.getAlert(id);
    const Msg & msg = findMsg(id);

    drawAlertMsg(alert,msg);
}

void UiBottomBox::drawAlertMsg(const UiAlertManager::Alert & alert, const Msg & msg)
{
    ASSERT(isValid(msg));

    drawBannerMsg(msg.content_line1, msg.content_line2, alert.severity);

    // Check if custom message, if message is defined here then a custom behaviour will be performed, otherwise a default behaviour will be followed
#if 0 // No custom messages at this time
    switch (msg.event) {
    // Alert no longer used
    case Event::ShotInfoUpdated:{
        char strbuf[64];
        sprintf(strbuf, "Switching to %s", Ui::instance.telem.currentShotName());
        drawBannerMsg(strbuf, msg.content_line2, alert.severity);
        }break;
    // Alert no longer used
    case Event::ShotInfoUpdateFail:{
        char strbuf[64];
        sprintf(strbuf, "%s not available", Ui::instance.telem.failShotName());
        drawBannerMsg(strbuf, msg.content_line2, alert.severity);
        }break;
    // Display in a standard message format otherwise
    default:
        drawBannerMsg(msg.content_line1, msg.content_line2, alert.severity);
        break;
    }
#endif
}

void UiBottomBox::drawBannerMsg(const char* content_line1, const char* content_line2, const UiAlertManager::Severity severity)
{
    switch (severity) {
    // Display standard banner notification
    case UiAlertManager::White:
        drawBannerMsg(content_line1, content_line2, UiColor::Black, HelveticaNeueLTProRoman);
        break;

    // Display standard banner confirmation
    case UiAlertManager::Green:
        drawBannerMsg(content_line1, content_line2, UiColor::Green, HelveticaNeueLTProLightWhiteOnBlack);
        break;

    // Display standard banner warning
    case UiAlertManager::Orange:
        drawBannerMsg(content_line1, content_line2, UiColor::Orange, HelveticaNeueLTProLightWhiteOnBlack);
        break;

    // Display standard banner alert
    case UiAlertManager::Red:
        drawBannerMsg(content_line1, content_line2, UiColor::Red, HelveticaNeueLTProLightWhiteOnBlack);
        break;

    default:
        drawBannerMsg(content_line1, content_line2, UiColor::Black, HelveticaNeueLTProRoman);
        break;
    }
}

void UiBottomBox::drawBannerMsg(const char* content_line1, const char* content_line2, const uint16_t color, const Gfx::FontAsset &font)
{
    clear(color);   // draw background with appropriate background color

    if (color == UiColor::Black){
        // draw border
        Gfx::fillRect(Gfx::Rect(20, Ui::HintBoxY, Gfx::WIDTH - 40, Ui::HintBoxBorderWeight), UiColor::Gray);
    }

    uint16_t color_fg;
    uint16_t color_bg;

    // determine foreground and background colors
    if (color == UiColor::White) {
        color_fg = UiColor::White;
        color_bg = UiColor::Black;
    } else if (color == UiColor::Green) {
        color_fg = UiColor::Black;
        color_bg = UiColor::Green;
    } else if (color == UiColor::Orange) {
        color_fg = UiColor::Black;
        color_bg = UiColor::Orange;
    } else if (color == UiColor::Red) {
        color_fg = UiColor::Black;
        color_bg = UiColor::Red;
    } else {
        color_fg = UiColor::White;
        color_bg = UiColor::Black;
    }

    if (color == UiColor::White) {
        // don't use writeCanvasCenterJustified multi-line variant to preserve custom spacing
        if (!content_line2) {
            Gfx::writeCanvasCenterJustified(Ui::HintBoxYLine1of1, content_line1, font, NULL, NULL);
        } else {
            Gfx::writeCanvasCenterJustified(Ui::HintBoxYLine1of2, content_line1, font, NULL, NULL);
            Gfx::writeCanvasCenterJustified(Ui::HintBoxYLine2of2, content_line2, font, NULL, NULL);
        }
    } else {
        if (!content_line2) {
            Gfx::writeCanvasCenterJustified(Ui::HintBoxYLine1of1, content_line1, font, &color_fg, &color_bg);
        } else {
            Gfx::writeCanvasCenterJustified(Ui::HintBoxYLine1of2, content_line1, font, &color_fg, &color_bg);
            Gfx::writeCanvasCenterJustified(Ui::HintBoxYLine2of2, content_line2, font, &color_fg, &color_bg);
        }
    }
}

void UiBottomBox::drawButtons()
{
    /*
     * Draw the lower region of this view.
     *
     * Normally shows what the mapping of the A/B buttons is,
     * but can also display notifications.
     */

    clear();

    // draw border
    Gfx::fillRect(Gfx::Rect(20, Ui::HintBoxY, Gfx::WIDTH - 40, Ui::HintBoxBorderWeight), UiColor::Gray);

    static const unsigned buttonY = 208;
    drawButtonFunction(27, buttonY-5, 57, buttonY, Io::ButtonA);
    drawButtonFunction(168, buttonY-5, 198, buttonY, Io::ButtonB);
}

void UiBottomBox::drawHintBoxAndCamera()
{
    const Gfx::FontAsset & f = HelveticaNeueLTProRoman;

    unsigned y = Ui::HintBoxY;

    Gfx::fillRect(Gfx::Rect(0, y, Gfx::WIDTH, Gfx::HEIGHT - y), 0x0);
    Gfx::fillRect(Gfx::Rect(20, y, Gfx::WIDTH - 40, 1), UiColor::Gray);

    Gfx::write(20, 202, "Hold", f);
    Gfx::drawImage(61, 200, Icon_1_Btn_OnBlack);
    Gfx::write(102, 202, "or", f);
    Gfx::drawImage(125, 200, Icon_2_Btn_OnBlack);
    Gfx::write(166, 202, "to save new preset", f);
}

const Gfx::ImageAsset & UiBottomBox::btnImgForConfig(Io::ButtonID id, const ButtonFunction::Config & cfg)
{
    /*
     * return the appropriate button icon for the given button,
     * given its state in cfg.
     */

    struct ButtonFuncImages {
        const Gfx::ImageAsset & highlighted;
        const Gfx::ImageAsset & enabled;
        const Gfx::ImageAsset & disabled;
    } static const btnImgs[2] = {
    {
        Icon_New_A_Btn_On,
        Icon_New_A_Btn,
        Icon_New_A_Btn_Dis,
    },
    {
        Icon_New_B_Btn_On,
        Icon_New_B_Btn,
        Icon_New_B_Btn_Dis,
    },
};

    ASSERT(id == Io::ButtonA || id == Io::ButtonB);
    const ButtonFuncImages & bfi = btnImgs[id - Io::ButtonA];

    if (cfg.hilighted()) {
        return bfi.highlighted;
    }

    if (cfg.enabled()) {
        return bfi.enabled;
    } else {
        return bfi.disabled;
    }
}

void UiBottomBox::drawButtonFunction(unsigned imgX, unsigned imgY,
                                     unsigned strX, unsigned strY,
                                     Io::ButtonID id)
{
    const ButtonFunction::Config & cfg = ButtonFunction::get(id);

    Gfx::drawImage(imgX, imgY, btnImgForConfig(id, cfg));

    if (cfg.enabled()) {
        Gfx::write(strX, strY, cfg.descriptor, HelveticaNeueLTProRoman);
    } else {
        Gfx::write(strX, strY, cfg.descriptor, HelveticaNeueLTProRoman16DarkGrey);
    }
}

bool UiBottomBox::alertComplete() const
{
    /*
     * Is this alert done?
     * We may have been dismissed, or may have timed out.
     */

    if (alertStateTransition == 0 || event == Event::None) {
        return true;
    }

    if (alertWaitDurationMillis == UiAlertManager::NO_TIMEOUT) {
        return false;
    }

    return SysTime::now() - alertStateTransition > SysTime::msTicks(alertWaitDurationMillis);
}


