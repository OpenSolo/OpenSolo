#ifndef _PAIRRES_H_
#define _PAIRRES_H_

#include <string>
#include "packetTypes.h"
#include "net_wmm.h"
#include "PacketHandler.h"

using namespace std;

/***********************************************************************
Class: The PairRes class.

Description:  Creates a UDP socket for pairRes data.
***********************************************************************/
class PairRes : public PacketHandler
{
public:
    // Constructor.  Takes an IP address, port and TOS value
    PairRes(string ipaddr, int port) : PacketHandler(ipaddr, port, 0x02, PKT_ID_PAIR_RESULT){};
};

#endif //_PAIRRES_H
