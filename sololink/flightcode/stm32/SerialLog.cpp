
#include <stdint.h>
#include <pthread.h>
#include <iostream>
#include <iomanip>
#include "util.h"
#include "SerialLog.h"

SerialLog::SerialLog(unsigned log_size, unsigned timeout)
    : _c_buf(log_size), _mutex_initted(false), _timeout_us(timeout), _last_up_time_us(0),
      _enabled(false)
{

    if ((_c_buf.free() > 0) && (pthread_mutex_init(&_mutex, NULL) == 0)) {
        _mutex_initted = true;
        _enabled = true;
    }

} // SerialLog::SerialLog

SerialLog::~SerialLog()
{
    if (_mutex_initted) {
        pthread_mutex_destroy(&_mutex);
        _mutex_initted = false;
    }
    _enabled = false;

} // SerialLog::~SerialLog()

// Discard packet at tail.
// Assume already locked. If the log is corrupt, e.g. there is enough data for
// PacketEntry but not enough for the packet data, then this won't work (but
// it is already corrupt).
bool SerialLog::discard_packet(void)
{
    PacketEntry pe;

    // get PacketEntry
    if (!_c_buf.get(&pe))
        return false;

    // discard variable-length packet data
    return _c_buf.discard(pe.num_bytes);

} // SerialLog::discard_packet

void SerialLog::check_timeout(uint64_t now)
{

    if (_enabled && (_last_up_time_us != 0) && (_timeout_us != 0) &&
        ((now - _last_up_time_us) > _timeout_us)) {
        _enabled = false;
    }

} // SerialLog::check_timeout

bool SerialLog::log_packet(const void *packet, unsigned num_bytes, uint8_t flags)
{

    lock();

    // Timestamp logged is CLOCK_REALTIME. It is believed this is more
    // useful when looking at logs.

    // Timestamp for timeout detection is CLOCK_MONOTONIC. This is required
    // to avoid false triggers (or missed triggers) when the time changes.

    uint64_t now_mt = clock_gettime_us(CLOCK_MONOTONIC);
    uint64_t now_rt = clock_gettime_us(CLOCK_REALTIME);

    check_timeout(now_mt);

    if (!_enabled) {
        unlock();
        return false;
    }

    // discard from the tail until there is room
    unsigned total_bytes = sizeof(PacketEntry) + num_bytes;
    while (_c_buf.free() < total_bytes) {
        if (!discard_packet()) {
            unlock();
            return false;
        }
    }

    PacketEntry pe;
    pe.timestamp = now_rt;
    pe.num_bytes = num_bytes;
    pe.flags = flags;
    _c_buf.put(pe);

    _c_buf.put(packet, num_bytes);

    if ((flags & PKTFLG_DIR) == PKTFLG_UP)
        _last_up_time_us = now_mt;

    unlock();

    return true;

} // SerialLog::log_packet

std::ostream &operator<<(std::ostream &os, SerialLog::PacketEntry &pe)
{

#if 0
    // Dump raw
    const uint8_t *p = (const uint8_t *)&pe;
    os << "PacketEntry:";
    for (unsigned i = 0; i < sizeof(pe); i++)
        os << ' ' << std::setfill('0') << std::setw(2) << std::hex
           << unsigned(*p++);
#elif 1
    // Dump formatted
    os << "time=" << pe.timestamp << " bytes=" << pe.num_bytes << " flags=" << std::setfill('0')
       << std::setw(2) << std::hex << unsigned(uint8_t(pe.flags));
#endif

    os << std::setfill(' ') << std::setw(0) << std::dec;

    return os;

} // operator<<

std::ostream &operator<<(std::ostream &os, SerialLog &sl)
{

    os << "size=" << sl.size() << " used=" << sl.used() << " free=" << sl.free()
       << " enabled=" << (sl.enabled() ? "true" : "false") << std::endl;

#if 0

    // Dump raw

    static const unsigned pkt_buf_size = 16;
    char pkt_buf[pkt_buf_size];

    while (sl.used() > 0)
    {

        unsigned n = pkt_buf_size;
        if (n > sl.used())
            n = sl.used();

        sl.get(pkt_buf, n);

        for (unsigned i = 0; i < n; i++)
            os << ' ' << std::setfill('0') << std::setw(2) << std::hex
               << unsigned(uint8_t(pkt_buf[i]));
        os << std::endl;
        os << std::dec;

    } // while (sl.used()...)

#elif 1

    // Dump formatted

    static const unsigned pkt_buf_size = 256;
    uint8_t pkt_buf[pkt_buf_size];
    char time_buf[32];

    while (sl.used() >= sizeof(SerialLog::PacketEntry)) {
        SerialLog::PacketEntry pe;
        if (!sl.get(&pe))
            return os;

        unsigned keep = pe.num_bytes;
        unsigned discard = 0;
        if (keep > pkt_buf_size) {
            keep = pkt_buf_size;
            discard = pe.num_bytes - pkt_buf_size;
        }
        if (!sl.get(pkt_buf, keep))
            return os;
        if (!sl.discard(discard))
            return os;
        clock_tostr_r(pe.timestamp, time_buf);
        const char *dir =
            ((pe.flags & SerialLog::PKTFLG_DIR) == SerialLog::PKTFLG_UP) ? "UP" : "DN";
        os << time_buf << ' ' << std::setw(3) << pe.num_bytes << ' ' << dir << ':';
        for (unsigned i = 0; i < keep; i++)
            os << ' ' << std::setfill('0') << std::setw(2) << std::hex << unsigned(pkt_buf[i]);
        if (discard == 0)
            os << std::endl;
        else
            os << " ..." << std::endl; // show that we did not print it all
        os << std::setfill(' ') << std::dec;

    } // while (sl.used()...)

#endif

    return os;

} // operator<<
