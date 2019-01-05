#ifndef _RC_H_
#define _RC_H_

#include <string>
#include <stdint.h>
#include <pthread.h>
#include "PacketHandler.h"

using namespace std;

/***********************************************************************
Class: The RC class.

Description:  The RC class.  Creates a UDP socket for RC channel
              transmission and handles all channel data encoding.
***********************************************************************/

class RC : public PacketHandler
{
private:
    // Packs the channel data from the STM32 with a timestamp
    // and sequence which is sent to the receiver on the Solo.
    int constructMessage(char inBuf[], char outBuf[], int inBufLen);

    // RC packet information
    int32_t _sequence;

    // If we're connected to the Solo yet.
    bool _connected;

public:
    // Constructor.  Takes an IP address, port and TOS value
    RC(string ipaddr, int port, int tos);

    // Override the uphandler
    int upHandler(char serBuf[], int len);

    // If we've got a new Solo IP address
    void setSoloIP(string *address);
};

#endif //_RC_H
