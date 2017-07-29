#include <stdio.h>
#include <net/if.h>
#include <netlink/netlink.h>
#include <netlink/genl/ctrl.h>
#include <netlink/genl/genl.h>
#include <linux/nl80211.h>

/*
* Retrieve wifi scan survey results and print to stdout
*
* Netlink documentation: http://www.infradead.org/~tgr/libnl/
* Netlink example: iw
*/

static int survey_handler(struct nl_msg *msg, void *arg);
static int error_handler(struct sockaddr_nl *nla, struct nlmsgerr *err,
                         void *arg);
static int finish_handler(struct nl_msg *msg, void *arg);
static int ack_handler(struct nl_msg *msg, void *arg);

static int header = 0;


int main(int argc, char *argv[])
{
    volatile int status = 0;
    struct nl_sock *nl_sock = NULL;
    int nl80211_id = -1;
    unsigned int if_index = 0;
    uint32_t if_index_uint32;
    struct nl_msg *msg = NULL;
    struct nl_cb *cmd_cb = NULL;
    struct nl_cb *sock_cb = NULL;
    void *hdr = NULL;
    int num_bytes = -1;

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

    if_index = if_nametoindex("wlan0-ap");
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

    hdr = genlmsg_put(msg, NL_AUTO_PORT, NL_AUTO_SEQ, nl80211_id, 0,
                      NLM_F_DUMP, NL80211_CMD_GET_SURVEY, 0);
    if (hdr == NULL) {
        fprintf(stderr, "ERROR creating netlink message\n");
        status = 1;
        goto cleanup;
    }

    if_index_uint32 = if_index;
    if (nla_put(msg, NL80211_ATTR_IFINDEX, sizeof(uint32_t), &if_index_uint32)
            != 0) {
        fprintf(stderr, "ERROR setting message attribute\n");
        status = 1;
        goto cleanup;
    }

    if (nl_cb_set(cmd_cb, NL_CB_VALID, NL_CB_CUSTOM, survey_handler, NULL)
            != 0) {
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
    nl_cb_set(cmd_cb, NL_CB_FINISH, NL_CB_CUSTOM, finish_handler,
              (void *)&status);
    nl_cb_set(cmd_cb, NL_CB_ACK, NL_CB_CUSTOM, ack_handler, (void *)&status);

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

    return status;

} /* main */


static struct {
    int chan;
    int freq;
} freq_chan_map[] = {
    {1, 2412}, {2, 2417}, {3, 2422}, {4, 2427}, {5, 2432}, {6, 2437},
    {7, 2442}, {8, 2447}, {9, 2452}, {10, 2457}, {11, 2462}, {12, 2467},
    {13, 2472}, {14, 2484},
};


static int freq_to_chan(int freq)
{
    int i_max = sizeof(freq_chan_map) / sizeof(freq_chan_map[0]);
    int i;

    for (i = 0; i < i_max; i++)
        if (freq == freq_chan_map[i].freq)
            return freq_chan_map[i].chan;

    return -1;
}


/* Called for each survey result message that comes back from the kernel */
static int survey_handler(struct nl_msg *msg, void *arg)
{
    struct nlattr *tb1[NL80211_ATTR_MAX + 1];
    struct nlmsghdr *nl_hdr;
    struct genlmsghdr *genl_hdr;
    struct nlattr *genl_attr_data;
    int genl_attr_len;
    unsigned int if_index;
    char if_name[IF_NAMESIZE + 1];
    struct nlattr *tb2[NL80211_SURVEY_INFO_MAX + 1];
    static struct nla_policy policy[NL80211_SURVEY_INFO_MAX + 1] = { { 0 } };

    policy[NL80211_SURVEY_INFO_FREQUENCY].type = NLA_U32;
    policy[NL80211_SURVEY_INFO_NOISE].type = NLA_U8;

    nl_hdr = nlmsg_hdr(msg);
    genl_hdr = (struct genlmsghdr *)nlmsg_data(nl_hdr);
    genl_attr_data = genlmsg_attrdata(genl_hdr, 0);
    genl_attr_len = genlmsg_attrlen(genl_hdr, 0);

    if (nla_parse(tb1, NL80211_ATTR_MAX, genl_attr_data, genl_attr_len, NULL)
            != 0) {
        fprintf(stderr, "ERROR parsing netlink message attributes\n");
        return NL_SKIP;
    }

    if_index = nla_get_u32(tb1[NL80211_ATTR_IFINDEX]);
    if (if_indextoname(if_index, if_name) == NULL)
        strcpy(if_name, "ERROR");

    if (!header) {
        printf("%s:\n", if_name);
        printf("   Freq   Noise   OnChan   ChBusy  ExtBusy    Rxing    Txing\n");
        printf("Ch  MHz     dBm     msec     msec     msec     msec     msec\n");
        /*      -- ---- - ----- -------- -------- -------- -------- -------- */
        header = 1;
    }


    if (tb1[NL80211_ATTR_SURVEY_INFO] == NULL) {
        printf("no data\n");
        return NL_SKIP;
    }

    if (nla_parse_nested(tb2, NL80211_SURVEY_INFO_MAX,
                         tb1[NL80211_ATTR_SURVEY_INFO], policy) != 0) {
        printf("ERROR parsing netlink message nested attributes\n");
        return NL_SKIP;
    }

    /* Concise description of what these attributes are is in linux/nl80211.h */

    if (tb2[NL80211_SURVEY_INFO_FREQUENCY] != 0) {
        uint32_t value = nla_get_u32(tb2[NL80211_SURVEY_INFO_FREQUENCY]);
        int chan = freq_to_chan(value);
        printf("%2d", chan);
    } else {
        printf("%2s", "");
    }

    if (tb2[NL80211_SURVEY_INFO_FREQUENCY] != 0) {
        uint32_t value = nla_get_u32(tb2[NL80211_SURVEY_INFO_FREQUENCY]);
        printf("%5u", value);
    } else {
        printf("%5s", "");
    }

    if (tb2[NL80211_SURVEY_INFO_IN_USE])
        printf("%2s", "*");
    else
        printf("%2s", "");

    if (tb2[NL80211_SURVEY_INFO_NOISE]) {
        int8_t value = (int8_t)nla_get_u8(tb2[NL80211_SURVEY_INFO_NOISE]);
        printf("%6d", (int)value);
    } else {
        printf("%6s", "");
    }

    if (tb2[NL80211_SURVEY_INFO_CHANNEL_TIME]) {
        uint64_t value = nla_get_u64(tb2[NL80211_SURVEY_INFO_CHANNEL_TIME]);
        printf("%9llu", value);
    } else {
        printf("%9s", "");
    }

    if (tb2[NL80211_SURVEY_INFO_CHANNEL_TIME_BUSY]) {
        uint64_t value =
            nla_get_u64(tb2[NL80211_SURVEY_INFO_CHANNEL_TIME_BUSY]);
        printf("%9llu", value);
    } else {
        printf("%9s", "");
    }

    if (tb2[NL80211_SURVEY_INFO_CHANNEL_TIME_EXT_BUSY]) {
        uint64_t value =
            nla_get_u64(tb2[NL80211_SURVEY_INFO_CHANNEL_TIME_EXT_BUSY]);
        printf("%9llu", value);
    } else {
        printf("%9s", "");
    }

    if (tb2[NL80211_SURVEY_INFO_CHANNEL_TIME_RX]) {
        uint64_t value =
            nla_get_u64(tb2[NL80211_SURVEY_INFO_CHANNEL_TIME_RX]);
        printf("%9llu", value);
    } else {
        printf("%9s", "");
    }

    if (tb2[NL80211_SURVEY_INFO_CHANNEL_TIME_TX]) {
        uint64_t value =
            nla_get_u64(tb2[NL80211_SURVEY_INFO_CHANNEL_TIME_TX]);
        printf("%9llu", value);
    } else {
        printf("%9s", "");
    }

    printf("\n");

    return NL_SKIP;
}


static int error_handler(struct sockaddr_nl *nla, struct nlmsgerr *err,
                         void *arg)
{
    *(int *)arg = err->error;
	return NL_STOP;
}


/* Called after all survey result messages */
static int finish_handler(struct nl_msg *msg, void *arg)
{
    *(int *)arg = 0;
	return NL_SKIP;
}


static int ack_handler(struct nl_msg *msg, void *arg)
{
    *(int *)arg = 0;
	return NL_STOP;
}
