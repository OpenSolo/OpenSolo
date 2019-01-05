#include <stdio.h>
#include <unistd.h>
#include <net/if.h>
#include <syslog.h>
#include <netlink/netlink.h>
#include <netlink/genl/ctrl.h>
#include <netlink/genl/genl.h>
#include <linux/nl80211.h>
#include <sys/socket.h>
#include <sys/un.h>
#include "../mavlink/c_library/common/mavlink.h"
#include "util.h"

/*
* Retrieve wifi information and:
*   - log it
*   - send mavlinke rssi message
*
* Netlink documentation: http://www.infradead.org/~tgr/libnl/
* Netlink example: iw
*/

/*
 * Implementation notes
 *
 * Each time this runs it creates a unix socket in /tmp. Since there is no
 * "clean" exit from this program, that socket is not deleted until the next
 * reboot, and then only because /tmp is not persistent. There is a very
 * unlikely failure mode where when this program dies and restarts, it comes
 * back with the same PID; if that happens, it will probably fail to bind to
 * the unix socket (since it /tmp/rssi_send.<pid> will already exist) and
 * exit. Whoever started this program (inittab) will notice and start it
 * again. [That case has never been observed to happen.]
 *
 * The netlink message creation, sending, and parsing is rather mysterious;
 * there is little in the way of documentation other than the source code.
 * Some basic unknowns are things like when we allocate a message and give it
 * to the send function, who should free it? It would be possible to drill
 * down further into the source and figure it out, but instead, testing is
 * used; a run at 1000 msgs/sec for tens of minutes shows that the program's
 * size is not growning, so there are probably no leaks.
 *
 * Late conversion from C to C++ to add logging.
 *
 * The netlink stuff returns information in attribute tables. When we get
 * one of those, we copy the attributes that are present into a simple
 * structure defined here (station_info and rate_info). Each of those
 * structures has a name that corresponds with one of the attribute enums
 * in linux/nl80211.h, and the struct has fields corresponding to the
 * enum values.
 */

/* system and component IDs to use in mavlink header */
static uint8_t system_id = 10;   /* change with -s option */
static uint8_t component_id = 0; /* change with -c option */

/* time between rssi messages (default 1 second) */
static unsigned interval_ms = 1000; /* change with -i option */

/* run verbose (debug) */
static int verbose = 0;

#define DBG(X)

/*
 * Rate info, contained in station info
 *
 * Fields commented out are ones where linux/nl80211.h does not say what the
 * type is, and we don't need right now, so they are just left out.
 */
typedef struct rate_info {
    uint16_t bitrate; /* total bitrate (u16, 100kbit/s) */
    uint8_t mcs;      /* mcs index for 802.11n (u8) */
    /* n40_mhz_width: 40 MHz dualchannel bitrate */
    /* short_gi: 400ns guard interval */
    uint32_t bitrate32; /* total bitrate (u32, 100kbit/s) */
    /* max: highest rate_info number currently defined */
    uint8_t vht_mcs; /* MCS index for VHT (u8) */
    uint8_t vht_nss; /* number of streams in VHT (u8) */
    /* n80_mhz_width: 80 MHz VHT rate */
    /* n80p80_mhz_width: 80+80 MHz VHT rate */
    /* n160_mhz_width: 160 MHz VHT rate */
} rate_info_t;

/* print structure to a string, debug */
static char *rate_info_str(char *s, const rate_info_t *p)
{
    /* 43 chars + 5 u32 = 43 + 5 * 10 = 93 chars max */
    sprintf(s, "bitrate=%u mcs=%u bitrate32=%u vht_mcs=%u vht_nss=%u", p->bitrate, p->mcs,
            p->bitrate32, p->vht_mcs, p->vht_nss);
    return s;
}

/*
 * Information retrieved via station info request message
 *
 * Fields commented out are ones where linux/nl80211.h does not say what the
 * type is, and we don't need right now, so they are just left out.
 */
typedef struct station_info {
    uint32_t inactive_time; /* time since last activity (u32, msecs) */
    uint32_t rx_bytes;      /* total received bytes (u32, from this station) */
    uint32_t tx_bytes;      /* total transmitted bytes (u32, to this station) */
    uint64_t rx_bytes64;    /* total received bytes (u64, from this station) */
    uint64_t tx_bytes64;    /* total transmitted bytes (u64, to this station) */
    int8_t signal;          /* signal strength of last received PPDU (u8, dBm) */
    rate_info_t tx_bitrate; /* current unicast tx rate, nested attribute containing
                               info as possible, see &enum nl80211_rate_info */
    uint32_t rx_packets;    /* total received packet (u32, from this station) */
    uint32_t tx_packets;    /* total transmitted packets (u32, to this station) */
    uint32_t tx_retries;    /* total retries (u32, to this station) */
    uint32_t tx_failed;     /* total failed packets (u32, to this station) */
    int8_t signal_avg;      /* signal strength average (u8, dBm) */
    /* llid: the station's mesh LLID */
    /* plid: the station's mesh PLID */
    /* plink_state: peer link state for the station (see %enum nl80211_plink_state) */
    rate_info_t rx_bitrate; /* last unicast data frame rx rate, nested attribute,
                               like NL80211_STA_INFO_TX_BITRATE. */
    /* bss_param: current station's view of BSS, nested attribute containing info as
       possible, see &enum nl80211_sta_bss_param */
    /* connected_time: time since the station is last connected */
    /* sta_flags: Contains a struct nl80211_sta_flag_update. */
    uint32_t beacon_loss; /* count of times beacon loss was detected (u32) */
    int64_t t_offset;     /* timing offset with respect to this STA (s64) */
    /* local_pm: local mesh STA link-specific power mode */
    /* peer_pm: peer mesh STA link-specific power mode */
    /* nonpeer_pm: neighbor mesh STA power save mode towards non-peer STA */
} station_info_t;

/*
 * Information retrieved via station info request message
 *
 * Fields commented out are ones where linux/nl80211.h does not say what the
 * type is, and we don't need right now, so they are just left out.
 */
typedef struct survey_info {
    /*
     * NL80211_SURVEY_INFO_FREQUENCY: center frequency of channel
     * NL80211_SURVEY_INFO_NOISE: noise level of channel (u8, dBm)
     * NL80211_SURVEY_INFO_IN_USE: channel is currently being used
     * NL80211_SURVEY_INFO_TIME: amount of time (in ms) that the radio
     *      was turned on (on channel or globally)
     * NL80211_SURVEY_INFO_TIME_BUSY: amount of the time the primary
     *      channel was sensed busy (either due to activity or energy detect)
     * NL80211_SURVEY_INFO_TIME_EXT_BUSY: amount of time the extension
     *      channel was sensed busy
     * NL80211_SURVEY_INFO_TIME_RX: amount of time the radio spent
     *      receiving data (on channel or globally)
     * NL80211_SURVEY_INFO_TIME_TX: amount of time the radio spent
     *      transmitting data (on channel or globally)
     * NL80211_SURVEY_INFO_TIME_SCAN: time the radio spent for scan (on this channel or globally)
     */

    bool in_use;
    uint32_t freq;
    int8_t noise;
    uint64_t chan_active_time;
    uint64_t chan_busy_time;
    uint64_t chan_ext_busy_time;
    uint64_t chan_receive_time;
    uint64_t chan_transmit_time;

} survey_info_t;

// state related to our netlink context
typedef struct {
    struct nl_sock *sock;
    int nl80211_id;
    unsigned int if_index;

    struct nl_cb *cmd_cb;
    struct nl_cb *sock_cb;
} nl_state_t;

// items that are referenced in netlink callback context
typedef struct {
    volatile int
        status; // ensure this is always dereferenced, even when only being written in callbacks
    station_info_t station_info;
    survey_info_t survey_info;
} cb_ctx_t;

/* print structure to console, debug */
static void station_info_dump(const station_info_t *s)
{
    char buf[100];
    printf("inactive_time=%u\n", s->inactive_time);
    printf("rx_bytes=%u tx_bytes=%u rx_bytes64=%llu tx_bytes64=%llu\n", s->rx_bytes, s->tx_bytes,
           s->rx_bytes64, s->tx_bytes64);
    printf("signal=%d signal_avg=%d beacon_loss=%u t_offset=%lld\n", s->signal, s->signal_avg,
           s->beacon_loss, s->t_offset);
    printf("rx_packets=%u tx_packets=%u tx_retries=%u tx_failed=%u\n", s->rx_packets, s->tx_packets,
           s->tx_retries, s->tx_failed);
    printf("tx_bitrate: %s\n", rate_info_str(buf, &s->tx_bitrate));
    printf("rx_bitrate: %s\n", rate_info_str(buf, &s->rx_bitrate));
}

static void send_rssi(int rssi, unsigned retries);
static void get_station_info(cb_ctx_t *cb_ctx, const nl_state_t *nl);
static void get_survey_info(cb_ctx_t *cb_ctx, const nl_state_t *nl);
static int valid_handler(struct nl_msg *msg, void *arg);
static int station_handler(struct nl_msg *msg, station_info_t *station_info);
static int survey_handler(struct nl_msg *msg, survey_info_t *survey_info);
static int error_handler(struct sockaddr_nl *nla, struct nlmsgerr *err, void *arg);
static int finish_handler(struct nl_msg *msg, void *arg);
static int ack_handler(struct nl_msg *msg, void *arg);

static bool nl_state_init(nl_state_t *nl);
static bool nl_state_init_callbacks(nl_state_t *nl, cb_ctx_t *cb);

static void usage(void)
{
    printf("rssi_send [-i interval_msec] [-s system_id] [-c component_id] [-v]\n");
    exit(1);
}

static uint64_t diff_clamp(uint64_t curr, uint64_t prev)
{
    if (curr < prev) {
        return 0;
    }
    return curr - prev;
}

static void log_station_info(const station_info_t *curr, const station_info_t *prev)
{
    /* station_info.[tr]x_bitrate.bitrate32 is in units of 100,000 */

    syslog(LOG_INFO, "station sig=%d txr=%d.%d rxr=%d.%d ret=%llu err=%d", curr->signal_avg,
           curr->tx_bitrate.bitrate32 / 10, curr->tx_bitrate.bitrate32 % 10,
           curr->rx_bitrate.bitrate32 / 10, curr->rx_bitrate.bitrate32 % 10,
           diff_clamp(curr->tx_retries, prev->tx_retries), curr->tx_failed);
}

static void log_survey_info(const survey_info_t *curr, const survey_info_t *prev)
{
    syslog(LOG_INFO, "survey freq=%d noise=%d active=%llu busy=%llu ext_busy=%llu rx=%llu tx=%llu",
           curr->freq, curr->noise, diff_clamp(curr->chan_active_time, prev->chan_active_time),
           diff_clamp(curr->chan_busy_time, prev->chan_busy_time),
           diff_clamp(curr->chan_ext_busy_time, prev->chan_ext_busy_time),
           diff_clamp(curr->chan_receive_time, prev->chan_receive_time),
           diff_clamp(curr->chan_transmit_time, prev->chan_transmit_time));
}

/*
 * main program -
 * initialize, then loop: read wifi status, log it, send rssi message
 */
int main(int argc, char *argv[])
{
    int opt;
    uint64_t now_us;
    uint64_t next_us;
    unsigned interval_us;

    cb_ctx_t cb_ctx;
    nl_state_t nl_state;

    station_info_t last_station_info;
    survey_info_t last_survey_info;

    /* all arguments are optional; normal use is with no arguments */
    while ((opt = getopt(argc, argv, "i:s:c:v:")) != -1) {
        switch (opt) {
        case 'i':
            interval_ms = atoi(optarg);
            break;
        case 's':
            system_id = atoi(optarg);
            break;
        case 'c':
            component_id = atoi(optarg);
            break;
        case 'v':
            verbose = atoi(optarg);
            break;
        default:
            usage();
        }
    }

    memset(&cb_ctx, 0, sizeof cb_ctx);
    memset(&last_station_info, 0, sizeof last_station_info);
    memset(&last_survey_info, 0, sizeof last_survey_info);

    openlog("rssi_send", LOG_NDELAY, LOG_LOCAL3);

    syslog(LOG_INFO, "main: built " __DATE__ " " __TIME__);

    if (!nl_state_init(&nl_state)) {
        syslog(LOG_ERR, "failed to init netlink\n");
        exit(1);
    }

    if (!nl_state_init_callbacks(&nl_state, &cb_ctx)) {
        syslog(LOG_ERR, "failed to init callbacks\n");
        exit(1);
    }

    interval_us = interval_ms * 1000;

    next_us = clock_gettime_us(CLOCK_MONOTONIC) + interval_us;

    while (1) {
        // delay until the next message time
        now_us = clock_gettime_us(CLOCK_MONOTONIC);
        if (next_us > now_us)
            usleep(next_us - now_us);
        next_us += interval_us;

        // both these are blocking
        get_station_info(&cb_ctx, &nl_state);
        get_survey_info(&cb_ctx, &nl_state);

        if (verbose >= 1)
            station_info_dump(&cb_ctx.station_info);

        log_station_info(&cb_ctx.station_info, &last_station_info);
        log_survey_info(&cb_ctx.survey_info, &last_survey_info);

        unsigned retries = diff_clamp(cb_ctx.station_info.tx_retries, last_station_info.tx_retries);

        memcpy(&last_station_info, &cb_ctx.station_info, sizeof last_station_info);
        memcpy(&last_survey_info, &cb_ctx.survey_info, sizeof last_survey_info);

        send_rssi(cb_ctx.station_info.signal_avg, retries);
    }

    return 0;

} /* main */

bool nl_state_init(nl_state_t *nl)
{
    /*
     * Initialize our netlink context.
     */

    memset(nl, 0, sizeof *nl);

    nl->sock = nl_socket_alloc();
    if (nl->sock == NULL) {
        fprintf(stderr, "ERROR allocating netlink socket\n");
        goto cleanup;
    }
    DBG(printf("nl_socket_alloc: nl_sock=%p\n", nl_sock);)

    if (genl_connect(nl->sock) != 0) {
        fprintf(stderr, "ERROR connecting netlink socket\n");
        goto cleanup;
    }
    DBG(printf("genl_connect: ok\n");)

    nl->nl80211_id = genl_ctrl_resolve(nl->sock, "nl80211");
    if (nl->nl80211_id < 0) {
        fprintf(stderr, "ERROR resolving netlink socket\n");
        goto cleanup;
    }
    DBG(printf("genl_ctrl_resolve: nl80211_id=%d\n", nl80211_id);)

    nl->if_index = if_nametoindex("wlan0");
    if (nl->if_index == 0) {
        fprintf(stderr, "ERROR getting interface index\n");
        goto cleanup;
    }
    DBG(printf("if_nametoindex: if_index=%u\n", if_index);)

    return true;

cleanup:
    if (nl->sock != NULL)
        nl_socket_free(nl->sock);

    return false;
}

bool nl_state_init_callbacks(nl_state_t *nl, cb_ctx_t *cb)
{
    /*
     * Register our callbacks to handle netlink responses/events.
     */

    nl->cmd_cb = nl_cb_alloc(NL_CB_DEFAULT);
    if (nl->cmd_cb == NULL) {
        fprintf(stderr, "ERROR allocating netlink command callback\n");
        goto cleanup;
    }
    DBG(printf("nl_cb_alloc: cmd_cb=%p\n", cmd_cb);)

    nl->sock_cb = nl_cb_alloc(NL_CB_DEFAULT);
    if (nl->sock_cb == NULL) {
        fprintf(stderr, "ERROR allocating netlink socket callback\n");
        goto cleanup;
    }
    DBG(printf("nl_cb_alloc: sock_cb=%p\n", nl->sock_cb);)

    // handle all NL_CB_VALID callbacks via valid_handler()
    if (nl_cb_set(nl->cmd_cb, NL_CB_VALID, NL_CB_CUSTOM, valid_handler, cb) != 0) {
        fprintf(stderr, "ERROR setting command callback\n");
        goto cleanup;
    }
    DBG(printf("nl_cb_set: ok\n");)

    // not clear that this is necessary, but following example convention for now...
    nl_socket_set_cb(nl->sock, nl->sock_cb);

    nl_cb_err(nl->cmd_cb, NL_CB_CUSTOM, error_handler, cb);
    nl_cb_set(nl->cmd_cb, NL_CB_FINISH, NL_CB_CUSTOM, finish_handler, cb);
    nl_cb_set(nl->cmd_cb, NL_CB_ACK, NL_CB_CUSTOM, ack_handler, cb);

    return true;

cleanup:
    if (nl->sock_cb != NULL) {
        nl_cb_put(nl->sock_cb);
    }

    if (nl->cmd_cb != NULL) {
        nl_cb_put(nl->cmd_cb);
    }
    return false;
}

/* send mavlink radio_status (rssi) message */
static void send_rssi(int rssi, unsigned retries)
{
    /* socket used to send to telem downlink */
    static int fd = -1;
    /* destination address */
    static struct sockaddr_un sa_dst;

    char sock_name[32];
    struct sockaddr_un sa_src;
    static unsigned const msg_max = 256;
    unsigned msg_len;
    uint8_t msg_buf[msg_max];
    mavlink_message_t msg;
    int num_bytes;
    uint8_t u8_rssi;
    uint8_t u8_retries;

    /* one-time init */
    if (fd == -1) {
        fd = socket(AF_UNIX, SOCK_DGRAM, 0);
        if (fd == -1) {
            perror("socket");
            return;
        }

        memset(sock_name, 0, sizeof(sock_name));
        snprintf(sock_name, sizeof(sock_name) - 1, "/tmp/rssi_send.%u", getpid());
        memset(&sa_src, 0, sizeof(sa_src));
        sa_src.sun_family = AF_UNIX;
        strncpy(sa_src.sun_path, sock_name, sizeof(sa_src.sun_path) - 1);
        if (bind(fd, (struct sockaddr *)&sa_src, sizeof(sa_src)) != 0) {
            perror("bind");
            close(fd);
            fd = -1;
            return;
        }

        /* set destination address that will be used for sendto */
        memset(sock_name, 0, sizeof(sock_name));
        strcpy(sock_name, "/run/telem_downlink");
        memset(&sa_dst, 0, sizeof(sa_dst));
        sa_dst.sun_family = AF_UNIX;
        strncpy(sa_dst.sun_path, sock_name, sizeof(sa_dst.sun_path) - 1);

    } /* if (fd...) */

    u8_rssi = (uint8_t)rssi;
    u8_retries = (uint8_t)retries;

    mavlink_msg_radio_status_pack(system_id, component_id, &msg, 0, /* rssi */
                                  u8_rssi,                          /* remrssi */
                                  0,                                /* txbuf */
                                  0,                                /* noise */
                                  0,                                /* remnoise */
                                  u8_retries,                       /* rxerrors */
                                  0);                               /* fixed */

    msg_len = mavlink_msg_to_send_buffer(msg_buf, &msg);

    if (verbose >= 2)
        printf("rssi_send: %02x %02x %02x %02x %02x %02x\n", msg_buf[0], msg_buf[1], msg_buf[2],
               msg_buf[3], msg_buf[4], msg_buf[5]);

    num_bytes = sendto(fd, msg_buf, msg_len, 0, (struct sockaddr *)&sa_dst, sizeof(sa_dst));
    if (num_bytes < 0)
        perror("sendto");

} /* send_rssi */

static bool send_nlcmd(const nl_state_t *nl, nl80211_commands c, int nl_msg_flags)
{
    /*
     * Assemble and send the netlink command 'c'.
     */

    void *hdr = NULL;
    int num_bytes = -1;
    uint32_t if_index_uint32;
    struct nl_msg *msg;

    bool success = true;

    msg = nlmsg_alloc();
    if (msg == NULL) {
        fprintf(stderr, "ERROR allocating netlink message\n");
        success = false;
        goto cleanup;
    }
    DBG(printf("nlmsg_alloc: msg=%p\n", msg);)

    hdr = genlmsg_put(msg, NL_AUTO_PORT, NL_AUTO_SEQ, nl->nl80211_id, 0, nl_msg_flags, c, 0);
    if (hdr == NULL) {
        fprintf(stderr, "ERROR creating netlink message\n");
        success = false;
        goto cleanup;
    }
    DBG(printf("genlmsg_put: hdr=%p\n", hdr);)

    if_index_uint32 = nl->if_index;
    if (nla_put(msg, NL80211_ATTR_IFINDEX, sizeof(uint32_t), &if_index_uint32) != 0) {
        fprintf(stderr, "ERROR setting message attribute\n");
        success = false;
        goto cleanup;
    }
    DBG(printf("nla_put: ok\n");)

    num_bytes = nl_send_auto(nl->sock, msg);
    if (num_bytes < 0) {
        fprintf(stderr, "ERROR sending netlink message\n");
        success = false;
        goto cleanup;
    }
    DBG(printf("nl_send_auto_complete: num_bytes=%d\n", num_bytes);)

cleanup:
    if (msg != NULL) {
        nlmsg_free(msg);
    }

    return success;
}

/*
 * Get station info from interface via netlink
 *
 * This sends the request to the kernel to send us the station info,
 * then waits for the response to come back. The response comes back
 * as a callback (station_handler):
 *
 * Normal operation:
 *  this function sends request
 *  this function calls nl_recvmsgs; inside that, station_handler is called
 *      station_handler fills in station_info
 *  this function calls nl_recvmsgs; inside that, finish_handler is called
 *      finish_handler clears 'status'
 *  this function sees status is cleared and returns
 *
 * Almost everything returned is parsed out and available. Only a few items
 * are logged, and only the signal strength is used in the mavlink message,
 * but pulling them all out of the netlink message should make it easier to
 * log more (or something different) if we want.
 */

static void get_station_info(cb_ctx_t *cb_ctx, const nl_state_t *nl)
{
    memset(&cb_ctx->station_info, 0, sizeof(cb_ctx->station_info));

    cb_ctx->status = 1;
    if (!send_nlcmd(nl, NL80211_CMD_GET_STATION, NLM_F_DUMP)) {
        return;
    }

    /* wait for callback to set station_info and set status=0 */
    while (cb_ctx->status == 1) {
        int rv = nl_recvmsgs(nl->sock, nl->cmd_cb);
        if (rv != 0) {
            fprintf(stderr, "nl_recvmsgs: %d\n", rv);
        }
    }
}

void get_survey_info(cb_ctx_t *cb_ctx, const nl_state_t *nl)
{
    memset(&cb_ctx->survey_info, 0, sizeof(cb_ctx->survey_info));

    cb_ctx->status = 1;
    if (!send_nlcmd(nl, NL80211_CMD_GET_SURVEY, NLM_F_DUMP)) {
        return;
    }

    /* wait for callback to set set status=0 */
    while (cb_ctx->status == 1) {
        int rv = nl_recvmsgs(nl->sock, nl->cmd_cb);
        if (rv != 0) {
            fprintf(stderr, "nl_recvmsgs: %d\n", rv);
        }
    }
}

int valid_handler(struct nl_msg *msg, void *arg)
{
    /*
     * Top level handler for all NL_CB_VALID/NL_CB_CUSTOM responses.
     *
     * Check the reported cmd and dispatch accordingly.
     */

    struct nlmsghdr *nl_hdr = nlmsg_hdr(msg);
    struct genlmsghdr *genl_hdr = (struct genlmsghdr *)nlmsg_data(nl_hdr);

    cb_ctx_t *ctx = (cb_ctx_t *)arg;

    switch (genl_hdr->cmd) {
    case NL80211_CMD_NEW_STATION:
        return station_handler(msg, &ctx->station_info);

    case NL80211_CMD_NEW_SURVEY_RESULTS:
        return survey_handler(msg, &ctx->survey_info);

    default:
        // unexpected msg
        return NL_SKIP;
    }
}

/*
 * Called for each station result message that comes back from the kernel.
 * We expect only one before finish_handler is called.
 */
static int station_handler(struct nl_msg *msg, station_info_t *station_info)
{
    struct nlattr *tb1[NL80211_ATTR_MAX + 1];
    struct nlmsghdr *nl_hdr;
    struct genlmsghdr *genl_hdr;
    struct nlattr *genl_attr_data;
    int genl_attr_len;
    struct nlattr *tb2[NL80211_STA_INFO_MAX + 1];
    static struct nla_policy policy2[NL80211_STA_INFO_MAX + 1] = {{0}};
    struct nlattr *tb3[NL80211_RATE_INFO_MAX + 1];
    static struct nla_policy policy3[NL80211_RATE_INFO_MAX + 1] = {{0}};

    nl_hdr = nlmsg_hdr(msg);
    genl_hdr = (struct genlmsghdr *)nlmsg_data(nl_hdr);
    genl_attr_data = genlmsg_attrdata(genl_hdr, 0);
    genl_attr_len = genlmsg_attrlen(genl_hdr, 0);

    if (nla_parse(tb1, NL80211_ATTR_MAX, genl_attr_data, genl_attr_len, NULL) != 0) {
        fprintf(stderr, "ERROR parsing netlink message attributes\n");
        return NL_SKIP;
    }

    if (tb1[NL80211_ATTR_STA_INFO] == NULL) {
        printf("no data\n");
        return NL_SKIP;
    }

    if (nla_parse_nested(tb2, NL80211_STA_INFO_MAX, tb1[NL80211_ATTR_STA_INFO], policy2) != 0) {
        printf("ERROR parsing netlink message nested attributes\n");
        return NL_SKIP;
    }

    /* Description of what attributes there are is in linux/nl80211.h */

    /* For each possible attribute, see if it is present in the info we
     * got, and if so, copy it to our station_info_t structure. */

    if (tb2[NL80211_STA_INFO_INACTIVE_TIME] != NULL)
        station_info->inactive_time = nla_get_u32(tb2[NL80211_STA_INFO_INACTIVE_TIME]);

    if (tb2[NL80211_STA_INFO_RX_BYTES] != NULL)
        station_info->rx_bytes = nla_get_u32(tb2[NL80211_STA_INFO_RX_BYTES]);

    if (tb2[NL80211_STA_INFO_TX_BYTES] != NULL)
        station_info->tx_bytes = nla_get_u32(tb2[NL80211_STA_INFO_TX_BYTES]);

    if (tb2[NL80211_STA_INFO_RX_BYTES64] != NULL)
        station_info->rx_bytes64 = nla_get_u64(tb2[NL80211_STA_INFO_RX_BYTES64]);

    if (tb2[NL80211_STA_INFO_TX_BYTES64] != NULL)
        station_info->tx_bytes64 = nla_get_u64(tb2[NL80211_STA_INFO_TX_BYTES64]);

    /* this appears to be signed dBm, not a u8 */
    if (tb2[NL80211_STA_INFO_SIGNAL] != NULL)
        station_info->signal = (int8_t)nla_get_u8(tb2[NL80211_STA_INFO_SIGNAL]);

    /* tx_bitrate is a nested structure; the station_info points to a nested
     * attribute thing that needs to be decoded */
    if (tb2[NL80211_STA_INFO_TX_BITRATE] != NULL &&
        nla_parse_nested(tb3, NL80211_RATE_INFO_MAX, tb2[NL80211_STA_INFO_TX_BITRATE], policy3) ==
            0) {
        rate_info_t *rate_info = &station_info->tx_bitrate;
        if (tb3[NL80211_RATE_INFO_BITRATE] != NULL)
            rate_info->bitrate = nla_get_u16(tb3[NL80211_RATE_INFO_BITRATE]);
        if (tb3[NL80211_RATE_INFO_MCS] != NULL)
            rate_info->mcs = nla_get_u8(tb3[NL80211_RATE_INFO_MCS]);
        if (tb3[NL80211_RATE_INFO_BITRATE32] != NULL)
            rate_info->bitrate32 = nla_get_u32(tb3[NL80211_RATE_INFO_BITRATE32]);
        if (tb3[NL80211_RATE_INFO_VHT_MCS] != NULL)
            rate_info->vht_mcs = nla_get_u8(tb3[NL80211_RATE_INFO_VHT_MCS]);
        if (tb3[NL80211_RATE_INFO_VHT_NSS] != NULL)
            rate_info->vht_nss = nla_get_u8(tb3[NL80211_RATE_INFO_VHT_NSS]);
    }

    if (tb2[NL80211_STA_INFO_RX_PACKETS] != NULL)
        station_info->rx_packets = nla_get_u32(tb2[NL80211_STA_INFO_RX_PACKETS]);

    if (tb2[NL80211_STA_INFO_TX_PACKETS] != NULL)
        station_info->tx_packets = nla_get_u32(tb2[NL80211_STA_INFO_TX_PACKETS]);

    if (tb2[NL80211_STA_INFO_TX_RETRIES] != NULL)
        station_info->tx_retries = nla_get_u32(tb2[NL80211_STA_INFO_TX_RETRIES]);

    if (tb2[NL80211_STA_INFO_TX_FAILED] != NULL)
        station_info->tx_failed = nla_get_u32(tb2[NL80211_STA_INFO_TX_FAILED]);

    /* this appears to be signed dBm, not a u8 */
    if (tb2[NL80211_STA_INFO_SIGNAL_AVG] != NULL)
        station_info->signal_avg = (int8_t)nla_get_u8(tb2[NL80211_STA_INFO_SIGNAL_AVG]);

    /* rx_bitrate is nested, like tx_bitrate */
    if (tb2[NL80211_STA_INFO_RX_BITRATE] != NULL &&
        nla_parse_nested(tb3, NL80211_RATE_INFO_MAX, tb2[NL80211_STA_INFO_RX_BITRATE], policy3) ==
            0) {
        rate_info_t *rate_info = &station_info->rx_bitrate;
        if (tb3[NL80211_RATE_INFO_BITRATE] != NULL)
            rate_info->bitrate = nla_get_u16(tb3[NL80211_RATE_INFO_BITRATE]);
        if (tb3[NL80211_RATE_INFO_MCS] != NULL)
            rate_info->mcs = nla_get_u8(tb3[NL80211_RATE_INFO_MCS]);
        if (tb3[NL80211_RATE_INFO_BITRATE32] != NULL)
            rate_info->bitrate32 = nla_get_u32(tb3[NL80211_RATE_INFO_BITRATE32]);
        if (tb3[NL80211_RATE_INFO_VHT_MCS] != NULL)
            rate_info->vht_mcs = nla_get_u8(tb3[NL80211_RATE_INFO_VHT_MCS]);
        if (tb3[NL80211_RATE_INFO_VHT_NSS] != NULL)
            rate_info->vht_nss = nla_get_u8(tb3[NL80211_RATE_INFO_VHT_NSS]);
    }

    if (tb2[NL80211_STA_INFO_BEACON_LOSS] != NULL)
        station_info->beacon_loss = nla_get_u32(tb2[NL80211_STA_INFO_BEACON_LOSS]);

    if (tb2[NL80211_STA_INFO_T_OFFSET] != NULL)
        station_info->t_offset = (int64_t)nla_get_u64(tb2[NL80211_STA_INFO_T_OFFSET]);

    return NL_SKIP;

} /* station_handler */

static int survey_handler(struct nl_msg *msg, survey_info_t *survey_info)
{
    /*
     * https://wireless.wiki.kernel.org/en/users/Documentation/acs says
     *
     * - active time is the amount of time the radio has spent on the channel
     * - busy time is the amount of time the channel has spent on the channel but noticed the
     * channel was busy
     *      and could not initiate communication if it wanted to.
     * - tx time is the amount of time the channel has spent on the channel transmitting data.
     * - interference factor is defined as the ratio of the observed busy time over the time we
     * spent on the channel,
     *      this value is then amplified by the noise floor observed on the channel in comparison to
     * the lowest noise floor
     *      observed on the entire band.
     */

    struct nlattr *tb[NL80211_ATTR_MAX + 1];
    struct genlmsghdr *gnlh = (struct genlmsghdr *)nlmsg_data(nlmsg_hdr(msg));
    struct nlattr *sinfo[NL80211_SURVEY_INFO_MAX + 1];
    char dev[20];

    static struct nla_policy survey_policy[NL80211_SURVEY_INFO_MAX + 1];
    survey_policy[NL80211_SURVEY_INFO_FREQUENCY].type = NLA_U32;
    survey_policy[NL80211_SURVEY_INFO_NOISE].type = NLA_U8;

    nla_parse(tb, NL80211_ATTR_MAX, genlmsg_attrdata(gnlh, 0), genlmsg_attrlen(gnlh, 0), NULL);

    if_indextoname(nla_get_u32(tb[NL80211_ATTR_IFINDEX]), dev);

    if (!tb[NL80211_ATTR_SURVEY_INFO]) {
        fprintf(stderr, "survey data missing!\n");
        return NL_SKIP;
    }

    if (nla_parse_nested(sinfo, NL80211_SURVEY_INFO_MAX, tb[NL80211_ATTR_SURVEY_INFO],
                         survey_policy)) {
        fprintf(stderr, "failed to parse nested attributes!\n");
        return NL_SKIP;
    }

    if (sinfo[NL80211_SURVEY_INFO_FREQUENCY]) {
        survey_info->in_use = sinfo[NL80211_SURVEY_INFO_IN_USE] ? true : false;
        if (!survey_info->in_use) {
            return NL_SKIP;
        }
        survey_info->freq = nla_get_u32(sinfo[NL80211_SURVEY_INFO_FREQUENCY]);
    }
    if (sinfo[NL80211_SURVEY_INFO_NOISE]) {
        survey_info->noise = nla_get_u8(sinfo[NL80211_SURVEY_INFO_NOISE]);
    }
    if (sinfo[NL80211_SURVEY_INFO_CHANNEL_TIME]) {
        survey_info->chan_active_time = nla_get_u64(sinfo[NL80211_SURVEY_INFO_CHANNEL_TIME]);
    }
    if (sinfo[NL80211_SURVEY_INFO_CHANNEL_TIME_BUSY]) {
        survey_info->chan_busy_time = nla_get_u64(sinfo[NL80211_SURVEY_INFO_CHANNEL_TIME_BUSY]);
    }
    if (sinfo[NL80211_SURVEY_INFO_CHANNEL_TIME_EXT_BUSY]) {
        survey_info->chan_ext_busy_time =
            nla_get_u64(sinfo[NL80211_SURVEY_INFO_CHANNEL_TIME_EXT_BUSY]);
    }
    if (sinfo[NL80211_SURVEY_INFO_CHANNEL_TIME_RX]) {
        survey_info->chan_receive_time = nla_get_u64(sinfo[NL80211_SURVEY_INFO_CHANNEL_TIME_RX]);
    }
    if (sinfo[NL80211_SURVEY_INFO_CHANNEL_TIME_TX]) {
        survey_info->chan_transmit_time = nla_get_u64(sinfo[NL80211_SURVEY_INFO_CHANNEL_TIME_TX]);
    }
#if 0
    if (sinfo[NL80211_SURVEY_INFO_TIME_SCAN]) {
        survey_info->chan_scan_time = nla_get_u64(sinfo[NL80211_SURVEY_INFO_TIME_SCAN]);
    }
#endif

    return NL_SKIP;
}

/* Never seen this one called, but the examples have it. */
static int error_handler(struct sockaddr_nl *nla, struct nlmsgerr *err, void *arg)
{

    cb_ctx_t *cb_ctx = (cb_ctx_t *)arg;
    cb_ctx->status = err->error;

    return NL_STOP;
}

/*
 * Called after station info message is sent. The calling of this is how we
 * know we're done.
 *
 * Other commands sent to netlink might get several responses back; this is
 * more useful in those cases.
 */
static int finish_handler(struct nl_msg *msg, void *arg)
{
    cb_ctx_t *cb_ctx = (cb_ctx_t *)arg;
    cb_ctx->status = 0;

    return NL_SKIP;
}

/* Never seen this one called, but the examples have it. */
static int ack_handler(struct nl_msg *msg, void *arg)
{
    cb_ctx_t *cb_ctx = (cb_ctx_t *)arg;
    cb_ctx->status = 0;

    return NL_STOP;
}
