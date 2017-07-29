#ifndef UPDATER_H
#define UPDATER_H

#include <iostream>
#include <stdint.h>
#include <string.h>
#include <netdb.h>
#include "packetTypes.h"
#include "net_wmm.h"
#include "PacketHandler.h"

using namespace std;

/***********************************************************************
Class: The Updater class.

Description:  Creates a UDP socket for updater message data.
***********************************************************************/
class Updater : public PacketHandler
{
public:
    // Constructor.  Takes an IP address, port and TOS value
    Updater(string ipaddr, int port) : PacketHandler(ipaddr, port, 0x02, PKT_ID_UPDATER){};
};

#endif // UPDATER_H
