
#include <stdio.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "arp_table.h"

#define MAX_ARP_ENTRIES 10
arp_entry_t arp_table[MAX_ARP_ENTRIES];

int main(int argc, char *argv[])
{
    int arp_entries;
    int i;

    arp_entries = MAX_ARP_ENTRIES;
    if (arp_table_get(arp_table, &arp_entries) != 0) {
        printf("ERROR reading arp table\n");
        exit(1);
    }

    for (i = 0; i < arp_entries; i++) {
        struct in_addr in;
        in.s_addr = arp_table[i].ip;
        uint8_t *mac = arp_table[i].mac;
        printf("%-15s 0x%x 0x%x %02x:%02x:%02x:%02x:%02x:%02x %s\n", inet_ntoa(in),
               arp_table[i].hw_type, arp_table[i].flags, mac[0], mac[1], mac[2], mac[3], mac[4],
               mac[5], arp_table[i].dev);
    }

    exit(0);

} /* main */
