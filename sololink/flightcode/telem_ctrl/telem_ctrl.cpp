
#include <string>
#include <sys/mman.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
#include <unistd.h>
#include "INIReader.h"
#include "arp_table.h"
#include "hostapd_ctrl.h"
#include "telem_dest.h"
#include "util.h"
#include "link_packet.h"
#include "mutex.h"
#include "net_wmm.h"

/*
* telem_ctrl
*
* Receive telemetry (mavlink) via UDP from Solo, and forward to:
*   stm32 process (sends to controller's STM32)
*   tlog process (creates tlog file on controller)
*   any host detected on network that
*   - is associated with AP (e.g. app, gcs)
*   - appears in ARP table (e.g gcs running in VM)
*
* Intercept SYSTEM_TIME messages in downlink, and set system time from GPS the
* first time it is found valid.
*
* Receive telemetry in the upstream direction and forward to Solo.
*
* Log telemetry statistics periodically:
*   downlink, total per (system id, component id)
*   downlink, sequence errors per (system id, component id)
*   uplink, total messages only
*
* This consumes about 2% of the CPU when forwarding 90 packets/second.
*/

/* process priority - this is used with SCHED_FIFO. A higher number is a
   higher priority. When priorities are viewed on the target (in /proc, or
   using lsproc.py), the number seen there will be (1 - number_here), so
   e.g. if PRIORITY is 50, it will show up as priority -51. */
#define TC_MAIN_PRIORITY 58

/* instead of pulling in all the mavlink headers...*/
#define MAVLINK_MSG_ID_SYSTEM_TIME 2

/* controller sends mavlink to this port on all discovered telemetry destinations (gcs, app) */
static short telem_dest_port_hbo; /* read from config on startup */

static pthread_t tlm_ctx;

/* log stats this often */
static uint64_t log_interval_us = 10 * 1000000;

/* read from config; whether we set the system time when a GPS message
   comes through */
static int use_gps_time = true;

/* becomes true when we get a good GPS time and set the system time */
static int got_gps_time = 0;

/* TOS used for telemetry packets from controller to solo */
static int uplink_tos = IP_TOS_BE;

/* TOS used for telemetry packets from controller to any GCS (including app) */
static int gcs_tos = IP_TOS_BE;

/* This is used to prevent swamping the log with error messages if
   something unexpected happens.
   Returns -1 if we cannot log an error now, or returns the number of
   messages skipped due to rate limiting if we can, i.e. a return of
   2 means log, and we have skipped 2 messages due to rate limiting. */
static int can_log_error(uint64_t now_us)
{
    static uint64_t err_time_us = 0;           /* last time we logged */
    static uint64_t err_interval_us = 1000000; /* once per second max */
    static unsigned skipped = 0;
    unsigned ret_val;
    if ((now_us - err_time_us) < err_interval_us) {
        /* can't log */
        skipped++;
        return -1;
    }
    /* yes; say we can and set err_time_us assuming we do log something */
    err_time_us = now_us;
    ret_val = skipped;
    skipped = 0;
    return ret_val;
}

/* another process creates this file and writes Solo's IP to it when it connects */
static const char *solo_ip_file = "/var/run/solo.ip";

/* how often to check it when waiting for Solo */
static unsigned solo_ip_poll_us = 100000;

/* solo's address */
static struct sockaddr_in sa_solo;

/*
* wait_solo - wait for Solo to appear on network
*
* Wait for the solo ip file to appear, and when it does, set our global solo
* ip address from it. This is called once at startup and does not return
* until Solo is there.
*/
static void wait_solo(in_addr_t *solo_addr)
{
    FILE *fp;
    char buf[40];
    char *status;
    int err;

    while (1) {

        while ((fp = fopen(solo_ip_file, "r")) == NULL)
            usleep(solo_ip_poll_us);

        memset(buf, 0, sizeof(buf));
        status = fgets(buf, sizeof(buf) - 1, fp);

        err = errno; /* save in case of error */

        fclose(fp);

        if (status == buf) {
            *solo_addr = inet_addr(buf);
            if (*solo_addr != htonl(INADDR_NONE))
                return;
            syslog(LOG_ERR, "converting \"%s\" to ip address", buf);
        } else {
            syslog(LOG_ERR, "reading %s: %s", solo_ip_file, strerror(err));
        }
        /* loop around and try again, probably futile */
        sleep(1);
    }

} /* wait_solo */

/*
* telemetry destinations table
*/

/* how often to update the table */
static unsigned telem_dest_update_interval_s = 5;

/* instance of telemetry destinations table */
static telem_dest_table dest_table;
static pthread_mutex_t dest_table_mutex;

/* arp table, filled in by arp_table_get() each time we update the telemetry
   destinations table */
#define ARP_ENTRIES_MAX 32
static arp_entry_t arp_table[ARP_ENTRIES_MAX];

/* table of everyone associated with the AP, filled in by each time we update
   the telemetry destinations table */
#define HOSTAPD_ENTRIES_MAX 32
static hostapd_station_info_t hostapd_table[HOSTAPD_ENTRIES_MAX];

/*
* update_telem_dest - update the telemetry destinations table
*
* Add a destination when we have the ip (from arp).
* Remove a destination when the mac is not in hostapd's list and the ip is not
* in the arp table.
*
* In testing, it is now looking like IP addresses "never" disappear from the
* arp table; they are just marked with flags=0 when the entry times out (but
* the IP is still there). That means once an IP gets in the list of
* destinations, it will never be removed. For our purposes, that is okay. We
* could remove it when flags=0, but choose not to, with the fear that there
* may be some other condition that causes flags to be zero and we should not
* delete the destination.
*/
static int update_telem_dest(void *hostapd_handle)
{
    int arp_entries;
    int hostapd_entries;
    int i;

    /* get arp table */
    memset(arp_table, 0, sizeof(arp_table));
    arp_entries = ARP_ENTRIES_MAX;
    if (arp_table_get(arp_table, &arp_entries) != 0) {
        syslog(LOG_ERR, "ERROR reading arp table");
        return -1;
    }

    /* get associated stations table */
    memset(hostapd_table, 0, sizeof(hostapd_table));
    hostapd_entries = HOSTAPD_ENTRIES_MAX;
    if (hostapd_ctrl_get_stations(hostapd_handle, hostapd_table, &hostapd_entries) != 0) {
        syslog(LOG_ERR, "ERROR getting station info");
        return -1;
    }

    /* The telemetry thread reads information from dest_table. To update it,
       we copy it to work_table, update work_table, then copy work_table back
       to dest_table inside a critical section. The telemetry thread might
       hold the lock for a while as it sends a packet to all the destinations,
       but this update function should hold it only for the final memcpy. */

    telem_dest_table work_table;
    memcpy(&work_table, &dest_table, sizeof(work_table));

    /* for each entry in the arp table, if it is not in work_dest table, add it */
    arp_table_dump(LOG_DEBUG, arp_table, arp_entries);
    for (i = 0; i < arp_entries; i++) {
        int s = work_table.find_by_mac_ip(arp_table[i].mac, arp_table[i].ip);
        /* is this arp entry one of our known telemetry destinations? */
        if (s == -1) {
            struct in_addr in;
            in.s_addr = arp_table[i].ip;
            syslog(LOG_DEBUG, "arp entry %d is not a known telem dest", i);
            if (in.s_addr == sa_solo.sin_addr.s_addr) {
                syslog(LOG_DEBUG, "skipping telem dest at %s (solo)", inet_ntoa(in));
            } else if (arp_table[i].flags == 0) {
                syslog(LOG_DEBUG, "skipping telem dest at %s (flags=0)", inet_ntoa(in));
            } else {
                syslog(LOG_INFO, "adding telem dest @ %s:%d", inet_ntoa(in), telem_dest_port_hbo);
                work_table.add(arp_table[i].mac, arp_table[i].ip, telem_dest_port_hbo, gcs_tos);
            }
        } else {
            syslog(LOG_DEBUG, "arp entry %d is telem dest %d", i, s);
        }
    }

    /* for each telem dest, if its mac is not in hostapd's list and its ip is not in the arp table,
     * remove it */
    syslog(LOG_DEBUG, "%d telemetry destinations", work_table.num_dest);
    for (i = 0; i < work_table.num_dest; i++) {
        /* don't mess with destinations on localhost */
        if (work_table.dest[i].sa.sin_addr.s_addr == htonl(INADDR_LOOPBACK)) {
            syslog(LOG_DEBUG, "work_table.dest[%d] (%s:%d) is local", i,
                   inet_ntoa(work_table.dest[i].sa.sin_addr),
                   ntohs(work_table.dest[i].sa.sin_port));
            continue;
        }
        /* in hostapd's list? */
        if (hostapd_ctrl_find_by_mac(hostapd_table, hostapd_entries, work_table.dest[i].mac) !=
            -1) {
            syslog(LOG_DEBUG, "work_table.dest[%d] (%s:%d) is associated", i,
                   inet_ntoa(work_table.dest[i].sa.sin_addr),
                   ntohs(work_table.dest[i].sa.sin_port));
            continue;
        }
        /* in arp table? */
        if (arp_table_find_by_ip(arp_table, arp_entries, work_table.dest[i].sa.sin_addr.s_addr) !=
            -1) {
            syslog(LOG_DEBUG, "work_table.dest[%d] (%s:%d) is in the arp table", i,
                   inet_ntoa(work_table.dest[i].sa.sin_addr),
                   ntohs(work_table.dest[i].sa.sin_port));
            continue;
        }
        /* work_table.dest[i] is not  associated with hostapd, and is not in arp table;
           delete it */
        syslog(LOG_DEBUG, "work_table.dest[%d] is neither associated nor in arp table", i);
        syslog(LOG_INFO, "deleting telem dest at %s", inet_ntoa(work_table.dest[i].sa.sin_addr));
        work_table.delete_by_index(i);
        i--; /* the next entry is at [i] now */
    }

    mutex_lock(&dest_table_mutex, NULL);

    memcpy(&dest_table, &work_table, sizeof(dest_table));

    mutex_unlock(&dest_table_mutex);

    dest_table.check();

    return 0;

} /* update_telem_dest */

/*
* sources[] table - one entry per mavlink source, containing expected next
* sequence number and basic stats (packet count, error count).
*
* Normally we only have two or three sources (pixhawk, rssi process, maybe
* gimbal).
*
* It has been observed in the past that we can get total garbage from Pixhawk
* (don't know if that can still happen). If that happens, the sources table
* will fill up with junk (bogus sys_id, comp_id), then we will stop adding
* new sources (they just won't be checked). Then the next time stats are
* printed (e.g. every 10 seconds), we'll print meaningless stats about the
* garbage, clear the table, and start over. If the junk goes away, this should
* recover.
*/

#define SOURCE_MAX 32

typedef struct {
    uint8_t sys_id;
    uint8_t comp_id;
    uint8_t seq;
    unsigned pkt_cnt;
    unsigned err_cnt;
} source_info_t;

static source_info_t sources[SOURCE_MAX];
static int num_sources = 0;

static void source_set(source_info_t *si, uint8_t sys_id, uint8_t comp_id, uint8_t seq)
{
    si->sys_id = sys_id;
    si->comp_id = comp_id;
    si->seq = seq;
    si->pkt_cnt = 1;
    si->err_cnt = 0;
}

/*
* source_check - check sequence number of a message
*
* Also maintain basic statistics on messages from each source (packet count,
* error count).
*
* Return zero if sequence correct, nonzero if sequence error
*/
static int source_check(uint8_t sys_id, uint8_t comp_id, uint8_t seq)
{
    int i;
    uint16_t new_id = (uint16_t(sys_id) << 8) | comp_id;

    /* find source */
    for (i = 0; i < num_sources; i++) {
        uint16_t old_id = (uint16_t(sources[i].sys_id) << 8) | sources[i].comp_id;
        if (old_id == new_id) {
            sources[i].pkt_cnt++;
            sources[i].seq += 1; /* expected sequence */
            if (seq == sources[i].seq)
                return 0; /* correct */
            /* sequence error */
            sources[i].err_cnt++;
            sources[i].seq = seq; /* set for next time */
            return -1;
        } else if (old_id > new_id)
            break; /* insert new one at [i] */
    }
    /* didn't find src_id, comp_id */
    /* i == num_source if we got to the end,
       or is index where we want to insert */
    if (num_sources < SOURCE_MAX) {
        /* add/insert new source */
        memmove(&sources[i + 1], &sources[i], (num_sources - i) * sizeof(source_info_t));
        source_set(&sources[i], sys_id, comp_id, seq);
        num_sources++;
    }
    return 0;
}

/*
* sources_clear - clear sources and stats
*
* This is called after each time stats are printed. There are two reasons:
* 1. So stats are deltas since the last printout, and
* 2. So if we get junk and fill up the sources[] table, it will be cleared
*    the next time we print stats.
*/
static void sources_clear(void)
{
    memset(sources, 0, sizeof(sources));
    num_sources = 0;
}

/*
* create_and_bind - create a socket and bind it to a local UDP port
*
* Used to create the socket on the upstream side that receives from and sends
* to Solo, and the socket on the downstream side that receives from and sends
* to everything else (stm32, tlog, app, gcs).
*
* Returns fd on success, -1 on error.
*/
int create_and_bind(short port_hbo, int tos)
{
    int fd;
    struct sockaddr_in sa;

    fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        perror("socket");
        return -1;
    }

    memset(&sa, 0, sizeof(sa));
    sa.sin_family = AF_INET;
    sa.sin_addr.s_addr = htonl(INADDR_ANY);
    sa.sin_port = htons(port_hbo);
    if (bind(fd, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
        perror("bind");
        close(fd);
        return -1;
    }

    if (setsockopt(fd, IPPROTO_IP, IP_TOS, &tos, sizeof(tos)) != 0) {
        perror("setsockopt");
        close(fd);
        return -1;
    }

    return fd;

} /* create_and_bind */

/*
* lock_mem - force allocation of stack and lock the pages
*/
static void lock_mem(uint32_t size)
{
    char stack[size];
    mlockall(MCL_CURRENT | MCL_FUTURE);
    memset(stack, 0, sizeof(stack));
}

#define TELEM_PKT_MAX 512

/*
* tlm_main
*/
static void *tlm_main(void *)
{
    int fd_solo;
    fd_set fds;
    int nfds = 0;
    int res;
    uint64_t now_us;
    uint8_t pkt[TELEM_PKT_MAX];
    LinkPacket packet;
    uint32_t link_next_seq = 0;
    struct sockaddr_in sa;
    socklen_t sa_len;
    int i;
    uint64_t log_time_us;
    uint32_t pkts_down_total = 0;
    uint32_t pkts_up_total = 0;
    uint32_t select_timeout = 0;
    struct timeval timeout;
    const uint64_t dropped_log_interval_us =
        1000000;                 // (1 sec) minimum time between logging drop events
    uint64_t dropped_log_us = 0; // last time we logged a drop event
    unsigned dropped_total = 0;  // total dropped since last time we logged

    /* Solo socket. This is where downlink packets arrive. */
    fd_solo = create_and_bind(telem_dest_port_hbo, uplink_tos);
    if (fd_solo < 0) {
        syslog(LOG_CRIT, "can't create solo socket and bind to port %d", telem_dest_port_hbo);
        return NULL;
    }

    /* Clear mavlink sources and stats. */
    sources_clear();

    /* Memory lock size should be tuned, but the value passed here is
       in addition to main's stack, and it is the only thing that uses
       significant stack. */
    lock_mem(32768);

    now_us = clock_gettime_us(CLOCK_MONOTONIC);
    log_time_us = now_us + log_interval_us;

    /* Wait for a packet to arrive in either the upstream or downstream
       direction, and forward it as needed. Also periodically check to see if
       there are any new destinations on the network where the downlink should
       go. Downlink goes to everyone on the network, port telem_dest_port_hbo. */
    while (1) {
        uint64_t t1_us;
        uint64_t t2_us;

        /* Wait for a packet, or time out if no packets arrive so we always
           periodically log status and check for new destinations. Downlink
           packets are on the order of 100/sec, so the timeout is such that
           we don't expect timeouts unless solo stops sending packets. We
           almost always get a packet with a 200 msec timeout, but not with
           a 100 msec timeout. (Timeouts don't really matter though.) */

        FD_ZERO(&fds);
        nfds = 0;
        FD_SET(fd_solo, &fds);
        if (fd_solo >= nfds)
            nfds = fd_solo + 1;

        mutex_lock(&dest_table_mutex, NULL);

        for (i = 0; i < dest_table.num_dest; i++) {
            int fd = dest_table.dest[i].fd;
            FD_SET(fd, &fds);
            if (fd >= nfds)
                nfds = fd + 1;
        }

        mutex_unlock(&dest_table_mutex);

        timeout.tv_sec = 0;
        timeout.tv_usec = 200000;

        t1_us = clock_gettime_us(CLOCK_MONOTONIC);

        /* The time from returning from select in loop N to getting to here in
           loop N+1 should be very short. 100 msec should be far far longer
           than we need; we are looking for unexpected blocks or stalls here. */
        if ((t1_us - now_us) > 100000) {
            syslog(LOG_ERR, "loop: took %u usec", (unsigned)(t1_us - now_us));
        }

        /* This select is intended to be the only place this thread blocks, so
           is the only place where the telemetry destinations table should get
           updated.
           Don't count on that (blocking has showed up in unexpected places),
           but do this select while not holding the telemetry dests table mutex
           in case it is int fact true.
           If a telemetry dest goes away, its fd is closed, which should have
           no effect on the select for Linux, but is unportable behavior. */
        res = select(nfds, &fds, NULL, NULL, &timeout);

        now_us = clock_gettime_us(CLOCK_MONOTONIC);

        /* select should time out in 200 msec at the most; warn if it blocks
           longer than that */
        if ((now_us - t1_us) > 250000)
            syslog(LOG_ERR, "select: blocked %u usec", (unsigned)(now_us - t1_us));

        if (res < 0) {
            int skipped;
            if ((skipped = can_log_error(now_us)) >= 0)
                syslog(LOG_ERR, "[%u] select: %s", skipped, strerror(errno));
            /* this sleep is to avoid soaking the CPU if select starts
               returning immediately for some reason */
            usleep(10000);
            continue;
        }

        if (res == 0) {
            /* timeout */
            select_timeout++;
            /* Could skip checking the two fds, but we need to continue on
               below that, possibly checking for new telemetry destinations
               or logging stats. */
        }

        /* Either have a packet ready in one of the sockets, or timed out.
           Processing one packet per loop makes it so neither uplink nor
           downlink can starve the other, e.g. if we get a huge burst of
           downlink packets, uplink still gets to send one packet per downlink
           packet if it wants to (vs no uplink at all until we work through
           the downlink burst). */

        /* check for downstream packets */

        if (FD_ISSET(fd_solo, &fds)) {
            /* packet from solo */
            sa_len = sizeof(sa);
            t1_us = clock_gettime_us(CLOCK_MONOTONIC);
            res = recvfrom(fd_solo, &packet, sizeof(packet), 0, (struct sockaddr *)&sa, &sa_len);
            t2_us = clock_gettime_us(CLOCK_MONOTONIC);
            /* recvfrom should not block; warn if it does */
            if ((t2_us - t1_us) > 10000)
                syslog(LOG_ERR, "recvfrom(solo): blocked %u usec", (unsigned)(t2_us - t1_us));

            packet.tc_recv_us = now_us; // timestamp when it was received in controller

            // initialize sequence check if this is the first downstream packet
            if (link_next_seq == 0)
                link_next_seq = packet.seq;

            // check sequence
            // downlink packets dropped between this packet and the previous one (normally zero)
            unsigned dropped = packet.seq - link_next_seq;
            // total dropped since last time we logged a message
            dropped_total += dropped;

            // Should we log? Yes, if we have seen drops and have not logged too recently.
            if ((dropped_total > 0) && ((now_us - dropped_log_us) >= dropped_log_interval_us)) {
                syslog(LOG_ERR, "dropped %u downlink packets", dropped_total);
                dropped_total = 0;
                dropped_log_us = now_us;
            }

            link_next_seq = packet.seq + 1;

            pkts_down_total++;

            /* We get one mavlink packet per udp datagram. Sanity checks here
               are: must be from solo's IP and have a valid mavlink header. */

            if (sa.sin_addr.s_addr != sa_solo.sin_addr.s_addr) {
                int skipped;
                if ((skipped = can_log_error(now_us)) >= 0)
                    syslog(LOG_ERR, "[%u] received packet not from solo (0x%08x)", skipped,
                           sa.sin_addr.s_addr);
            } else if (res < (LinkPacket::HDR_LEN + 8)) {
                int skipped;
                if ((skipped = can_log_error(now_us)) >= 0)
                    syslog(LOG_ERR, "[%u] received runt packet (%d bytes)", skipped, res);
            } else if (packet.payload[0] != 0xFE && packet.payload[0] != 0xFD) {
                int skipped;
                if ((skipped = can_log_error(now_us)) >= 0)
                    syslog(LOG_ERR, "[%u] received bad magic (0x%02x)", skipped, packet.payload[0]);
            }
            /*
            else if (packet.payload[1] != (res - LinkPacket::HDR_LEN - 8))
            {
                int skipped;
                if ((skipped = can_log_error(now_us)) >= 0)
                    syslog(LOG_ERR, "[%u] inconsistent length (%u, %u)",
                           skipped, packet.payload[1], res);
            }
            */
            else {
                /* packet is from solo and passes sanity checks */

                /* Run through the entire datagram and check each sequence and sys/comp.
                 * Also check for a GPS time that we can set the clock to */
                uint8_t *p_payload = packet.payload;
                while (p_payload < ((uint8_t *)&packet + res)) {
                    uint32_t message_id;
                    uint8_t sys_id;
                    uint8_t comp_id;
                    uint8_t payload_offset;
                    uint8_t seq;
                    uint8_t siglen = 0;
                    #define MAVLINK_STX_MAVLINK1 254
                    if (p_payload[0] == MAVLINK_STX_MAVLINK1) {
                        message_id = p_payload[5];
                        sys_id = p_payload[3];
                        comp_id = p_payload[4];
                        payload_offset = 6;
                        seq = p_payload[2];
                    } else {
                        message_id = (p_payload[7]) | (p_payload[8]<<8) | p_payload[9]<<16;
                        sys_id = p_payload[5];
                        comp_id = p_payload[6];
                        payload_offset = 10;
                        seq = p_payload[4];
                        const uint8_t incompat_flags = p_payload[2];
                        const uint8_t MAVLINK_IFLAG_SIGNED = (1U << 0);
                        if (incompat_flags & MAVLINK_IFLAG_SIGNED) {
                            siglen = 13;
                        }
                        // FIXME: skip packet if incompat flag not recognised
                    }

                    source_check(sys_id, comp_id, seq);

                    syslog(LOG_INFO, "msg_id=%u msgid2=%u", (unsigned)message_id, (unsigned)message_id2);

                    if (!got_gps_time && message_id == MAVLINK_MSG_ID_SYSTEM_TIME) {
                        // XXX hefty magic here
                        //   usec since unix epoch is bytes 6..13, little-endian
                        int b;
                        uint64_t time_us = 0;
                        for (b = payload_offset+7; b >= payload_offset; b--)
                            time_us = time_us * 256 + p_payload[b];
                        if (time_us != 0) {
                            char buf[32];
                            syslog(LOG_INFO, "gps time %s", clock_tostr_r(time_us, buf));
                            got_gps_time = 1;
                            if (use_gps_time) {
                                clock_settime_us(CLOCK_REALTIME, time_us);
                                syslog(LOG_INFO, "system time set from gps time");
                            }
                        }
                    }

                    p_payload += (payload_offset + p_payload[1] + 2 + siglen); // Increase by the length of the header+payload+checksum+signature
                }

                /* check source port */
                if (sa_solo.sin_port == 0) {
                    sa_solo.sin_port = sa.sin_port;
                    syslog(LOG_INFO, "solo @ %s:%d", inet_ntoa(sa_solo.sin_addr),
                           ntohs(sa_solo.sin_port));
                } else if (sa_solo.sin_port != sa.sin_port) {
                    sa_solo.sin_port = sa.sin_port;
                    syslog(LOG_INFO, "solo is now at %s:%d", inet_ntoa(sa_solo.sin_addr),
                           ntohs(sa_solo.sin_port));
                }

                /* send to all destinations */
                t1_us = clock_gettime_us(CLOCK_MONOTONIC);

                mutex_lock(&dest_table_mutex, NULL);

                t2_us = clock_gettime_us(CLOCK_MONOTONIC);
                /* mutex_lock should not take longer than the memcpy in
                   update_telem_dest; warn if it takes too long */
                if ((t2_us - t1_us) > 10000)
                    syslog(LOG_ERR, "mutex_lock: blocked %u usec", (unsigned)(t2_us - t1_us));
                packet.tc_send_us = clock_gettime_us(CLOCK_MONOTONIC);
                for (i = 0; i < dest_table.num_dest; i++) {
                    // send the whole LinkPacket or just the mavlink payload
                    const void *buf = NULL;
                    ssize_t len = 0;
                    if (dest_table.dest[i].format == TF_MAVLINK) {
                        buf = (const void *)(packet.payload);
                        len = res - LinkPacket::HDR_LEN;
                    } else if (dest_table.dest[i].format == TF_LINK_PACKET) {
                        buf = (const void *)(&packet);
                        len = res;
                    }
                    /* sendto blocks if the network has gone away */
                    errno = 0;
                    ssize_t r = sendto(dest_table.dest[i].fd, buf, len, MSG_DONTWAIT,
                                       (struct sockaddr *)&(dest_table.dest[i].sa),
                                       sizeof(dest_table.dest[i].sa));
                    if (r != len) {
                        dest_table.dest[i].err_cnt++;
                        if ((now_us - dest_table.dest[i].err_us) >= 1000000) {
                            syslog(LOG_ERR, "[%u] sendto %s:%d returned %d, expected %d: %s",
                                   dest_table.dest[i].err_cnt,
                                   inet_ntoa(dest_table.dest[i].sa.sin_addr),
                                   ntohs(dest_table.dest[i].sa.sin_port), r, len, strerror(errno));
                            dest_table.dest[i].err_cnt = 0;
                            dest_table.dest[i].err_us = now_us;
                        }
                    }
                }

                mutex_unlock(&dest_table_mutex);
            }
        }

        /* check for upstream packets */

        mutex_lock(&dest_table_mutex, NULL);

        for (i = 0; i < dest_table.num_dest; i++) {

            int fd = dest_table.dest[i].fd;

            if (FD_ISSET(fd, &fds)) {
                /* packet from gcs */
                sa_len = sizeof(sa);
                t1_us = clock_gettime_us(CLOCK_MONOTONIC);
                res = recvfrom(fd, pkt, sizeof(pkt), 0, (struct sockaddr *)&sa, &sa_len);
                t2_us = clock_gettime_us(CLOCK_MONOTONIC);
                /* recvfrom should not block; warn if it does */
                if ((t2_us - t1_us) > 10000)
                    syslog(LOG_ERR, "recvfrom(gcs): blocked %u usec", (unsigned)(t2_us - t1_us));

                pkts_up_total++;

                /* send to solo */
                if (sa_solo.sin_addr.s_addr != 0 && sa_solo.sin_port != 0) {
                    /* sendto blocks if the network has gone away */
                    if (sendto(fd_solo, pkt, res, MSG_DONTWAIT, (struct sockaddr *)&sa_solo,
                               sizeof(sa_solo)) != res) {
                        int skipped;
                        if ((skipped = can_log_error(now_us)) >= 0)
                            syslog(LOG_ERR, "[%u] sendto %s:%d: %s", skipped,
                                   inet_ntoa(sa_solo.sin_addr), ntohs(sa_solo.sin_port),
                                   strerror(errno));
                    }
                }
            }

        } // for (int i...)

        mutex_unlock(&dest_table_mutex);

        /* check for time to log */

        if (now_us >= log_time_us) {
            char msg[200]; /* usually use about 40 characters */
            char *m = msg;
            int n, r, s;

            memset(msg, 0, sizeof(msg));
            r = sizeof(msg) - 1; /* never overwrite that last '\0' */

            /* In the following, snprintf will never write more than 'r'
             * characters, so if we maintain that correctly and just let it
             * go non-positive if we overflow, then this won't overrun. The
             * return from snprint when it runs out of room is >= 'r', so 'r'
             * goes zero or negative if we run out of room. */

            n = snprintf(m, r, "dn:%d", pkts_down_total);
            m += n;
            r -= n;

            for (s = 0; s < num_sources; s++) {
                if (r > 0) {
                    n = snprintf(m, r, " (%d,%d)%d/%d", sources[s].sys_id, sources[s].comp_id,
                                 sources[s].pkt_cnt, sources[s].err_cnt);
                    m += n;
                    r -= n;
                }
            }

            if (r > 0) {
                n = snprintf(m, r, " up:%d", pkts_up_total);
                m += n;
                r -= n;
            }

#if 0
            /* timeout count is only useful for tuning the timeout value */
            if (r > 0)
            {
                n = snprintf(m, r, " to:%d", select_timeout);
                m += n;
                r -= n;
            }
#endif

            syslog(LOG_INFO, msg);

            sources_clear();
            pkts_down_total = 0;
            pkts_up_total = 0;
            select_timeout = 0;

            log_time_us += log_interval_us;
        }

    } /* while (1) */

    return NULL;

} /* tlm_main */

static int start_tlm_main(void)
{
    int r;

    if ((r = pthread_create(&tlm_ctx, NULL, tlm_main, NULL)) != 0) {
        syslog(LOG_ERR, "start_tlm_main: pthread_create returned %d", r);
        return 1;
    }

    if ((r = pthread_setname_np(tlm_ctx, "tlm_main")) != 0) {
        syslog(LOG_ERR, "start_tlm_main: pthread_setname_np returned %d", r);
        return 1;
    }

    struct sched_param sp;
    memset(&sp, 0, sizeof(sp));
    sp.sched_priority = TC_MAIN_PRIORITY;
    if ((r = pthread_setschedparam(tlm_ctx, SCHED_FIFO, &sp)) != 0) {
        syslog(LOG_ERR, "start_tlm_main: pthread_setschedparam returned %d", r);
        return 1;
    }

    return 0;

} /* start_tlm_main */

int main(int argc, char *argv[])
{

    //
    // initialize logging
    //

    openlog("tlm", LOG_NDELAY, LOG_LOCAL1);

    setlogmask(LOG_UPTO(LOG_INFO));

    syslog(LOG_INFO, "telem_ctrl starting: built " __DATE__ " " __TIME__);

    //
    // read configuration
    //

    INIReader reader("/etc/sololink.conf");
    if (reader.ParseError() < 0) {
        syslog(LOG_CRIT, "can't parse /etc/sololink.conf");
        exit(1);
    }

    std::string s1 = reader.Get("solo", "mavDestIp", "127.0.0.1");
    const char *stm32_ip = s1.c_str();
    short stm32_port_hbo = reader.GetInteger("solo", "mavDestPort", 5015);
    syslog(LOG_INFO, "stm32 @ %s:%d", stm32_ip, stm32_port_hbo);

    std::string s2 = reader.Get("solo", "tlogDestIp", "127.0.0.1");
    const char *tlog_ip = s2.c_str();
    short tlog_port_hbo = reader.GetInteger("solo", "tlogDestPort", 14583);
    syslog(LOG_INFO, "tlog @ %s:%d", tlog_ip, tlog_port_hbo);

    telem_dest_port_hbo = reader.GetInteger("solo", "telemDestPort", 14550);
    syslog(LOG_INFO, "telem_dest_port = %d", telem_dest_port_hbo);

    use_gps_time = reader.GetBoolean("solo", "useGpsTime", true) ? 1 : 0;
    syslog(LOG_INFO, "use_gps_time = %d", use_gps_time);

    uplink_tos = reader.GetInteger("solo", "telemUpTos", IP_TOS_DEFAULT);
    syslog(LOG_INFO, "uplink_tos = 0x%02x", uplink_tos);

    gcs_tos = reader.GetInteger("solo", "telemGcsTos", IP_TOS_DEFAULT);
    syslog(LOG_INFO, "gcs_tos = 0x%02x", gcs_tos);

    // Stations where downlink packets will be forwarded. Solo sends all
    // mavlink to this process, and this process figures out who needs them
    // (stm32, tlog process, app, gcs, etc.).
    dest_table.init();
    mutex_init(&dest_table_mutex);

    // add internal destinations (stm32, tlog)
    mutex_lock(&dest_table_mutex, NULL);
    dest_table.add(NULL, inet_addr(stm32_ip), stm32_port_hbo, 0, TF_LINK_PACKET);
    dest_table.add(NULL, inet_addr(tlog_ip), tlog_port_hbo);
    mutex_unlock(&dest_table_mutex);

    // Solo destination socket address - the address in Solo where uplink
    // packets will be sent. Fill in the family now, fill in the ip address
    // from the solo ip address file (below), then finally fill in the port
    // when we get any downlink (since port number on solo is dynamic).
    memset(&sa_solo, 0, sizeof(sa_solo));
    sa_solo.sin_family = AF_INET;

    // This does not return until Solo is there.
    wait_solo(&sa_solo.sin_addr.s_addr);

    //
    // start telemetry thread
    //

    if (start_tlm_main() != 0) {
        syslog(LOG_ERR, "telem_ctrl: error starting tlm_main");
        exit(1);
    }

    //
    // periodically scan for telemetry consumers
    //

    // hostapd connection. This is used to query hostapd for a list of all
    // associated telemetry destinations. (Underneath, it is a unix-domain
    // socket that talks to the hostapd process.)
    void *hostapd_handle = hostapd_ctrl_new("wlan0-ap");
    if (hostapd_handle == NULL) {
        syslog(LOG_CRIT, "can't create connection to hostapd");
        exit(1);
    }

    while (true) {

        update_telem_dest(hostapd_handle);

        sleep(telem_dest_update_interval_s);

    } // while (true)

} // main
