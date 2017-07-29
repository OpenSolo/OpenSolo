#ifndef _PAIRREQ_H_
#define _PAIRREQ_H_

#include <string>
#include "packetTypes.h"
#include "net_wmm.h"
#include "PacketHandler.h"

using namespace std;

/***********************************************************************
Class: The pairReq class.

Description:  Creates a UDP socket for pairReqest data.
***********************************************************************/
class PairReq : public PacketHandler
{
public:
    // Constructor.  Takes an IP address, port and TOS value
    PairReq(string ipaddr, int port) : PacketHandler(ipaddr, port, 0x02, PKT_ID_PAIR_REQUEST){};

    // Handles upstream data transmission
    int upHandler(char serBuf[], int len);
};

#endif //_PAIRREQ_H
