#ifndef _SYSINFO_H_
#define _SYSINFO_H_

#include <string>
#include "PacketHandler.h"
#include "packetTypes.h"
#include "net_wmm.h"

using namespace std;

/***********************************************************************
Class: The sysinfo class.

Description:  Creates a UDP socket for system info.
***********************************************************************/

class SysInfo : public PacketHandler
{
public:
    // Constructor.  Takes an IP address and port
    SysInfo(string ipaddr, int port) : PacketHandler(ipaddr, port, 0x03, PKT_ID_SYS_INFO){};

    // Overriden upHandler to read STM32 board data
    int upHandler(char serBuf[], int len);

    // Send a blank packet to the sysinfo port to "ping" the STM32
    void ping(void);
};

#endif //_SYSINFO_H
