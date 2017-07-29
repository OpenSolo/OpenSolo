#include <iostream>
#include <iomanip>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <arpa/inet.h>
#include "packetTypes.h"
#include "util.h"
#include "net_wmm.h"
#include "TcpServer.h"
#include "InputReport.h"

using namespace std;

// Send an InputReport to a stream in a friendly format.
ostream &operator<<(ostream &os, const struct InputReportMessage &msg)
{
    os << "msgId=" << msg.msgId;
    os << " length=" << msg.length;
    os << " timestamp=" << msg.timestamp;
    os << " gimbalY=" << msg.gimbalY;
    os << " gimbalRate=" << msg.gimbalRate;
    os << " battery=" << msg.battery;
    return os;
}

// Constructor - create and start the server that allows clients to connect
// and receive input reports
InputReport::InputReport(int port, int msg_rate)
    : PacketHandler("127.0.0.1", port, IP_TOS_DEFAULT, PKT_ID_INPUT_REPORT),
      tcpServer(port, "InputReport"), msgInterval_us(1000000 / msg_rate), nextMsgTime_us(0)
{
    tcpServer.start();
}

// upHandler - called when an inpurt report message is received from the
// STM32. Prepend the timestamp and send it to all attached clients (if any).
// The timestamp is include in case it is useful for debug/analysis, and
// CLOCK_MONOTONIC is used because it seems more likely that message intervals
// are more interesting that absolute times.
int InputReport::upHandler(char serBuf[], int len)
{
    uint64_t now_us;
    now_us = clock_gettime_us(CLOCK_MONOTONIC);
    if (now_us > nextMsgTime_us) {
        InputReportMessage msg(now_us, serBuf);
        tcpServer.send_clients(&msg, sizeof(msg));
        // the following assumes CLOCK_MONOTONIC (no jumps)
        if (nextMsgTime_us == 0)
            nextMsgTime_us = now_us;
        nextMsgTime_us += msgInterval_us;
    }
    return 0;
}
