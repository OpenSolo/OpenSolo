
#include <iostream>
#include "packetTypes.h"
#include "ButtonFunctionCfg.h"

// Output ButtonFunctionCfgMsg to a stream in a human-readable format
ostream &operator<<(ostream &os, const struct ButtonFunctionCfgMsg &msg)
{
    os << "button_id=" << int(msg.button_id);
    os << " button_event=" << int(msg.button_event);
    os << " shot_id=" << int(msg.shot_id);
    os << " state=" << int(msg.state);
    // is descriptor EOS-terminated?
    os << " descriptor=\"" << msg.descriptor << '\"';
    return os;
}

// UDP port on local machine where downstream ButtonFunctionCfg should be sent
unsigned ButtonFunctionCfg::udpPort = 0;

ButtonFunctionCfg::ButtonFunctionCfg(int port)
    : PacketHandler("127.0.0.1", port, 0x02, PKT_ID_BUTTON_FUNCTION_CFG)
{

    ButtonFunctionCfg::udpPort = port;

} // ButtonFunctionCfg::ButtonFunctionCfg
