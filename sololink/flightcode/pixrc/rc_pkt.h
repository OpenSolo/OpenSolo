#ifndef RC_PKT_H
#define RC_PKT_H

/*
 * This is the RC packet structure as found in shared memory on Solo.
 * At startup, it is written by the pixrc process, UDP_task. At runtime, it
 * may be switched to be updated by some other flight-control process. It is
 * always read by the pixrc process, serial_task, which converts it to DSM and
 * writes it to the Pixhawk.
 */

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define NUM_CHANNELS 8

struct __attribute((__packed__)) rc_pkt {
    uint64_t timestamp;
    uint16_t sequence;
    uint16_t channel[NUM_CHANNELS];
};

#ifdef __cplusplus
};
#endif

#endif /* RC_PKT_H */
