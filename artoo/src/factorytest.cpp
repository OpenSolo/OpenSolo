#include "factorytest.h"
#include "buttonmanager.h"
#include "haptic.h"
#include "buzzer.h"
#include "ili9341parallel.h"
#include "board.h"

void FactoryTest::onOutputTest(const uint8_t *bytes, unsigned len)
{
    /*
     * Dispatched from hostprotocol.
     */

    if (len < 5) {
        return;
    }

    static const unsigned NUM_LEDS = 6;

    const uint8_t whiteLedMask = bytes[0];
    const uint8_t greenLedMask = bytes[1];
    const uint16_t buzzerHz = (bytes[3] << 8) | bytes[2];
    const uint8_t motorSeconds = bytes[4];

    Buzzer::init(440);    // only using buzzer for factory test

    for (unsigned i = 0; i < NUM_LEDS; ++i) {
        bool whiteOn = whiteLedMask & (1 << i);
        bool greenOn = greenLedMask & (1 << i);

        Button & b = ButtonManager::button(static_cast<Io::ButtonID>(Io::ButtonPower + i));
        b.setWhiteLed(whiteOn);
        b.setGreenLed(greenOn);
    }

    if (buzzerHz) {
        Buzzer::setFrequency(buzzerHz);
        Buzzer::play();
    } else {
        Buzzer::stop();
    }

    if (motorSeconds) {
        // XXX: this is probably ok, but need to verify whether
        //      we need arbitrary durations for HW testing
        Haptic::startPattern(Haptic::SingleMedium);
    }
}

void FactoryTest::onGpioTest(const uint8_t *bytes, unsigned len)
{
    /*
     * Dispatched from hostprotocol to control i/o lines during factory test.
     */

    if (len < 2) {
        return;
    }

    switch (bytes[0]) {
    case GpioLedBacklight:
        ILI9341Parallel::lcd.setBacklight(bytes[1] ? 100 : 0);
        break;

    case GpioChargerEnable:
        if (bytes[1]) {
            CHG_ENABLE_GPIO.setHigh();
        } else {
            CHG_ENABLE_GPIO.setLow();
        }
        break;
    }
}
