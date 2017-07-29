#ifndef ARP_TABLE_H
#define ARP_TABLE_H

#include <stdint.h>
#include <netinet/in.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifndef MAC_LEN
#define MAC_LEN 6
#endif
#define DEV_NAME_MAX 16

typedef struct {
    in_addr_t ip; /* IP in network byte order */
    unsigned hw_type;
    unsigned flags;
    uint8_t mac[MAC_LEN];
    char dev[DEV_NAME_MAX];
} arp_entry_t;

extern int arp_table_get(arp_entry_t *arp_table, int *arp_entries);
extern int arp_table_find_by_ip(arp_entry_t *arp_table, int arp_entries, in_addr_t ip);
extern void arp_table_dump(int priority, const arp_entry_t *arp_table, int arp_entries);

#ifdef __cplusplus
};
#endif

#endif /* ARP_TABLE_H */
