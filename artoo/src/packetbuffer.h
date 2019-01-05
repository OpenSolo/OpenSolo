#ifndef PACKETBUFFER_H
#define PACKETBUFFER_H

/*
 * Packet for transmitting messages to our host.
 * Packets are optionally framed via SLIP.
 */

#include <stdint.h>

#include "stm32/common.h"

namespace Slip {

static const unsigned END       = 0300; // indicates end of packet
static const unsigned ESC       = 0333; // indicates byte stuffing
static const unsigned ESC_END   = 0334; // ESC ESC_END means END data byte
static const unsigned ESC_ESC   = 0335; // ESC ESC_ESC means ESC data byte

}

template <unsigned tSize>
class PacketBuffer {

    uint8_t bytes[tSize];
    unsigned len;

public:

    PacketBuffer() :
        len(0)
    {}

    ALWAYS_INLINE void reset() {
        len = 0;
    }

    ALWAYS_INLINE bool isFull() const {
        return len == tSize;
    }

    ALWAYS_INLINE bool isEmpty() const {
        return len == 0;
    }

    ALWAYS_INLINE const uint8_t * data() const {
        return bytes;
    }

    ALWAYS_INLINE unsigned length() const {
        return len;
    }

    ALWAYS_INLINE unsigned bytesFree() const {
        return tSize - len;
    }

    ALWAYS_INLINE unsigned payloadLen() const {
        return (len == 0) ? 0 : len - 1;
    }

    ALWAYS_INLINE void append(uint8_t b) {
        ASSERT(!isFull());
        bytes[len++] = b;
    }

    ALWAYS_INLINE void append(const void *src, unsigned count) {
        ASSERT(bytesFree() >= count);
        memcpy(bytes + len, src, count);
        len += count;
    }

    void appendSlip(uint8_t b) {
        switch (b) {
        case Slip::END:
            append(Slip::ESC);
            append(Slip::ESC_END);
            break;

        case Slip::ESC:
            append(Slip::ESC);
            append(Slip::ESC_ESC);
            break;

        default:
            append(b);
        }
    }

    void appendSlip(const void *src, unsigned count) {
        const uint8_t *p = reinterpret_cast<const uint8_t*>(src);
        while (count--) {
            appendSlip(*p);
            p++;
        }
    }

    template<typename T>
    void appendItemSlip(const T & s) {
        const uint8_t *p = reinterpret_cast<const uint8_t*>(&s);
        unsigned sz = sizeof s;
        while (sz--) {
            appendSlip(*p);
            p++;
        }
    }

    ALWAYS_INLINE void delimitSlip() {
        append(Slip::END);
    }
};

#endif // PACKETBUFFER_H
