#include "la-log.h"

// Caution: the functions exposed in here are called by different
// threads in the same process.

LALog lalog;

// globa functions for convenience
void la_log_syslog_open()
{
    lalog.syslog_open();
}

void la_log_unsuppress()
{
    lalog.unsupress();
}

void la_log(int priority, const char *format, ...)
{
    va_list ap;
    va_start(ap, format);
    lalog.log_ap(priority, format, ap);
    va_end(ap);
}

void LALog::syslog_open()
{
    openlog("dl", LOG_NDELAY, LOG_LOCAL1);

    use_syslog = true;
}

void LALog::log(const int priority, const char *format, ...)
{
    va_list ap;
    va_start(ap, format);
    log_ap(priority, format, ap);
    va_end(ap);
}

bool LALog::should_suppress()
{
    return _message_count_this_time_period >= _max_messages_per_time_period;
}

void LALog::unsupress()
{
    _suppressing = false;
    _message_count_this_time_period = 0;
    _time_period_start = time(NULL);
    if (_suppressed_message_count) {
        // hmmm.  recursion. hmmm.
        log(LOG_ERR, "%d messages supressed", _suppressed_message_count);
        _message_count_this_time_period--; // *cough* let one
        // *message through
        // *apart from us....
        _suppressed_message_count = 0;
    }
}
void LALog::log_ap(int priority, const char *format, va_list ap)
{
    if (time(NULL) - _time_period_start > _time_period) {
        unsupress();
    }
    if (should_suppress()) {
        _suppressing = true;
    }
    if (suppressing()) {
        _suppressed_message_count++;
        return;
    }

    _message_count_this_time_period++;

    if (use_syslog) {
        vsyslog(priority, format, ap);
    } else {
        vfprintf(stderr, format, ap);
        fprintf(stderr, "%s", "\n");
    }
}
