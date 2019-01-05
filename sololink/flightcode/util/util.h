#ifndef UTIL_H
#define UTIL_H

#include <stdint.h>

#if (defined __MACH__ && defined __APPLE__)
typedef int clockid_t;
#define CLOCK_REALTIME 0
#define CLOCK_MONOTONIC 1
#else
#include <time.h>
#endif

#ifdef __cplusplus
extern "C" {
#endif

extern uint64_t clock_gettime_us(clockid_t clock_id);
extern void clock_settime_us(clockid_t clock_id, uint64_t t_us);
extern const char *clock_tostr_r(uint64_t t_us, char *buf);
extern const char *clock_gettime_str_r(clockid_t clock_id, char *buf);
extern int hex_aton(char a);
#define MAC_STRING_LEN 18
extern char *mac_ntoa(uint8_t *mac_bytes, char *mac_string);
extern uint8_t *mac_aton(const char *mac_string, uint8_t *mac_bytes);

#ifdef __cplusplus
};
#endif

#endif /* UTIL_H */
