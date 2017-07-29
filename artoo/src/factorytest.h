#ifndef FACTORYTEST_H
#define FACTORYTEST_H

#include "stm32/common.h"

class FactoryTest
{
public:
    FactoryTest();  // do not implement

    static void onOutputTest(const uint8_t *bytes, unsigned len);
    static void onGpioTest(const uint8_t *bytes, unsigned len);

private:
    enum GpioTestPins {
        GpioLedBacklight,
        GpioChargerEnable,
    };
};

#endif // FACTORYTEST_H
