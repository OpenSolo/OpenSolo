#ifndef NET_STATS_H
#define NET_STATS_H

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    unsigned rx_queue;
} udp_info_t;

extern int udp_info_get(unsigned port, udp_info_t *info);

#ifdef __cplusplus
};
#endif

#endif /* NET_STATS_H */
