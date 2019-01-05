#ifndef RC_IPC_H
#define RC_IPC_H

/*
 * Definitions supporting IPC sharing of RC packets. Internally, there
 * is a shared memory containing an RC packet (rc_pkt.h) and a semaphore
 * controlling access.
 */

#include "rc_pkt.h"

#ifdef __cplusplus
extern "C" {
#endif

extern void *rc_ipc_attach(int verbosity);

extern int rc_ipc_put(void *rc_ipc_id, const struct rc_pkt *pkt, int verbosity);

extern int rc_ipc_get(void *rc_ipc_id, struct rc_pkt *pkt, int verbosity);

extern int rc_ipc_detach(void *rc_ipc_id, int verbosity);

#ifdef __cplusplus
};
#endif

#endif /* RC_IPC_H */
