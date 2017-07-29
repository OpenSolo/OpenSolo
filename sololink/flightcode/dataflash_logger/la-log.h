#ifndef _LA_LOG_H
#define _LA_LOG_H

#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <syslog.h>
#include <time.h>

void la_log_syslog_open();
void la_log(int priority, const char *format, ...);
void la_log_unsuppress();

class LALog
{
public:
    LALog() : _time_period_start(time(NULL))
    {
    }
    void syslog_open();

    void log(int priority, const char *format, ...);
    void log_ap(int priority, const char *format, va_list ap);

    void unsupress();
    bool should_suppress();
    bool suppressing()
    {
        return _suppressing;
    }

private:
    // really rough rate limiting for log messages.  We could keep a
    // hash here of formats and selectively supress based on format.
    bool _suppressing = false;
    const uint8_t _time_period = 5; // seconds
    const uint8_t _max_messages_per_time_period = 10;
    uint32_t _suppressed_message_count = 0;
    uint8_t _message_count_this_time_period = 0;
    time_t _time_period_start;

    bool use_syslog = false;
};

#endif
