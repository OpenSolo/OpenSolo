#ifndef LINK_PACKET_H
#define LINK_PACKET_H

#include <stdint.h>

struct LinkPacket {
    static const int MAX_PAYLOAD = 1444; /* MTU minus the header */

    uint64_t tf_recv_us;
    uint64_t tf_send_us;
    uint64_t tc_recv_us;
    uint64_t tc_send_us;
    uint64_t stm_recv_us;
    uint32_t seq;
    uint32_t data1;
    uint32_t data2;
    uint32_t data3;
    uint8_t payload[MAX_PAYLOAD];

    // everything but the payload
    static const int HDR_LEN = 56;
};

#endif // LINK_PACKET_H
