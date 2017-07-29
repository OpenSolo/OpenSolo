
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "net_stats.h"

/* The udp rx queue size is reported in multiples of some kernel-internal
 * buffer. We want the number of packets queued, which is presumably the
 * number of buffers. However, if we ever see a rx queue value that is not
 * a multiple of this, start reporting the raw number. */
#define UDP_RX_QUEUE_BUFSIZE 2496
int udp_rx_queue_bufsize_correct = 1; /* assume correct */

/*
* udp_info_get - get info about a udp port
*
* Read /proc/net/udp and fill in udp_info with status of a particular port.
* At the moment we only care about the rx queue size, so that is the only
* field in udp_info_t, and the only thing parsed from /proc/net/udp for the
* port.
*
* /proc/net/udp:
*    sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
* ref pointer drops
*    53: 00000000:0035 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 5842 2
* 86b0c500 0
*    67: 00000000:0043 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 5837 2
* 86b0c280 0
*   136: 00000000:A288 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 31927
* 2 86b0c780 0
*   141: 00000000:138D 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 31880
* 2 86b0cc80 0
*   205: 00000000:15CD 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 31982
* 2 86b0cf00 0
*   209: 00000000:CFD1 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 31855
* 2 86b0d180 0
*   224: 00000000:38E0 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 31870
* 2 86b0ca00 0
*
* Returns 0 on success, nonzero on error.
*/
int udp_info_get(unsigned port, udp_info_t *udp_info)
{
    int status = -1;
    FILE *fp;
    char linebuf[200];

    memset(udp_info, 0, sizeof(*udp_info));

    fp = fopen("/proc/net/udp", "r");
    if (fp == NULL)
        return -1;

    while (fgets(linebuf, sizeof(linebuf), fp) != NULL) {
        char *saveptr;
        char *token;
        unsigned token_len;
        char *endptr;
        unsigned token_val;

        /* get first token (sl, "53") */
        token = strtok_r(linebuf, " :", &saveptr);
        if (token == NULL)
            continue; /* error getting first token in line */
        token_len = strlen(token);
        if (token_len == 0)
            continue; /* odd... */
        if (!isdigit(token[0]))
            continue; /* first line, token is "sl" */
        /* token not used */

        /* get next token (local_address/IP, "00000000") */
        token = strtok_r(NULL, " :", &saveptr);
        if (token == NULL)
            continue; /* error getting next token in line */
        /* token not used */

        /* get third token local_address/port in hex */
        token = strtok_r(NULL, " :", &saveptr);
        if (token == NULL)
            continue; /* error getting next token in line */
        endptr = NULL;
        token_val = strtol(token, &endptr, 16);
        if (*endptr != '\0')
            continue; /* error converting token from hex to decimal */
        if (token_val != port)
            continue; /* not the port we're looking for */

        /* get next token (remote_address/IP, "00000000") */
        token = strtok_r(NULL, " :", &saveptr);
        if (token == NULL)
            continue; /* error getting next token in line */
        /* token not used */

        /* get next token (remote_address/port, "0000") */
        token = strtok_r(NULL, " :", &saveptr);
        if (token == NULL)
            continue; /* error getting next token in line */
        /* token not used */

        /* get next token (st, "07") */
        token = strtok_r(NULL, " :", &saveptr);
        if (token == NULL)
            continue; /* error getting next token in line */
        /* token not used */

        /* get next token (tx_queue, "00000000") */
        token = strtok_r(NULL, " :", &saveptr);
        if (token == NULL)
            continue; /* error getting next token in line */
        /* token not used */

        /* get next token (rx_queue, "00000000") */
        token = strtok_r(NULL, " :", &saveptr);
        if (token == NULL)
            continue; /* error getting next token in line */
        endptr = NULL;
        token_val = strtol(token, &endptr, 16);
        if (*endptr != '\0')
            continue; /* error converting token from hex to decimal */
        /* verify our assumed rx queue bufsize is correct */
        if ((token_val % UDP_RX_QUEUE_BUFSIZE) != 0)
            udp_rx_queue_bufsize_correct = 0;
        /* if correct, adjust the queue depth we are reporting */
        if (udp_rx_queue_bufsize_correct)
            token_val = token_val / UDP_RX_QUEUE_BUFSIZE;
        /* report queue depth */
        udp_info->rx_queue = token_val;

        /* not interested in any more fields; we are done */
        status = 0;
        break;

    } /* while (fgets...) */

    fclose(fp);

    return status;

} /* udp_info_get */
