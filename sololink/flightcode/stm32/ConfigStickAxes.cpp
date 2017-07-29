
#include "packetTypes.h"
#include "ConfigStickAxes.h"

// UDP port on local machine where downstream ConfigStickAxesMsg should be sent
unsigned ConfigStickAxes::udpPort = 0;

ConfigStickAxes::ConfigStickAxes(int port) : PacketHandler("", port, 0x02, PKT_ID_CONFIG_STICK_AXES)
{
    ConfigStickAxes::udpPort = port;
}
