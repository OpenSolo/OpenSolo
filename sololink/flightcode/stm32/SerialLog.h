#ifndef SERIAL_LOG_H
#define SERIAL_LOG_H

#include <stdint.h>
#include <pthread.h>
#include "CircularBuffer.h"

// Log all traffic to/from the STM32.
// The log is just a circular buffer to which packets are written,
// prepended by a timestamp, length, and flags:
//
// uint64_t timestamp;  usec since unix epoch
// uint16_t num_bytes;  size of packet[]
// uint8_t flags;       upstream or downstream
// uint8_t packet[];    packet bytes, as passed to or received from the slip
//                      encoder

class SerialLog
{

public:
    // Header logged for each packet.
    struct __attribute((__packed__)) PacketEntry {
        uint64_t timestamp;
        uint16_t num_bytes;
        uint8_t flags;
        uint8_t packet[0]; // variable-length
    };

    SerialLog(unsigned log_size, unsigned timeout_us = 0);

    ~SerialLog();

    // PacketEntry.flags field
    static const int PKTFLG_DIR = 0x01;  // mask
    static const int PKTFLG_UP = 0x00;   // STM32->i.MX6
    static const int PKTFLG_DOWN = 0x01; // i.MX6->STM32

    // Log a packet (PacketEntry followed by the supplied bytes)
    bool log_packet(const void *packet, unsigned num_bytes, uint8_t flags);

    // Return enable status of this logger. Logging is automatically
    // disabled when the timeout is reached.
    bool enabled(void) const
    {
        return _enabled;
    }

    // Size of logging buffer
    unsigned size(void) const
    {
        return _c_buf.size();
    }

    // Bytes used in buffer
    unsigned used(void) const
    {
        return _c_buf.used();
    }

    // Free bytes in buffer
    unsigned free(void) const
    {
        return _c_buf.free();
    }

    // Get bytes from buffer.
    bool get(void *p, unsigned num_bytes)
    {
        return _c_buf.get(p, num_bytes);
    }

    // Get structure from buffer.
    template < class type >
    bool get(type *p)
    {
        return get(p, sizeof(type));
    }

    // Discard a number of bytes from the buffer.
    bool discard(unsigned num_bytes)
    {
        return _c_buf.discard(num_bytes);
    }

private:
    CircularBuffer _c_buf;
    pthread_mutex_t _mutex;
    bool _mutex_initted;
    unsigned _timeout_us;
    uint64_t _last_up_time_us;
    bool _enabled;

    // Discard a packet
    bool discard_packet(void);
    void check_timeout(uint64_t now);

    void lock(void)
    {
        pthread_mutex_lock(&_mutex);
    }

    void unlock(void)
    {
        pthread_mutex_unlock(&_mutex);
    }
};

std::ostream &operator<<(std::ostream &, SerialLog::PacketEntry &);

// destructive dump; log is empty after this
std::ostream &operator<<(std::ostream &, SerialLog &);

#endif // SERIAL_LOG_H
