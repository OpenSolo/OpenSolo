#ifndef SET_TELEM_UNITS_H
#define SET_TELEM_UNITS_H

#include "PacketHandler.h"

class SetTelemUnits : public PacketHandler
{
public:
    SetTelemUnits(int port);

    void set(string &setting);

    static unsigned udpPort;
};

#endif // SET_TELEM_UNITS_H
