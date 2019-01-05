#ifndef CONFIG_STICK_AXES_H
#define CONFIG_STICK_AXES_H

#include "PacketHandler.h"

class ConfigStickAxes : public PacketHandler
{
public:
    ConfigStickAxes(int port);

    static unsigned udpPort;
};

#endif // CONFIG_STICK_AXES_H
