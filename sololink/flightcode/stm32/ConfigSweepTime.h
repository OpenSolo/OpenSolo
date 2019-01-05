#ifndef CONFIG_SWEEP_TIME_H
#define CONFIG_SWEEP_TIME_H

#include "PacketHandler.h"

class ConfigSweepTime : public PacketHandler
{
public:
    ConfigSweepTime(int port);

    static unsigned udpPort;
};

#endif // CONFIG_SWEEP_TIME_H
