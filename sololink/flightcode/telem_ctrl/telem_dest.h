#ifndef TELEM_DEST_H
#define TELEM_DEST_H

//
// telemetry destinations table
//
// This is the destinations that receive mavlink. It is updated periodically
// based on who is associated with the AP and who is in the ARP table. The
// table's first 'num_dest' entries are in use, and all entries after that are
// free. An entry is added by putting it at index 'num_dest'. An entry 'k' is
// deleted by copying all entries from 'k' + 1 to the end down one slot
// (overwriting the entry to be deleted) and clearing the one now at the end.
//

#ifndef MAC_LEN
#define MAC_LEN 6
#endif

// Each entry either wants raw mavlink, or a link_packet (mavlink with
// metadata wrapper).
typedef enum {
    TF_MAVLINK,     // raw mavlink
    TF_LINK_PACKET, // link_packet.h
    TF_MAX          // (last)
} telem_format_t;

// one entry in table
struct telem_dest {
    telem_format_t format;
    int fd;
    sockaddr_in sa;
    unsigned err_cnt; // send errors for this dest since last message
    uint64_t err_us;  // time of last send error message
    uint8_t mac[MAC_LEN];
};

// the table (entries plus count)
struct telem_dest_table {
    // Maximum number of destinations. Normally we have up to four:
    // two internal (stm32 and tlog), maybe an app, and maybe a gcs.
    static const int DEST_MAX = 32;

    telem_dest dest[DEST_MAX];
    int num_dest;

    void init(void);
    void dump(int priority) const;
    void check(void) const;
    int add(const uint8_t *mac, const in_addr_t ip, const short port_hbo, int tos = 0,
            telem_format_t format = TF_MAVLINK);
    void delete_by_index(int index);
    int find_by_mac_ip(const uint8_t *mac, const in_addr_t ip) const;
};

#endif // TELEM_DEST_H
