
#include <sys/types.h>
#include <dirent.h>

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
#include "util.h"
#include "proc_table.h"

/*
* proc_table_get - get proc table
*
* Read
*   /proc/<pid>/stat
*   /proc/<pid>/task/<tid>/stat
* and fill in proc_table.
*
* We don't get a true snapshot, since things under /proc can change while
* reading through them. Each open/read needs to handle sudden disappearance.
*
* 'man proc' describes the contents of the stat files. Example contents of
* stat files below have line breaks inserted for readability.
*
* /proc/861/stat:
*
*   861 (telem_forwarder) S 1 861 861 0 -1 4194560 427 0 4 0 217 2685 0 0 20
*   0 4 0 10613 30613504 328 4294967295 32768 84056 2125479472 2125478440
*   1993544836 0 0 0 0 4294967295 0 0 17 0 0 0 0 0 0 118784 119528 25137152
*   2125479709 2125479725 2125479725 2125479907 0
*
*   pid=861 utime=217 stime=2685
*
* /proc/861/task/@/stat:
*
*   861 (telem_forwarder) S 1 861 861 0 -1 4194560 408 0 4 0 0 13 0 0 20
*   0 4 0 10613 30613504 328 4294967295 32768 84056 2125479472 2125478440
*   1993544836 0 0 0 0 2147779492 0 0 17 0 0 0 0 0 0 118784 119528 25137152
*   2125479709 2125479725 2125479725 2125479907 0
*
*   pid=861 utime=0 stime=13
*
*   878 (telem_forwarder) S 1 861 861 0 -1 4194624 4 0 0 0 193 2595 0 0 -40
*   0 4 0 10659 30613504 328 4294967295 32768 84056 2125479472 1992428328
*   1993700708 0 0 0 0 2148340764 0 0 -1 0 39 1 0 0 0 118784 119528 25137152
*   2125479709 2125479725 2125479725 2125479907 0
*
*   pid=878 utime=193 stime=2595
*
*   879 (telem_forwarder) S 1 861 861 0 -1 4194368 5 0 0 0 14 49 0 0 -41
*   0 4 0 10659 30613504 328 4294967295 32768 84056 2125479472 1984040064
*   1995229292 0 0 0 0 2151581412 0 0 -1 0 40 1 0 0 0 118784 119528 25137152
*   2125479709 2125479725 2125479725 2125479907 0
*
*   pid=879 utime=14 stime=49
*
*   880 (telem_forwarder) S 1 861 861 0 -1 4194368 10 0 0 0 12 23 0 0 -4
*   0 4 0 10659 30613504 328 4294967295 32768 84056 2125479472 1975655240
*   1993544836 0 0 0 0 2147779492 0 0 -1 0 3 1 0 0 0 118784 119528 25137152
*   2125479709 2125479725 2125479725 2125479907 0
*
*   pid=880 utime=12 stime=23
*
* Oddly, the utimes and stimes of the tasks don't sum to the utime and stime
* of the overall process; from the above, the task sums are:
*   utime=219 stime=2680
* compared to the process's:
*   utime=217 stime=2685
*
* On success, proc_table is filled in with proc entries, proc_entries is set
* to the number of entries, and 0 is returned. On error, nonzero is returned.
*/
int proc_table_get(proc_entry_t *proc_table, int *proc_entries)
{
    int status = 0;
    int entries;
    DIR *dp1;
    struct dirent *de1;
    DIR *dp2;
    struct dirent *de2;
    int pid;
    int tid;
    char *endptr;
    char tasks_dir[32];
    char file_name[48];
    FILE *fp;
    int match;

    if (proc_table == NULL || proc_entries == NULL || *proc_entries == 0) {
        fprintf(stderr, "proc_table_get: invalid arguments\n");
        return -1;
    }

    memset(proc_table, 0, *proc_entries * sizeof(proc_entry_t));
    entries = 0;

    dp1 = opendir("/proc");
    if (dp1 == NULL) {
        fprintf(stderr, "error opening directory /proc\n");
        return -1;
    }

    /* loop through /proc/<pid>/ until the table fills up or we read all */
    while ((entries < *proc_entries) && ((de1 = readdir(dp1)) != NULL)) {
        /* quick check: ignore non-directory entries */
        if (de1->d_type != DT_DIR)
            continue;
        /* it's a pid if it can be converted to an integer */
        pid = strtol(de1->d_name, &endptr, 10);
        if (*endptr != '\0')
            continue;
        /* loop through process's tasks */
        sprintf(tasks_dir, "/proc/%d/task", pid);
        dp2 = opendir(tasks_dir);
        if (dp2 == NULL) {
            /* this happens if the process disappears between the time we find
               /proc/<pid>/ and the time we try to open /proc/<pid>/task/ */
            /*fprintf(stderr, "error opening directory %s\n", tasks_dir);*/
            continue;
        }

        /* loop over all /proc/<pid>/task/<tid>/ */
        while ((entries < *proc_entries) && ((de2 = readdir(dp2)) != NULL)) {
            /* quick check: ignore non-directory entries */
            if (de2->d_type != DT_DIR)
                continue;
            /* it's a tid if it can be converted to an integer */
            tid = strtol(de2->d_name, &endptr, 10);
            if (*endptr != '\0')
                continue;
            /* read task's stat file */
            sprintf(file_name, "/proc/%d/task/%d/stat", pid, tid);
            fp = fopen(file_name, "r");
            if (fp == NULL) {
                /* this has not been observed, but presumably could happen if
                   the process or task disappears between the time we find
                   /proc/<pid>/ or /proc/<pid>/task/<tid>, and the time we try
                   to open /proc/<pid>/task/<tid>/stat */
                /*fprintf(stderr, "error opening file %s\n", file_name);*/
                continue;
            }

            /*
             * Format as specified by 'man proc':
             * %d (%s) %c %d %d %d %d %d %u %lu
             * %lu %lu %lu %lu %lu %ld %ld %ld %ld %ld
             * %ld %llu %lu %ld %lu %lu %lu %lu %lu %lu
             * %lu %lu %lu %lu %lu %lu %lu %d %d %u
             * %u %llu %lu %ld %lu %lu %lu %lu %lu %lu
             * %lu %d
             */
            match = fscanf(fp, "%d %31s %*c %*d %*d %*d %*d %*d %*u %*u "
                               "%*u %*u %*u %lu %lu %*d %*d %ld %ld %*d "
                               "%*d %*u %*u %*d %*u %*u %*u %*u %*u %*u "
                               "%*u %*u %*u %*u %*u %*u %*u %*d %*d %*u "
                               "%*u %*u %*u %*d %*u %*u %*u %*u %*u %*u "
                               "%*u %*d",
                           &proc_table->pid, proc_table->comm, &proc_table->utime,
                           &proc_table->stime, &proc_table->priority, &proc_table->nice);
            if (match == 6) {
                proc_table++;
                entries++;
            } else {
                /* fscanf fails to match for a process name with spaces (!),
                   e.g. "ci otg thread". It may also fail if the process or
                   task disappears (that has not been observed). */
                /*fprintf(stderr, "error parsing line for %s (matched %d)\n",
                        file_name, match);*/
            }
            fclose(fp);

        } /* while (de2...) */

        closedir(dp2);

    } /* while (de1...) */

    closedir(dp1);

    *proc_entries = entries;

    return status;

} /* proc_table_get */

/*
* proc_table_diff - find diffs between two proc_tables
*
* For each pid that appears in both proc tables, create an output entry
* containing the difference between the corresponding utime and stime fields.
*
* Output table cannot be the same as either input table.
*
* Differences are computed as (table 2 value) - (table 1 value).
*/
int proc_table_diff(proc_entry_t *proc_table_1, int proc_entries_1, proc_entry_t *proc_table_2,
                    int proc_entries_2, proc_entry_t *proc_table_3, int *proc_entries_3)
{
    int entry1;
    int entry2;
    int entry3;
    int pid;

    entry3 = 0;

    /* proc_entries_1 or proc_entries_2 can be zero */
    if (proc_table_1 == NULL || proc_table_2 == NULL || proc_table_3 == NULL ||
        proc_table_3 == proc_table_1 || proc_table_3 == proc_table_2 || proc_entries_3 == NULL ||
        *proc_entries_3 == 0) {
        fprintf(stderr, "proc_table_diff: invalid arguments\n");
        return -1;
    }

    memset(proc_table_3, 0, *proc_entries_3 * sizeof(proc_entry_t));

    /* loop through proc_table_1 */
    for (entry1 = 0; entry1 < proc_entries_1; entry1++) {
        pid = proc_table_1[entry1].pid;

        /* see if there is a matching entry in proc_table_2 */
        for (entry2 = 0; entry2 < proc_entries_2; entry2++)
            if (proc_table_2[entry2].pid == pid)
                break; /* match! */

        /* was there a match? */
        if (proc_table_2[entry2].pid != pid)
            continue; /* no */

        /* proc_table_1[entry1] and proc_table_2[entry2] are the same pid */

        proc_table_3[entry3].pid = pid;
        memcpy(proc_table_3[entry3].comm, proc_table_1[entry1].comm, COMM_MAX);
        proc_table_3[entry3].utime = proc_table_2[entry2].utime - proc_table_1[entry1].utime;
        proc_table_3[entry3].stime = proc_table_2[entry2].stime - proc_table_1[entry1].stime;
        /* all other fields are left zero */

        entry3++;

        if (entry3 >= *proc_entries_3)
            break;

    } /* for (entry1...) */

    *proc_entries_3 = entry3;

    return 0;

} /* proc_table_diff */

/*
* proc_table_top - sort proc table by top CPU users
*
* The goal is to get this right the first time - no instabilities.
*
* We have around 70 entries, and most of those (80-90%) have zero CPU usage.
* An insertion sort is used: go through the array, and for each nonzero entry,
* insert it at its sorted position. This should result in an insertion for
* each entry with nonzero CPU usage; the zero entries can be skipped quickly
* and will end up at the bottom.
*/
void proc_table_top(proc_entry_t *proc_table, int proc_entries)
{
    int i, j;
    long unsigned sum1;
    long unsigned sum2;
    proc_entry_t p;

    /* loop over all entries */
    for (i = 0; i < proc_entries; i++) {
        sum1 = proc_table[i].utime + proc_table[i].stime;
        /* skip zero entries */
        if (sum1 == 0)
            continue;
        /* All entries above this one are already sorted. Insert this one at
           the sorted position (above its current position). If it should
           stay where it is, then we'll go through the j loop without doing
           the insertion. */
        for (j = 0; j < i; j++) {
            sum2 = proc_table[j].utime + proc_table[j].stime;
            if (sum2 < sum1) {
                /* insert i at j */

                /* save entry at i */
                p = proc_table[i]; /* structure copy */

                /* move down, leaving empty slot at j, overwriting slot at i */
                memmove(&proc_table[j + 1], &proc_table[j], (i - j) * sizeof(proc_entry_t));

                /* copy saved entry to j */
                proc_table[j] = p; /* structure copy */

                break; /* for j */
            }

        } /* for (j...) */

    } /* for (i...) */

} /* proc_table_top */

/*
* proc_table_dump - print proc table to stdout
*/
void proc_table_dump(const proc_entry_t *proc_table, int proc_entries)
{
    int i;

    printf("proc_table (%d entries):", proc_entries);

    for (i = 0; i < proc_entries; i++)
        printf("%6d %-20s %6lu %6lu %4ld %4ld\n", proc_table[i].pid, proc_table[i].comm,
               proc_table[i].utime, proc_table[i].stime, proc_table[i].priority,
               proc_table[i].nice);

} /* proc_table_dump */
