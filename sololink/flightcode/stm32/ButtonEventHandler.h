#ifndef BUTTON_EVENT_HANDLER_H
#define BUTTON_EVENT_HANDLER_H

#include "PacketHandler.h"
#include "TcpServer.h"

/***********************************************************************
Class: The ButtonEventHandler class.

Description: Button events are upstream-only. A TCP server is created;
             a client connected to the server gets all button events
             that arrive from the STM32.
***********************************************************************/

class ButtonEventHandler : public PacketHandler
{

public:
    ButtonEventHandler(int port);

    int upHandler(char serBuf[], int len);

private:
    // clients attach to this to receive button events
    TcpServer tcpServer;
};

#endif // BUTTON_EVENT_HANDLER_H
