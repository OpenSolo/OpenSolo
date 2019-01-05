
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <stdint.h>
#include <string.h>
#include <syslog.h>
#include <unistd.h>
#include "telem_dest.h"

//
// telem_dest_table::init - initialize a telem_dest_table
//
void telem_dest_table::init(void)
{

    memset(this, 0, sizeof(telem_dest_table));

    for (int i = 0; i < DEST_MAX; i++)
        dest[i].fd = -1;

} // telem_dest_table::init

//
// telem_dest_table::dump - dump a telem_dest_table to log (debug)
//
void telem_dest_table::dump(int priority) const
{
    int i;

    syslog(priority, "telem_dest_table::dump: num_dest=%d", num_dest);
    for (i = 0; i < DEST_MAX; i++) {
        const uint8_t *mac = dest[i].mac;
        syslog(priority, "%s:%d %d %u %02x:%02x:%02x:%02x:%02x:%02x %d",
               inet_ntoa(dest[i].sa.sin_addr), ntohs(dest[i].sa.sin_port), dest[i].fd,
               dest[i].err_cnt, mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], dest[i].format);
    }

} // telem_dest_table::dump

//
// telem_dest_table::check - check that a telem_dest_table is not corrupt (debug)
//
// num_dest must be in range. The first num_dest entries should be nonzero in
// the ip and port fields, then entries after that should be all zeros. format
// must be valid.
//
void telem_dest_table::check(void) const
{
    int corrupt = 0;

    if (num_dest < 0 || num_dest >= DEST_MAX) {
        corrupt = 1;
    } else {
        int i;
        // entries in use
        for (i = 0; i < num_dest; i++) {
            if (dest[i].sa.sin_addr.s_addr == 0 || dest[i].sa.sin_port == 0 || dest[i].fd < 0)
                corrupt = 1;
        }
        // unused entries
        for (i = num_dest; i < DEST_MAX; i++) {
            if (dest[i].sa.sin_addr.s_addr != 0 || dest[i].sa.sin_port != 0 || dest[i].fd != -1 ||
                dest[i].err_cnt != 0 || dest[i].err_us != 0 || dest[i].mac[0] != 0 ||
                dest[i].mac[1] != 0 || dest[i].mac[2] != 0 || dest[i].mac[3] != 0 ||
                dest[i].mac[4] != 0 || dest[i].mac[5] != 0)
                corrupt = 1;
        }
        // format field
        for (i = num_dest; i < DEST_MAX; i++) {
            if (dest[i].format < 0 || dest[i].format >= TF_MAX)
                corrupt = 1;
        }
    }

    // dump if corrupt
    if (corrupt) {
        syslog(LOG_CRIT, "telem dest table is corrupt");
        dump(LOG_CRIT);
    }

} // telem_dest_table::check

extern int create_and_bind(short src_port_hbo, int tos);

//
// telem_dest_table::add - add a destination to the list of destinations receiving mavlink
//
// ip and port parameters are in network byte order.
//
// Returns 0 on success, or -1 on error (no room in table).
//
int telem_dest_table::add(const uint8_t *mac, const in_addr_t dest_ip, const short dest_port_hbo,
                          int tos, telem_format_t format)
{

    if (num_dest >= DEST_MAX)
        return -1; // table full

    int fd = create_and_bind(0, tos); // any local port
    if (fd < 0)
        return -1;

    dest[num_dest].fd = fd;

    dest[num_dest].format = format;

    // mac will be NULL for local destinations (stm32, tlog)
    if (mac != NULL)
        memcpy(dest[num_dest].mac, mac, MAC_LEN);

    dest[num_dest].sa.sin_addr.s_addr = dest_ip;
    dest[num_dest].sa.sin_port = htons(dest_port_hbo);

    num_dest++;

    return 0;

} // telem_dest_table::add

//
// telem_dest_table::delete_by_index - delete a destination at a specified index
//
void telem_dest_table::delete_by_index(int index)
{

    (void)close(dest[index].fd);

    for (int i = index; i < (DEST_MAX - 1); i++)
        memcpy(&dest[i], &dest[i + 1], sizeof(telem_dest));

    memset(&dest[DEST_MAX - 1], 0, sizeof(telem_dest));
    dest[DEST_MAX - 1].fd = -1;

    num_dest--;

} // telem_dest_table::delete_by_index

//
// telem_dest_table::find_by_mac_ip - find a destination with a specified mac and IP
//
int telem_dest_table::find_by_mac_ip(const uint8_t *mac, const in_addr_t ip) const
{
    int i;

    for (i = 0; i < num_dest; i++)
        if (memcmp(mac, dest[i].mac, MAC_LEN) == 0 && ip == dest[i].sa.sin_addr.s_addr)
            return i;

    return -1;

} // telem_dest_table::find_by_mac_ip
