#ifndef BUTTON_H
#define BUTTON_H

/*
 * Button captures press/release events.
 */

#include "io.h"

#include "stm32/gpio.h"
#include "stm32/systime.h"
#include "stm32/sys.h"

class Button
{
public:
    enum Polarity {
        ActiveHigh, // considered to be pressed when input is high
        ActiveLow,  // considered to be pressed when input is low
    };

    enum Event {
        Press,          // edge-based
        Release,        // edge-based
        ClickRelease,   // edge/duration-based
        ShortHold,      // duration-based
        Hold,           // duration-based
        LongHold,       // duration-based
        DoubleClick,
        HoldRelease,     // edge & duration based
        LongHoldRelease // edge & duration based
    };

    static const unsigned ClickMillis = 500;
    static const unsigned ShortHoldMillis = ClickMillis;
    static const unsigned HoldMillis = 1700;
    static const unsigned LongHoldMillis = 2700;

    Button(GPIOPin p, GPIOPin active, GPIOPin backlight, Io::ButtonID bid, Polarity pol = ActiveHigh);

    void init(bool enableIsr = false);

    Io::ButtonID ALWAYS_INLINE id() const {
        return btnid;
    }

    SysTime::Ticks pressDuration() const;
    SysTime::Ticks releasedAt() const {
        return releaseTimestamp;
    }

    bool ALWAYS_INLINE isPressed() const {
        if (polarity == ActiveHigh) {
            return pin.isHigh();
        }
        return pin.isLow();
    }

    bool isHeldShort() const {
        return shortHoldFlagSet() && isPressed();
    }

    bool isHeld() const {
        return holdFlagSet() && isPressed();
    }

    bool isHeldLong() const {
        return longHoldFlagSet() && isPressed();
    }

    /*
     * wasClicked(), wasHeld() and wasHeldLong() report whether the button
     * was *previously* held, after a release.
     */

    bool wasClicked() const {
        if (isPressed()) {
            return false;
        }
        return releaseTimestamp - pressTimestamp < SysTime::msTicks(ClickMillis);
    }

    bool wasHeld() const {
        if (isPressed()) {
            return false;
        }
        return ((releaseTimestamp - pressTimestamp > SysTime::msTicks(HoldMillis)) and releaseTimestamp - pressTimestamp < SysTime::msTicks(LongHoldMillis));
    }

    bool wasHeldLong() const {
        if (isPressed()) {
            return false;
        }
        return releaseTimestamp - pressTimestamp > SysTime::msTicks(LongHoldMillis);
    }

    // optionally suppress hold events
    // only works when called after the button has been pressed

    void ALWAYS_INLINE suppressCurrentHoldEvent() {
        reportedEvents |= SuppressHold;
    }

    bool ALWAYS_INLINE holdSuppressed() const {
        return reportedEvents & SuppressHold;
    }

    /*
     * LED control.
     *
     * These will only have effect for LEDs
     * that were not specified as LED_GPIO_NONE.
     */

    void setLed(bool active) {
        if (active) {
            setLedActive();
        } else {
            setLedInactive();
        }
    }

    void setLedActive() {
        greenLedOn();
        whiteLedOff();
    }

    void setLedInactive() {
        whiteLedOn();
        greenLedOff();
    }

    void setGreenLed(bool on) {
        if (on) {
            greenLedOn();
        } else {
            greenLedOff();
        }
    }

    void ALWAYS_INLINE greenLedOn() {
        activePin.setLow();
    }

    void ALWAYS_INLINE greenLedOff() {
        activePin.setHigh();
    }

    void ALWAYS_INLINE greenLedToggle() {
        activePin.toggle();
    }

    void setWhiteLed(bool on) {
        if (on) {
            whiteLedOn();
        } else {
            whiteLedOff();
        }
    }

    void ALWAYS_INLINE whiteLedOn() {
        backlightPin.setLow();
    }

    void ALWAYS_INLINE whiteLedOff() {
        backlightPin.setHigh();
    }

    void ALWAYS_INLINE enableIRQ() {
        pin.irqEnable();
    }

    void ALWAYS_INLINE disableIRQ() {
        pin.irqEnable();
    }

    // only intended to be called by Inputs
    bool isr();
    void pollForHold();

private:
    // max duration between clicks that can be considered a double click
    static const unsigned DoubleClickGapMillis = 250;

    enum ReportedEventID {
        ShortHoldReported   = (1 << 0),
        HoldReported        = (1 << 1),
        LongHoldReported    = (1 << 2),
        SuppressHold        = (1 << 3), // suppress hold events for the current press
    };

    const GPIOPin pin;          // input
    const GPIOPin activePin;    // blue LED
    const GPIOPin backlightPin; // white pwm'd LED
    const Polarity polarity;

    const Io::ButtonID btnid;

    SysTime::Ticks pressTimestamp;
    SysTime::Ticks releaseTimestamp;
    uint32_t reportedEvents;    // bitmap of ReportedEventID

    bool ALWAYS_INLINE shortHoldFlagSet() const {
        return reportedEvents & ShortHoldReported;
    }

    bool ALWAYS_INLINE holdFlagSet() const {
        return reportedEvents & HoldReported;
    }

    bool ALWAYS_INLINE longHoldFlagSet() const {
        return reportedEvents & LongHoldReported;
    }
};

#endif // BUTTON_H
