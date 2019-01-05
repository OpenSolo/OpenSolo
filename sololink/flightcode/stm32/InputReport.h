#ifndef INPUT_REPORT_H
#define INPUT_REPORT_H

#include <stdint.h>
#include <time.h>
#include "PacketHandler.h"
#include "TcpServer.h"

// The message as sent to clients connected to the TCP server
struct __attribute((__packed__)) InputReportMessage {
    // These fields are expected to be the only data and in this order.
    // The message constructor takes the raw message from the STM32 and picks
    // out fields to fill these in.
    uint32_t msgId;
    uint32_t length; // bytes following, i.e. 16
    uint64_t timestamp;
    uint16_t gimbalY;
    uint16_t gimbalRate;
    uint16_t battery;
    uint16_t spare; // to make it a multiple of 4

    static const uint32_t MSG_ID = 2003; // XXX move elsewhere

    InputReportMessage(uint64_t ts, const char *rawMsg)
        : msgId(MSG_ID), length(sizeof(InputReportMessage) - 8), timestamp(ts), spare(0)
    {
        // rawMsg is as produced in artoo's Inputs::producePacket() (without
        // the initial packet ID). All fields little endian.
        gimbalY = rawMsg[0] | ((uint16_t)(rawMsg[1]) << 8);
        gimbalRate = rawMsg[2] | ((uint16_t)(rawMsg[3]) << 8);
        battery = rawMsg[4] | ((uint16_t)(rawMsg[5]) << 8);
    }
};

/***********************************************************************
Class: The InputReport class.

Description: Input reports are upstream-only. A TCP server is created;
             a client connected to the server gets input reports that
             arrive from the STM32. The constructor's 'msg_rate'
             determines how many messages per second are forwarded.
             Messages come from the STM32 at 50 Hz, but for battery
             monitoring, the forwarding rate can be set much lower
             (e.g. 1 Hz).
***********************************************************************/

class InputReport : public PacketHandler
{

public:
    InputReport(int port, int msg_rate);

    int upHandler(char serBuf[], int len);

private:
    // clients attach to this to receive input reports
    TcpServer tcpServer;

    // message rate limiting
    unsigned msgInterval_us;
    uint64_t nextMsgTime_us;
};

#endif // INPUT_REPORT_H
