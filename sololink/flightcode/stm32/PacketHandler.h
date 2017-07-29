#ifndef _PACKETHANDLER_H_
#define _PACKETHANDLER_H_

#include <string>
#include <stdint.h>
#include <netinet/in.h>

using namespace std;

/***********************************************************************
Class: The PacketHandler class.

Description:  Creates a UDP socket for data, which is sent
              bidirectionally to and from the stm32.  This is the base
              class for all types of data handled by the stm32
***********************************************************************/

class PacketHandler
{
protected:
    // Socket descriptor and the socket address
    int _sock_fd;
    struct sockaddr_in _sock;
    int _pktID;

public:
    // Constructor.  Takes an IP address, port, TOS value
    // and the packet id int
    PacketHandler(string ipaddr, int port, int tos, int pktID);

    // Handles upstream data transmission, returns the number of bytes sent
    int upHandler(char serBuf[], int len);

    // Handles downstream data transmission
    void downHandler(int ser_fd, uint32_t debug = 0);

    // The upstream thread needs to get the file descriptor
    inline int getfd(void)
    {
        return _sock_fd;
    };
};

#endif //_PACKETHANDLER_H
