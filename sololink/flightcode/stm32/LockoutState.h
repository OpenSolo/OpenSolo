#ifndef LOCKOUT_STATE_H
#define LOCKOUT_STATE_H

#include <iostream>
#include <stdint.h>
#include "PacketHandler.h"

// Message as sent to the STM32
struct __attribute((__packed__)) LockoutStateMsg {
    // packet ID is prepended just before slip-encoding
    uint8_t lockout; // nonzero for lockout, zero for not locked out
};

ostream &operator<<(ostream &os, const struct LockoutStateMsg &msg);

/***********************************************************************
Class: The LockoutState class.

Description:  Creates a UDP socket for LockoutState data.
***********************************************************************/
class LockoutState : public PacketHandler
{
public:
    LockoutState(int port);

    static unsigned udpPort;
};

#endif // LOCKOUT_STATE_H
