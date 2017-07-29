
#include <iostream>
#include "packetTypes.h"
#include "net_wmm.h"
#include "SetShotInfo.h"

// Output SetShotInfoMsg to a stream in a human-readable format
ostream &operator<<(ostream &os, const struct SetShotInfoMsg &msg)
{
    os << "descriptor=\"" << msg.descriptor << '\"'; // assume EOS-terminated
    return os;
}

// UDP port on local machine where downstream SetShotInfo should be sent
unsigned SetShotInfo::udpPort = 0;

SetShotInfo::SetShotInfo(int port) : PacketHandler("127.0.0.1", port, 0x02, PKT_ID_SET_SHOT_INFO)
{

    SetShotInfo::udpPort = port;

} // SetShotInfo::SetShotInfo
