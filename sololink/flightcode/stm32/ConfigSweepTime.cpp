
#include "packetTypes.h"
#include "ConfigSweepTime.h"

// UDP port on local machine where downstream ConfigSweepTime should be sent
unsigned ConfigSweepTime::udpPort = 0;

ConfigSweepTime::ConfigSweepTime(int port) : PacketHandler("", port, 0x02, PKT_ID_CONFIG_SWEEP_TIME)
{
    ConfigSweepTime::udpPort = port;
}
