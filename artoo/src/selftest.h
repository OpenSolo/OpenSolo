#ifndef _SELF_TEST_H
#define _SELF_TEST_H

#include "hostprotocol.h"

#include "stm32/gpio.h"

class SelfTest
{
public:
    SelfTest();

    static void checkForShorts();
    static bool producePacket(HostProtocol::Packet & p);

private:
    enum Result {
        None,
        Pass,
        Fail
    };

    static bool checkAdjacentPinsForShorts(GPIOPin *pins, unsigned pincount);
    static uint8_t result;
};

#endif // _SELF_TEST_H
