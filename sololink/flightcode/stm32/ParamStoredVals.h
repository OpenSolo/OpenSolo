#ifndef PARAM_STORED_VALS_H
#define PARAM_STORED_VALS_H

#include "PacketHandler.h"
#include "packetTypes.h"

class ParamStoredVals : public PacketHandler
{
public:
    ParamStoredVals(int port) : PacketHandler("", port, 0x02, PKT_ID_PARAM_STORED_VALS){};
};

#endif // PARAM_STORED_VALS_H
