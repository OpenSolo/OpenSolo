#include <stdint.h>
#include "packetTypes.h"
#include "util.h"
#include "net_wmm.h"
#include "TcpServer.h"
#include "ButtonEventMessage.h"
#include "ButtonEventHandler.h"

using namespace std;

// Constructor - create and start the server that allows clients to connect
// and receive button events
ButtonEventHandler::ButtonEventHandler(int port)
    : PacketHandler("127.0.0.1", port, 0x02, PKT_ID_BUTTON_EVENT), tcpServer(port, "ButtonEvent")
{
    tcpServer.start();
}

// upHandler - called when a button event message is received from the STM32.
// Prepend the timestamp and send it to all attached clients (if any).
// CLOCK_MONOTONIC is used because it seems more likely that a client would be
// interested in intervals between button events instead of absolute button
// event time.
int ButtonEventHandler::upHandler(char serBuf[], int len)
{
    uint64_t now_us;
    now_us = clock_gettime_us(CLOCK_MONOTONIC);
    ButtonEventMessage msg(now_us, serBuf);
    tcpServer.send_clients(&msg, sizeof(msg));
    return 0;
}
