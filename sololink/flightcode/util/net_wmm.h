#ifndef NET_WMM_H
#define NET_WMM_H

#ifdef __cplusplus
extern "C" {
#endif

#define IP_TOS_DEFAULT 0   /* default (best effort) */
#define IP_TOS_BK (1 << 5) /* background, lowest */
#define IP_TOS_BE (3 << 5) /* best effort, default */
#define IP_TOS_VI (5 << 5) /* video */
#define IP_TOS_VO (7 << 5) /* voice, highest */

#ifdef __cplusplus
};
#endif

#endif /* NET_WMM_H */
