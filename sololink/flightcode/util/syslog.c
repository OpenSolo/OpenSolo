
#include "util.h"
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <syslog.h>
#include <time.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/times.h>
#include <sys/un.h>

// can build it in blocking mode for testing
#undef INCLUDE_BLOCKING

// can show some of the long block times with this enabled
#undef INCLUDE_HISTOGRAM

#ifndef SYSLOG_SOCK_NAME
#define SYSLOG_SOCK_NAME "/dev/log"
#endif

#ifndef SYSLOG_MSG_MAX
#define SYSLOG_MSG_MAX 512
#endif

static int log_fd = -1;
static const char *log_ident = "-";
static int log_facility = LOG_USER;
static int log_dropped = 0;
static int log_options = 0;
#define LOG_MASK_ALL 0xff
static int log_mask = LOG_MASK_ALL;

#ifdef INCLUDE_HISTOGRAM
#define hist_bins 100
static int hist[hist_bins];
static unsigned hist_dump_interval_us = 60 * 1000000;
#endif

int setlogmask(int new_mask)
{
    int old_mask = log_mask;

    if (new_mask != 0 && (new_mask & LOG_MASK_ALL) == 0)
        log_mask = new_mask;

    return old_mask;

} // setlogmask

void openlog(const char *ident, int options, int facility)
{

    int fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (fd < 0) {
        perror("openlog: socket");
        return;
    }

#ifndef INCLUDE_BLOCKING
    if (fcntl(fd, F_SETFL, O_NONBLOCK) != 0) {
        perror("openlog: fcntl");
        close(fd);
        return;
    }
#endif

    struct sockaddr_un sa_un;
    memset(&sa_un, 0, sizeof(sa_un));
    sa_un.sun_family = AF_UNIX;
    strncpy(sa_un.sun_path, SYSLOG_SOCK_NAME, sizeof(sa_un.sun_path) - 1);
    if (connect(fd, (struct sockaddr *)&sa_un, sizeof(sa_un)) != 0) {
        perror("openlog: connect");
        close(fd);
        return;
    }

    log_facility = facility;
    log_ident = ident;
    log_options = options;

    log_fd = fd;

} // openlog

void closelog(void)
{

    int fd = log_fd;

    log_fd = -1;
    log_facility = LOG_USER;
    log_ident = "-";
    log_options = 0;
    log_dropped = 0;

    close(fd);

} // closelog

// format as expected by busybox's syslogd
// return 0 on success, nonzero on error
static int vsyslog2(int sev, const char *fmt, va_list ap)
{

    if (log_fd < 0 || sev < 0 || sev > 7 || fmt == NULL)
        return 1;

    if (!(LOG_MASK(LOG_PRI(sev)) & log_mask))
        return 0;

    uint64_t now_us = clock_gettime_us(CLOCK_REALTIME);
    time_t s = now_us / 1000000;
    struct tm now_tm;
    localtime_r(&s, &now_tm);

    char msg[SYSLOG_MSG_MAX];
    char *p = msg;
    int remain = sizeof(msg) - 1; // never overwrite the last '\0'
    int n;

    memset(msg, 0, sizeof(msg));

    // Notes on error checking: snprintf(str, size, fmt, ...) returns 'size'
    // or more if there is not enough room. We detect that by updating the
    // remaining room, then not writing any more if that becomes nonpositive.
    // To guarantee the resulting string (even if truncated due to overflow)
    // is always '\0' terminated, we started with it zeroed and initialized
    // remaining room to one less than the overall size above. Error checking
    // starts after the first arbitrary-length field (ident).

    n = snprintf(p, remain, "<%d>", log_facility + sev); // 13 chars max
    remain -= n;
    p += n;

// busybox syslogd time format is different from RFC5424 - it looks for
// spaces and colons at specific offsets to know whether the message
// already has a timestamp.
#if 1
    // busybox syslogd; format-sensitive
    n = strftime(p, remain, "%h %e %T ", &now_tm); // 16 chars max
    remain -= n;
    p += n;
    // nonstandard - Milliseconds can't be printed right after the seconds,
    // since busybox syslogd looks for the space after the seconds. We can
    // stick it in like this, and although the output format is goofy, it
    // seems like good information. For example, we'd like:
    //     Sep  9 05:53:47.191 3dr_solo local0.info pixrc: ...
    // but the best we can do is:
    //     Sep  9 05:53:47 3dr_solo local0.info 191 pixrc: ...
    int us = now_us % 1000000;
    n = snprintf(p, remain, "+%03d ", us / 1000); // 5 chars
    remain -= n;
    p += n;
#else
    // RFC5424 is different (and allows fractions of a second)
    n = strftime(p, remain, "%FT%T", &now_tm);
    remain -= n;
    if (remain <= 0)
        goto vsyslog2_out;
    p += n;
    int us = now_us % 1000000;
    n = snprintf(p, remain, ".%03dZ - ", us / 1000);
    remain -= n;
    if (remain <= 0)
        goto vsyslog2_out;
    p += n;
#endif

    n = snprintf(p, remain, "%s", log_ident); // variable length
    remain -= n;
    if (remain <= 0)
        goto vsyslog2_out;
    p += n;

    if (log_options & LOG_PID) {
        n = snprintf(p, remain, "[%d]", getpid()); // 11 chars max
        remain -= n;
        if (remain <= 0)
            goto vsyslog2_out;
        p += n;
    }

    n = snprintf(p, remain, ": "); // 2 chars
    remain -= n;
    if (remain <= 0)
        goto vsyslog2_out;
    p += n;

    n = vsnprintf(p, remain, fmt, ap); // variable length
    remain -= n;
    if (remain <= 0)
        goto vsyslog2_out;
    p += n;

vsyslog2_out:

    if (log_options & LOG_PERROR)
        fprintf(stderr, "%s\n", msg);

    int len = p - msg;

#ifdef INCLUDE_HISTOGRAM
    static uint64_t hist_dump_us = 0;
    uint64_t t1_us = clock_gettime_us(CLOCK_MONOTONIC);
#endif

    // nonblocking only seems to work if send is used (not write)
    int r = send(log_fd, msg, len, 0);

#ifdef INCLUDE_HISTOGRAM
    unsigned t_us = clock_gettime_us(CLOCK_MONOTONIC) - t1_us;
    unsigned t_ms = (t_us + 500) / 1000;
    if (t_ms >= hist_bins)
        t_ms = hist_bins - 1;
    hist[t_ms]++;
    if (t1_us >= hist_dump_us) {
        if (hist_dump_us != 0) {
            printf("syslog block time histogram (msec)\n");
            int b;
            for (b = 0; b < hist_bins; b++)
                if (hist[b] != 0)
                    printf("%2d %d\n", b, hist[b]);
        }
        hist_dump_us = t1_us + hist_dump_interval_us;
        memset(hist, 0, sizeof(hist));
    }
#endif

    if (r == len)
        return 0;
    else
        return 1;

} // vsyslog2

// this function exists solely to let syslog/vsyslog log a drop message
static int syslog1(int sev, const char *fmt, ...)
{
    va_list ap;

    va_start(ap, fmt);

    int r = vsyslog2(sev, fmt, ap);

    va_end(ap);

    return r;

} // syslog1

void vsyslog(int sev, const char *fmt, va_list ap)
{

    if (log_dropped > 0 && syslog1(LOG_ERR, "dropped %d messages", log_dropped) == 0)
        log_dropped = 0;

    if (vsyslog2(sev, fmt, ap) != 0)
        log_dropped++;

} // vsyslog

void syslog(int sev, const char *fmt, ...)
{
    va_list ap;

    va_start(ap, fmt);

    vsyslog(sev, fmt, ap);

    va_end(ap);

} // syslog
