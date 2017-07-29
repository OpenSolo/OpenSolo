#include <iostream>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <syslog.h>
#include <time.h>
#include <arpa/inet.h>
#include <errno.h>
#include "packetTypes.h"
#include "util.h"
#include "RC.h"

#define RC_BUFSIZE 26

/* How often to log a sendto() error */
#define SENDTO_LOG_DT_US 1000000

using namespace std;

/***********************************************************************
Method: RC constructor

Description: Sets up the RC UDP port based on an ip address string, port
             and TOS value.
             Call the base constructor, but store the solo IP address
             separately as we may not be connected to it at the moment
***********************************************************************/
RC::RC(string ipaddr, int port, int tos) : PacketHandler("", port, tos, PKT_ID_DSM_CHANNELS)
{
    // Set up the sequence number
    _sequence = 0;

    // We are not yet connected
    _connected = false;
}

/***********************************************************************
Method: RC message constructor

Description: Encodes the RC data in the following format:

he packet as received has the channel data starting at pkt[0].
Channel data is  little-endian.

    Start
    Byte    Size    Description
    0       2       Channel 0
    2       2       Channel 1
    4       2       Channel 2
    6       2       Channel 3
    8       2       Channel 4
    10      2       Channel 5
    12      2       Channel 6
    14      2       Channel 7
    16 (packet length)

    A packet as sent to a UDP port has the following format. All fields
    are little-endian.

    Start
    Byte    Size    Description
    0       8       Timestamp, usec since stm32 process started
    8       2       Sequence number
    10      2       Channel 0
    12      2       Channel 1
    14      2       Channel 2
    16      2       Channel 3
    18      2       Channel 4
    20      2       Channel 5
    22      2       Channel 6
    24      2       Channel 7
    26 (packet length)

***********************************************************************/
int RC::constructMessage(char inBuf[], char outBuf[], int inBufLen)
{
    uint64_t timestamp_us;

    // Note that this is CLOCK_REALTIME, vs. CLOCK_MONOTONIC used
    // in most other places.
    timestamp_us = clock_gettime_us(CLOCK_REALTIME);

    memcpy(outBuf, &timestamp_us, sizeof(timestamp_us));
    memcpy(&outBuf[8], &_sequence, sizeof(_sequence));
    memcpy(&outBuf[10], inBuf, inBufLen);

    ++_sequence;

    return (inBufLen + 10);
}

/***********************************************************************
Method: RC data handler

Description: Transmits RC data over the UDP.  Checks RC data for
             integrity, and logs if incorrect
***********************************************************************/
int RC::upHandler(char serBuf[], int len)
{
    char buf[RC_BUFSIZE];
    int n;
    int bytesSent;
    static uint64_t last_logerr_us = 0;
    uint64_t now_us;
    static int n_sendto_errs = 0;

    // Need to wait until we get the solo IP address from the
    // pair server before sending any RC data.
    if (!_connected)
        return 0;

    if (len != 16) {
        // this happens!
        int npr = 16;
        if (npr > len)
            npr = len;
        char buf[64];
        char *p = buf;
        int m = sizeof(buf) - 1;
        memset(buf, 0, sizeof(buf));
        for (int i = 0; i < npr; i++) {
            int n = snprintf(p, m, "%02x ", (unsigned)(serBuf[i]));
            if (n >= m)
                break;
            p += n;
            m -= n;
        }
        syslog(LOG_ERR, "bad RC packet (len=%d): %s", len, buf);
        return 0;
    }

    // Create the string to be sent
    n = constructMessage(serBuf, buf, len);

    // Send the data
    bytesSent = sendto(_sock_fd, buf, n, 0, (struct sockaddr *)&_sock, sizeof(_sock));

    if (bytesSent <= 0) {
        ++n_sendto_errs;

        // Log the error and the number of failures we've seen
        now_us = clock_gettime_us(CLOCK_MONOTONIC);
        if (now_us - last_logerr_us > SENDTO_LOG_DT_US) {
            syslog(LOG_ERR, "RC send failed (%i): %s\n", n_sendto_errs, strerror(errno));
            last_logerr_us = now_us;
            n_sendto_errs = 0;
        }

        return 0;
    }

    return bytesSent;
}

/***********************************************************************
Method: setSoloIP

Description: Sets the Solo IP after receiving it from the solo ip file
***********************************************************************/
void RC::setSoloIP(string *address)
{
    // Changing the socket is thread-safe because we check the
    //_connected flag in the upHandler.
    inet_aton(address->c_str(), &_sock.sin_addr);
    _connected = true;
}
