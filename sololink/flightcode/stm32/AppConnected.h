#ifndef APP_CONNECTED_H
#define APP_CONNECTED_H

#include <string>
#include <pthread.h>
#include "packetTypes.h"
#include "net_wmm.h"
#include "PacketHandler.h"

/***********************************************************************
Class: The AppConnected class.

Description:  Creates a UDP socket for app-connected message data.
***********************************************************************/
class AppConnected : public PacketHandler
{
public:
    // Constructor.  Takes an IP address, port and TOS value
    AppConnected(string ipaddr, int port)
        : PacketHandler(ipaddr, port, IP_TOS_DEFAULT, PKT_ID_SOLO_APP_CONNECTION){};
};

#endif // APP_CONNECTED_H
