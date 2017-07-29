#include "button.h"
#include "buttonmanager.h"
#include "board.h"

Button::Button(GPIOPin p, GPIOPin active, GPIOPin backlight, Io::ButtonID bid, Polarity pol) :
    pin(p),
    activePin(active),
    backlightPin(backlight),
    polarity(pol),
    btnid(bid),
    pressTimestamp(0),
    releaseTimestamp(0),
    reportedEvents(0)
{
}

void Button::init(bool enableIsr)
{
    pin.setControl(GPIOPin::IN_PULL);
    if (polarity == ActiveLow) {
        pin.pullup();
    } else {
        pin.pulldown();
    }

    if (enableIsr) {
        pin.irqInit();
        pin.irqSetRisingEdge();
        pin.irqSetFallingEdge();
        pin.irqEnable();
    }

    if (activePin != LED_GPIO_NONE) {
        activePin.setControl(GPIOPin::OUT_2MHZ);
        activePin.setHigh();
    }

    if (backlightPin != LED_GPIO_NONE) {
        backlightPin.setControl(GPIOPin::OUT_2MHZ);
        backlightPin.setLow();
    }
}

bool Button::isr()
{
    /*
     * An edge has been detected.
     * Not doing any debounce here - TBD if we'll need to.
     *
     * Called in ISR context.
     */

    if (!pin.irqPending()) {
        return false;
    }

    pin.irqAcknowledge();

    SysTime::Ticks now = SysTime::now();

    if (isPressed()) {

        reportedEvents = 0;
        pressTimestamp = now;
        ButtonManager::dispatchEvt(this, Press);

        if (now - releaseTimestamp < SysTime::msTicks(DoubleClickGapMillis)) {
            // XXX: dispatch dc on press or release?
            ButtonManager::dispatchEvt(this, DoubleClick);
        }

    } else {
        releaseTimestamp = now;

        ButtonManager::dispatchEvt(this, Release);
        if ((releaseTimestamp - pressTimestamp) / SysTime::msTicks(1) < ClickMillis) {
            ButtonManager::dispatchEvt(this, ClickRelease);
        }
    }

    return true;
}

SysTime::Ticks Button::pressDuration() const
{
    /*
     * Return the current press duration.
     */

    if (isPressed()) {
        return SysTime::now() - pressTimestamp;
    }

    return 0;
}

void Button::pollForHold()
{
    /*
     * Called periodically when a button is pressed,
     * in order to generate hold events.
     */

    if (holdSuppressed()) {
        return;
    }

    SysTime::Ticks duration = pressDuration();

    if (!shortHoldFlagSet()) {
        if (duration > SysTime::msTicks(ShortHoldMillis)) {
            reportedEvents |= ShortHoldReported;
            ButtonManager::dispatchEvt(this, ShortHold);
        }
    }

    if (!holdFlagSet()) {
        if (duration > SysTime::msTicks(HoldMillis)) {
            reportedEvents |= HoldReported;
            ButtonManager::dispatchEvt(this, Hold);
        }
    }

    if (!longHoldFlagSet()) {
        if (duration > SysTime::msTicks(LongHoldMillis)) {
            reportedEvents |= LongHoldReported;
            ButtonManager::dispatchEvt(this, LongHold);
        }
    }
}
