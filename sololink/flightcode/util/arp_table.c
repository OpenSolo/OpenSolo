
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "util.h"
#include "arp_table.h"

/*
* arp_table_get - get arp table
*
* Read /proc/net/arp and fill in arp_table.
*
* /proc/net/arp:
* IP address       HW type     Flags       HW address            Mask     Device
* 10.1.1.112       0x1         0x2         04:8d:38:7f:1e:20     *        wlan0-ap
* 10.1.1.10        0x1         0x2         00:1f:09:04:00:22     *        wlan0-ap
*
* On success, arp_table is filled in with arp entries, arp_entries is set to
* the number of entries, and zero is returned. On error, nonzero is returned.
*/
int arp_table_get(arp_entry_t *arp_table, int *arp_entries)
{
    int status = 0;
    FILE *fp;
    char linebuf[200];
    int entries;

    if (arp_table == NULL || arp_entries == NULL)
        return -1;

    fp = fopen("/proc/net/arp", "r");
    if (fp == NULL)
        return -1;

    memset(arp_table, 0, *arp_entries * sizeof(arp_entry_t));
    entries = 0;

    /* skip first line */
    fgets(linebuf, sizeof(linebuf), fp);

    /* read entries, one per line */
    while (fgets(linebuf, sizeof(linebuf), fp) != NULL) {
        char *saveptr;
        char *token;
        unsigned token_len;
        char *endptr;
        unsigned token_val;
        struct in_addr ip;

        /* get first token (IP address, "10.1.1.112") */
        token = strtok_r(linebuf, " ", &saveptr);
        if (token == NULL) {
            status = -1;
            break; /* error getting first token in line */
        }
        token_len = strlen(token);
        if (token_len == 0 || !inet_aton(token, &ip)) {
            status = -1;
            break; /* error parsing token */
        }
        arp_table[entries].ip = ip.s_addr;

        /* get next token (HW type, "0x1") */
        token = strtok_r(NULL, " ", &saveptr);
        if (token == NULL) {
            status = -1;
            break; /* error getting next token in line */
        }
        endptr = NULL;
        token_val = strtol(token, &endptr, 0);
        if (*endptr != '\0') {
            status = -1;
            break; /* error converting token */
        }
        arp_table[entries].hw_type = token_val;

        /* get next token (Flags, "0x2") */
        token = strtok_r(NULL, " ", &saveptr);
        if (token == NULL) {
            status = -1;
            break; /* error getting next token in line */
        }
        endptr = NULL;
        token_val = strtol(token, &endptr, 0);
        if (*endptr != '\0') {
            status = -1;
            break; /* error converting token */
        }
        arp_table[entries].flags = token_val;

        /* get HW address ("04:8d:38:7f:1e:20") */
        token = strtok_r(NULL, " ", &saveptr);
        if (token == NULL) {
            status = -1;
            break; /* error getting next token in line */
        }
        if (mac_aton(token, arp_table[entries].mac) == NULL) {
            status = -1;
            break; /* error converting token to mac address */
        }

        /* get next token (Mask, "*") */
        token = strtok_r(NULL, " ", &saveptr);
        if (token == NULL) {
            status = -1;
            break; /* error getting next token in line */
        }
        /* token not used */

        /* get next token (Device, "wlan0-ap") */
        token = strtok_r(NULL, " \n", &saveptr);
        if (token == NULL) {
            status = -1;
            break; /* error getting next token in line */
        }
        strncpy(arp_table[entries].dev, token, DEV_NAME_MAX - 1);

        entries++;
        if (entries >= *arp_entries) {
            /* return success (leave status = 0) */
            break; /* filled up user-supplied table */
        }

    } /* while (fgets...) */

    fclose(fp);

    *arp_entries = entries;

    return status;

} /* arp_table_get */

/*
* arp_table_find_ip - find entry in arp table using ip as key
*
* Returns index of entry, or -1 if not found.
*/
int arp_table_find_by_ip(arp_entry_t *arp_table, int arp_entries, in_addr_t ip)
{
    int i;

    for (i = 0; i < arp_entries; i++)
        if (ip == arp_table[i].ip)
            return i;

    return -1;

} /* arp_table_find_ip */

void arp_table_dump(int priority, const arp_entry_t *arp_table, int arp_entries)
{
    int i;

    syslog(priority, "arp_table:");

    for (i = 0; i < arp_entries; i++) {
        struct in_addr in;
        in.s_addr = arp_table[i].ip;
        const uint8_t *mac = arp_table[i].mac;
        syslog(priority, "%-15s 0x%x 0x%x %02x:%02x:%02x:%02x:%02x:%02x %s\n", inet_ntoa(in),
               arp_table[i].hw_type, arp_table[i].flags, mac[0], mac[1], mac[2], mac[3], mac[4],
               mac[5], arp_table[i].dev);
    }

} /* arp_table_dump */
