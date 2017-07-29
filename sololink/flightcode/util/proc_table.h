#ifndef PROC_TABLE_H
#define PROC_TABLE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int pid; /* (1) pid %d */
#define COMM_MAX 32
    char comm[COMM_MAX]; /* (2) comm %s */
                         /* (3) state %c */
                         /* (4) ppid %d */
                         /* (5) pgrp %d */
                         /* (6) session %d */
                         /* (7) tty_nr %d */
                         /* (8) tpgid %d */
                         /* (9) flags %u */
                         /* (10) minflt %lu */
                         /* (11) cminflt %lu */
                         /* (12) majflt %lu */
                         /* (13) cmajflt %lu */
    long unsigned utime; /* (14) utime %lu */
    long unsigned stime; /* (15) stime %lu */
                         /* (16) cutime %ld */
                         /* (17) cstime %ld */
    long int priority;   /* (18) priority %ld */
    long int nice;       /* (19) nice %ld */
                         /* (20) num_threads %ld */
                         /* (21) itrealvalue %ld */
                         /* (22) starttime %llu */
                         /* (23) vsize %lu */
                         /* (24) rss %ld */
                         /* (25) rsslim %lu */
                         /* (26) startcode %lu */
                         /* (27) endcode %lu */
                         /* (28) startstack %lu */
                         /* (29) kstkesp %lu */
                         /* (30) kstkeip %lu */
                         /* (31) signal %lu */
                         /* (32) blocked %lu */
                         /* (33) sigignore %lu */
                         /* (34) sigcatch %lu */
                         /* (35) wchan %lu */
                         /* (36) nswap %lu */
                         /* (37) cnswap %lu */
                         /* (38) exit_signal %d */
                         /* (39) processor %d */
                         /* (40) rt_priority %u */
                         /* (41) policy %u */
                         /* (42) delayacct_blkio_ticks %llu */
                         /* (43) guest_time %lu */
                         /* (44) cguest_time %ld */
                         /* (45) start_data %lu */
                         /* (46) end_data %lu */
                         /* (47) start_brk %lu */
                         /* (48) arg_start %lu */
                         /* (49) arg_end %lu */
                         /* (50) env_start %lu */
                         /* (51) env_end %lu */
                         /* (52) exit_code %d */

} proc_entry_t;

extern int proc_table_get(proc_entry_t *proc_table, int *proc_entries);
extern int proc_table_diff(proc_entry_t *proc_table_1, int proc_entries_1,
                           proc_entry_t *proc_table_2, int proc_entries_2,
                           proc_entry_t *proc_table_3, int *proc_entries_3);
extern void proc_table_top(proc_entry_t *proc_table, int proc_entries);
extern void proc_table_dump(const proc_entry_t *proc_table, int proc_entries);

#ifdef __cplusplus
};
#endif

#endif /* PROC_TABLE_H */
