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

static void get_station_info(station_info_t *station_info);
static int station_handler(struct nl_msg *msg, void *arg);
static int error_handler(struct sockaddr_nl *nla, struct nlmsgerr *err, void *arg);
static int finish_handler(struct nl_msg *msg, void *arg);
static int ack_handler(struct nl_msg *msg, void *arg);

int get_retries(void)
{
    station_info_t station_info;
    static uint32_t retries_last = 0;
    unsigned retries;

    get_station_info(&station_info);

    /* retries is logged as the difference from last time */
    if (retries_last == 0)
        retries = 0;
    else
        retries = station_info.tx_retries - retries_last;

    retries_last = station_info.tx_retries;

    return retries;
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
static void get_station_info(station_info_t *station_info)
{
    struct nl_sock *nl_sock = NULL;
    int nl80211_id = -1;
    unsigned int if_index = 0;
    uint32_t if_index_uint32;
    struct nl_msg *msg = NULL;
    struct nl_cb *cmd_cb = NULL;
    struct nl_cb *sock_cb = NULL;
    void *hdr = NULL;
    int num_bytes = -1;
    /* This is static because I'm not 100% sure the callbacks that may set it
       cannot get called again under some edge condition. Static is safe,
       re-entrancy is irrelevant. */
    static volatile int status = 0;

    memset(station_info, 0, sizeof(*station_info));

    nl_sock = nl_socket_alloc();
    if (nl_sock == NULL) {
        fprintf(stderr, "ERROR allocating netlink socket\n");
        status = 1;
        goto cleanup;
    }

    if (genl_connect(nl_sock) != 0) {
        fprintf(stderr, "ERROR connecting netlink socket\n");
        status = 1;
        goto cleanup;
    }

    nl80211_id = genl_ctrl_resolve(nl_sock, "nl80211");
    if (nl80211_id < 0) {
        fprintf(stderr, "ERROR resolving netlink socket\n");
        status = 1;
        goto cleanup;
    }

    if_index = if_nametoindex("wlan0");
    if (if_index == 0) {
        fprintf(stderr, "ERROR getting interface index\n");
        status = 1;
        goto cleanup;
    }

    msg = nlmsg_alloc();
    if (msg == NULL) {
        fprintf(stderr, "ERROR allocating netlink message\n");
        status = 1;
        goto cleanup;
    }

    cmd_cb = nl_cb_alloc(NL_CB_DEFAULT);
    if (cmd_cb == NULL) {
        fprintf(stderr, "ERROR allocating netlink command callback\n");
        status = 1;
        goto cleanup;
    }

    sock_cb = nl_cb_alloc(NL_CB_DEFAULT);
    if (sock_cb == NULL) {
        fprintf(stderr, "ERROR allocating netlink socket callback\n");
        status = 1;
        goto cleanup;
    }

    hdr = genlmsg_put(msg, NL_AUTO_PORT, NL_AUTO_SEQ, nl80211_id, 0, NLM_F_DUMP,
                      NL80211_CMD_GET_STATION, 0);
    if (hdr == NULL) {
        fprintf(stderr, "ERROR creating netlink message\n");
        status = 1;
        goto cleanup;
    }

    if_index_uint32 = if_index;
    if (nla_put(msg, NL80211_ATTR_IFINDEX, sizeof(uint32_t), &if_index_uint32) != 0) {
        fprintf(stderr, "ERROR setting message attribute\n");
        status = 1;
        goto cleanup;
    }

    if (nl_cb_set(cmd_cb, NL_CB_VALID, NL_CB_CUSTOM, station_handler, station_info) != 0) {
        fprintf(stderr, "ERROR setting command callback\n");
        status = 1;
        goto cleanup;
    }

    nl_socket_set_cb(nl_sock, sock_cb);

    num_bytes = nl_send_auto_complete(nl_sock, msg);
    if (num_bytes < 0) {
        fprintf(stderr, "ERROR sending netlink message\n");
        status = 1;
        goto cleanup;
    }

    status = 1;
    nl_cb_err(cmd_cb, NL_CB_CUSTOM, error_handler, (void *)&status);
    nl_cb_set(cmd_cb, NL_CB_FINISH, NL_CB_CUSTOM, finish_handler, (void *)&status);
    nl_cb_set(cmd_cb, NL_CB_ACK, NL_CB_CUSTOM, ack_handler, (void *)&status);

    /* wait for callback to set station_info and set status=0 */
    while (status == 1)
        nl_recvmsgs(nl_sock, cmd_cb);

cleanup:

    if (sock_cb != NULL)
        nl_cb_put(sock_cb);

    if (cmd_cb != NULL)
        nl_cb_put(cmd_cb);

    if (msg != NULL)
        nlmsg_free(msg);

    if (nl_sock != NULL)
        nl_socket_free(nl_sock);

} /* get_station_info */

/*
 * Called for each station result message that comes back from the kernel.
 * We expect only one before finish_handler is called.
 */
static int station_handler(struct nl_msg *msg, void *arg)
{
    station_info_t *station_info = (station_info_t *)arg;
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

/* Never seen this one called, but the examples have it. */
static int error_handler(struct sockaddr_nl *nla, struct nlmsgerr *err, void *arg)
{
    *(int *)arg = err->error;
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
    /* arg is a pointer to 'status' in get_station_info() */
    *(int *)arg = 0;
    return NL_SKIP;
}

/* Never seen this one called, but the examples have it. */
static int ack_handler(struct nl_msg *msg, void *arg)
{
    *(int *)arg = 0;
    return NL_STOP;
}
