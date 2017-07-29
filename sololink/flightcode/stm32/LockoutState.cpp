
#include <iostream>
#include "packetTypes.h"
#include "net_wmm.h"
#include "LockoutState.h"

// Output LockoutState to a stream in a human-readable format
ostream &operator<<(ostream &os, const struct LockoutStateMsg &msg)
{
    os << "lockout=" << (msg.lockout ? "true" : "false");
    return os;
}

// UDP port on local machine where downstream LockoutState should be sent
unsigned LockoutState::udpPort = 0;

LockoutState::LockoutState(int port) : PacketHandler("127.0.0.1", port, 0x02, PKT_ID_LOCKOUT_STATE)
{
    LockoutState::udpPort = port;
}
