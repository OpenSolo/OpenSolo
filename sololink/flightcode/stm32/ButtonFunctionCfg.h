#ifndef BUTTON_FUNCTION_CFG_H
#define BUTTON_FUNCTION_CFG_H

#include <iostream>
#include <stdint.h>
#include "net_wmm.h"
#include "PacketHandler.h"

// Message as sent to the STM32; message from App is in SoloMessage.h
struct __attribute((__packed__)) ButtonFunctionCfgMsg {
    // packet ID is prepended just before slip-encoding
    uint8_t button_id;
    uint8_t button_event;
    uint8_t shot_id;
    uint8_t state;
    char descriptor[0];
    static const int descriptor_max = 20; // (does not appear in struct)
};

static const int ButtonFunctionCfgMsg_BufSize =
    sizeof(ButtonFunctionCfgMsg) + ButtonFunctionCfgMsg::descriptor_max;

ostream &operator<<(ostream &os, const struct ButtonFunctionCfgMsg &msg);

/***********************************************************************
Class: The ButtonFunctionCfg class.

Description:  Creates a UDP socket for ButtonFunctionCfg data.
***********************************************************************/
class ButtonFunctionCfg : public PacketHandler
{
public:
    ButtonFunctionCfg(int port);

    // This is nasty, but I need a way to get the UDP port number to which
    // downstream messages should be sent from somewhere that does not have
    // access to the stm32's ButtonFunctionCfg object. This is set by the
    // constructor.
    static unsigned udpPort;
};

#endif // BUTTON_FUNCTION_CFG_H
