#include "selftest.h"
#include "flightmanager.h"
#include "board.h"

#include "stm32/sys.h"
#include "stm32/systime.h"

uint8_t SelfTest::result;

bool SelfTest::producePacket(HostProtocol::Packet & p)
{
    if (result == None) {
        return false;
    }

    p.delimitSlip();
    p.appendSlip(HostProtocol::SelfTest);
    p.appendSlip(result);
    p.delimitSlip();

    result = None;
    return true;
}

void SelfTest::checkForShorts()
{
    /*
     * For each run of adjacent pins, check for shorts.
     */

    // only want to do this in the factory, really
    if (FlightManager::instance.linkIsConnected()) {
        return;
    }

    GPIOPin displayConnectorPins[] = {
        DISPLAY_GPIO_NOE,
        DISPLAY_GPIO_NWE,
        DISPLAY_GPIO_CS,
        DISPLAY_GPIO_DC,
        DISPLAY_GPIO_RST,

        DISPLAY_GPIO_D0,
        DISPLAY_GPIO_D1,
        DISPLAY_GPIO_D2,
        DISPLAY_GPIO_D3,
        DISPLAY_GPIO_D4,
        DISPLAY_GPIO_D5,
        DISPLAY_GPIO_D6,
        DISPLAY_GPIO_D7,
        DISPLAY_GPIO_D8,
        DISPLAY_GPIO_D9,
        DISPLAY_GPIO_D10,
        DISPLAY_GPIO_D11,
        DISPLAY_GPIO_D12,
        DISPLAY_GPIO_D13,
        DISPLAY_GPIO_D14,
        DISPLAY_GPIO_D15,
    };

    // C0 - C5
    GPIOPin stickInputPins[] = {
        STICK_1_GPIO,
        STICK_2_GPIO,
        STICK_3_GPIO,
        STICK_0_GPIO,
        GIMBAL_Y_GPIO,
        GIMBAL_RATE_GPIO
    };

    struct PinGroup {
        GPIOPin *pins;
        unsigned len;
    } pinGroups[] = {
        { displayConnectorPins, arraysize(displayConnectorPins) },
        { stickInputPins, arraysize(stickInputPins) },
    };

    uint8_t res = Pass;

    for (unsigned i = 0; i < arraysize(pinGroups); ++i) {
        PinGroup & pg = pinGroups[i];
        if (!checkAdjacentPinsForShorts(pg.pins, pg.len)) {
            res = Fail;
            break;
        }
    }

    result = res;
    HostProtocol::instance.requestTransaction();
}

bool SelfTest::checkAdjacentPinsForShorts(GPIOPin *pins, unsigned pincount)
{
    /*
     * Drive neighbor pins low, and ensure we can pull up the pin
     * in the middle. Otherwise, we assume lines are shorted.
     */

    for (unsigned i = 0; i < pincount; ++i) {

        if (i > 0) {
            GPIOPin & left = pins[i - 1];
            left.setControl(GPIOPin::OUT_2MHZ);
            left.setLow();
        }
        if (i < pincount - 1) {
            GPIOPin & right = pins[i + 1];
            right.setControl(GPIOPin::OUT_2MHZ);
            right.setLow();
        }

        GPIOPin & pin = pins[i];
        pin.setControl(GPIOPin::IN_PULL);
        pin.pullup();

        // need to wait briefly wait for input to pull up
        const SysTime::Ticks deadline = SysTime::now() + SysTime::msTicks(5);
        while (SysTime::now() < deadline) {
            Sys::waitForInterrupt();
        }

        if (!pin.isHigh()) {
            return false;
        }
    }

    return true;
}
