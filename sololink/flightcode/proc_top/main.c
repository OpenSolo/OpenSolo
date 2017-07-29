
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "util.h"
#include "proc_table.h"

#define MAX_PROC_ENTRIES 100
static proc_entry_t proc_table_1[MAX_PROC_ENTRIES];
static proc_entry_t proc_table_2[MAX_PROC_ENTRIES];
static proc_entry_t proc_table_3[MAX_PROC_ENTRIES];

int main(int argc, char *argv[])
{
    FILE *fp = stdout;
    int proc_entries_1;
    int proc_entries_2;
    int proc_entries_3;
    int i;
    proc_entry_t *pt1;
    proc_entry_t *pt2;
    proc_entry_t *ptx;
    int *pe1;
    int *pe2;
    int *pex;
    uint64_t now_us;
    uint64_t next_us;
    long unsigned percent;
    char time_buf[32];
    long unsigned sum;
    const unsigned interval_us = 10000000;
    const unsigned hz = 100;
    const unsigned interval_jiffies = (interval_us * hz) / 1000000;

    /* one argument; if supplied, it's the output filename */
    if (argc > 1) {
        FILE *fp2 = fopen(argv[1], "a");
        if (fp2 != NULL)
            fp = fp2;
    }

    now_us = clock_gettime_us(CLOCK_REALTIME);
    fprintf(fp, "\n");
    fprintf(fp, "%s proc_top starting\n", clock_tostr_r(now_us, time_buf));

    next_us = clock_gettime_us(CLOCK_MONOTONIC) + interval_us;

    proc_entries_1 = MAX_PROC_ENTRIES;
    if (proc_table_get(proc_table_1, &proc_entries_1) != 0) {
        fprintf(stderr, "ERROR reading proc table\n");
        exit(1);
    }

    pt1 = proc_table_1;
    pt2 = proc_table_2;
    pe1 = &proc_entries_1;
    pe2 = &proc_entries_2;

    while (1) {
        now_us = clock_gettime_us(CLOCK_MONOTONIC);
        if (next_us > now_us)
            usleep(next_us - now_us);
        next_us += interval_us;

        now_us = clock_gettime_us(CLOCK_REALTIME);

        *pe2 = MAX_PROC_ENTRIES;
        if (proc_table_get(pt2, pe2) != 0) {
            fprintf(stderr, "ERROR reading proc table\n");
            exit(1);
        }

        proc_entries_3 = MAX_PROC_ENTRIES;
        proc_table_diff(pt1, *pe1, pt2, *pe2, proc_table_3, &proc_entries_3);

        proc_table_top(proc_table_3, proc_entries_3);

        fprintf(fp, "\n");
        fprintf(fp, "%s\n", clock_tostr_r(now_us, time_buf));
        fprintf(fp, "%6s %-20s %6s %6s %4s\n", "pid", "name", "utime", "stime", "pct");
        for (i = 0; i < proc_entries_3; i++) {
#if 0
            /* Quit printing when the total time becomes zero. This prints
               a lot of nearly-idle tasks. */
            if (proc_table_3[i].utime == 0 && proc_table_3[i].stime == 0)
                break;
#endif
            sum = proc_table_3[i].utime + proc_table_3[i].stime;
            percent = (100 * sum + interval_jiffies / 2) / interval_jiffies;
#if 1
            /* Quit printing when the the percentage rounds to zero. The
               CPU usage is *not* zero, but this gives us a handful (~5)
               of tasks per dump. */
            if (percent == 0)
                break;
#endif
            fprintf(fp, "%6d %-20s %6lu %6lu %3lu%%\n", proc_table_3[i].pid, proc_table_3[i].comm,
                    proc_table_3[i].utime, proc_table_3[i].stime, percent);
        }

        fflush(fp);

        /* swap tables */

        ptx = pt1;
        pt1 = pt2;
        pt2 = ptx;

        pex = pe1;
        pe1 = pe2;
        pe2 = pex;

    } /* while (1) */

    exit(0);

} /* main */
