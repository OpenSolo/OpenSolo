#ifndef SET_SHOT_INFO_H
#define SET_SHOT_INFO_H

#include <iostream>
#include <stdint.h>
#include "PacketHandler.h"

// Message as sent to the STM32; message from App is in SoloMessage.h
struct __attribute((__packed__)) SetShotInfoMsg {
    // packet ID is prepended just before slip-encoding
    char descriptor[0];
    static const int descriptor_max = 64; // (does not appear in struct)
};

static const int SetShotInfoMsg_BufSize = sizeof(SetShotInfoMsg) + SetShotInfoMsg::descriptor_max;

ostream &operator<<(ostream &os, const struct SetShotInfoMsg &msg);

/***********************************************************************
Class: The SetShotInfo class.

Description:  Creates a UDP socket for SetShotInfo data.
***********************************************************************/
class SetShotInfo : public PacketHandler
{
public:
    SetShotInfo(int port);

    // This is nasty, but I need a way to get the UDP port number to which
    // downstream messages should be sent from somewhere that does not have
    // access to the stm32's setShotInfo object. This is set by the
    // constructor.
    static unsigned udpPort;
};

#endif // SET_SHOT_INFO_H
