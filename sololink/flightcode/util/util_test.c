#include <stdint.h>
#include <stdio.h>
#include <unistd.h>
#include "util.h"
#include "util_test.h"

int util_test(void)
{
    int status = 0;
    uint64_t t0, t1;

    // CLOCK_REALTIME incrementing
    t0 = clock_gettime_us(CLOCK_REALTIME);
    usleep(10000);
    t1 = clock_gettime_us(CLOCK_REALTIME);
    if (t1 == t0) {
        fprintf(stderr, "util_test: CLOCK_REALTIME did not change\n");
        status = 1;
        goto util_test_exit_0;
    }

    // CLOCK_MONOTONIC incrementing
    t0 = clock_gettime_us(CLOCK_MONOTONIC);
    usleep(10000);
    t1 = clock_gettime_us(CLOCK_MONOTONIC);
    if (t1 == t0) {
        fprintf(stderr, "util_test: CLOCK_MONOTONIC did not change\n");
        status = 1;
        goto util_test_exit_0;
    }

util_test_exit_0:
    return status;

} // util_test
