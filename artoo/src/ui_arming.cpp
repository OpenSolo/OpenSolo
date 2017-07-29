#include "ui_arming.h"
#include "ui.h"
#include "lockout.h"
#include "flightmanager.h"
#include "buttonmanager.h"
#include "battery.h"
#include "haptic.h"
#include "resources-gen.h"

const Gfx::FontAsset & UiArming::InstructionFont = HelveticaNeueLTProRoman26;

UiArming::UiArming() :
    progressClearPending(false),
    armStateDirty(true),
    waitingForGps(false),
    progressW(0),
    blinkTicker(0),
    progressBar(Ui::HintBoxY + Ui::HintBoxBorderWeight)
{
}

void UiArming::init()
{
    Gfx::clear(0x0);

    Ui::instance.topBar.init();

    if (FlightManager::instance.mustWaitForGpsToArm()) {
        writeWaitingForGps();
    } else {
        waitingForGps = false;
        writeInstructions();
    }

    UiTelemetry & telem = Ui::instance.telem;

    clearArmingProgress();
    telem.bottomBox.init(UiBottomBox::DisplayArming);
    telem.bottomBox.update();
}

void UiArming::update()
{
    const FlightManager & fm = FlightManager::instance;
    const Telemetry & t = fm.telemVals();

    Ui::instance.topBar.update();

    if (!t.flightBatteryInitialized()) {
        /*
         * if we haven't gotten a battery level from the vehicle yet,
         * we don't want to start arming.
         * would be good to communicate this to the user somehow, but
         * for now we'll just rely on them pressing FLY again if they
         * try to arm before we've gotten a battery reading.
         */
        return;
    }

    if (t.battLevel < FlightManager::BatteryLevelCritical) {
        Ui::instance.pendEvent(Event::FlightBatteryTooLowForTakeoff);
        return;
    }

    if (Battery::instance.level() <= Battery::CRITICALLY_LOW_PERCENT &&
        !Battery::instance.chargerIsPresent())
    {
        Ui::instance.pendEvent(Event::ControllerBatteryTooLowForTakeoff);
        return;
    }

    if (fm.mustWaitForGpsToArm()) {
        if (!waitingForGps) {
            writeWaitingForGps();
        }
    } else {
        // otherwise, ensure we draw the arming state
        if (waitingForGps) {
            armStateDirty = true;
        }
        waitingForGps = false;
    }

    Button & b = ButtonManager::button(Io::ButtonFly);

    // handle arming state changes
    if (armStateDirty && !waitingForGps) {
        armStateDirty = false;

        if (b.wasHeld()) {
            clearArmingProgress();
        }
        writeInstructions();
    }

    // progress bar
    if (b.isPressed()) {
        drawArmingProgress();
    } else {
        if (progressClearPending) {
            progressClearPending = false;
            clearArmingProgress();
        }
    }

    // handle FLY button led
    if (!fm.armed()) {
        b.greenLedOff();
    } else {
        const SysTime::Ticks now = SysTime::now();
        if (now - blinkTicker > SysTime::msTicks(ARMED_LED_BLINK_MILLIS)) {
            b.greenLedToggle();
            blinkTicker = now;
        }
    }

    if (progressW == 0 && !b.isPressed()) {
        Ui::instance.telem.bottomBox.update();
    }
}

void UiArming::writeWaitingForGps()
{
    uint16_t y = Ui::DefaultFlyBtnY + Ui::FlyBtnTextOffset;
    const Gfx::FontAsset & f = InstructionFont;
    const Gfx::FontAsset & f2 = HelveticaNeueLTProRoman;

    // clear from the top of the fly button to the top of the hint box
    Gfx::fillRect(Gfx::Rect(0, Ui::DefaultFlyBtnY, Gfx::WIDTH, Ui::HintBoxY - y), 0x0);

    Gfx::writeCanvasCenterJustified(y, "Searching for GPS", f);
    y += f.height() + 6;

    Gfx::writeCanvasCenterJustified(y, "may take a few minutes", f2);
    y += f2.height() + 3;

    Gfx::writeCanvasCenterJustified(y, "Solo requires a clear view of the sky", f2);

    waitingForGps = true;
}

void UiArming::writeInstructions()
{
    if (!FlightManager::instance.armed()) {
        Ui::writeFlyBtnInstructions("Hold ", " to start motors");
    } else {
        Ui::writeFlyBtnInstructions("Hold ", " to take off");
    }
}

void UiArming::onFlyButtonEvt(Button *b, Button::Event evt)
{
    /*
     * Latch button events from ISR context so we can draw them
     * in display update context.
     *
     * Previously, we left the progress bar up if the release
     * came from a hold event, signifying that the hold was
     * successful and the operation is in progress, but that
     * was found to be confusing, so just clearing on any release now.
     */

    UNUSED(b);

    switch (evt) {
    case Button::Press:
        if (waitingForGps) {
            Haptic::startPattern(Haptic::UhUh);
        }
        break;

    case Button::Release:
        progressClearPending = true;
        break;

    default:
        break;
    }
}

void UiArming::onArmFailed()
{
    progressClearPending = true;
}

void UiArming::onTakeoffFailed()
{
    progressClearPending = true;
}

void UiArming::drawArmingProgress()
{
    if (!Lockout::isUnlocked()) {
        return;
    }

    if (waitingForGps) {
        return;
    }

    Button & b = ButtonManager::button(Io::ButtonFly);
    if (b.isHeld()) {
        // only want to draw progress up until the hold event
        return;
    }

    unsigned millis = MIN(b.pressDuration() / SysTime::msTicks(1), Button::HoldMillis);
    unsigned prog = scale(millis, 0U, Button::HoldMillis, 0U, Gfx::WIDTH);

    // XXX: could keep track of where we were and just draw the delta...
    if (progressW == 0 || progressW > prog) {
        progressBar.clear();
    }

    if (progressW != prog) {
        progressW  = prog;
        progressBar.update(progressW);
    }
}

void UiArming::clearArmingProgress()
{
    /*
     * Replace the bottom area with bottomBox if we're not showing progress.
     */

    if (progressW) {
        Ui::instance.telem.bottomBox.init(UiBottomBox::DisplayArming);
    }

    progressW = 0;
}
