#include <syslog.h>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include "PacketHandler.h"
#include "SLIP.h"
#include <arpa/inet.h>
#include "SerialLog.h"

using namespace std;

#define BUFSIZE 4096

/***********************************************************************
Method: PacketHandler constructor

Description: Sets up the PacketHandler UDP port based on an ip address string,
             port, TOS value, and pktID type.
 ***********************************************************************/
PacketHandler::PacketHandler(string ipaddr, int port, int tos, int pktID) : _pktID(pktID)
{
    // TODO: Handle a failure of opening the socket
    // TODO: put a timeout on this port in case the select messes up

    /* create a UDP socket */
    if ((_sock_fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        syslog(LOG_ERR, "pkt: cannot create socket");
        return;
    }

    /* bind the socket to any valid IP address and a specific port */
    memset((char *)&_sock, 0, sizeof(_sock));
    _sock.sin_family = AF_INET;

    if (ipaddr != "") // If its empty, we let the overriding methods handle it
        inet_aton(ipaddr.c_str(), &_sock.sin_addr);

    _sock.sin_port = htons(port);

    if (bind(_sock_fd, (struct sockaddr *)&_sock, sizeof(_sock)) < 0) {
        syslog(LOG_ERR, "pkt: bind failed on port %d", port);
        return;
    }

    setsockopt(_sock_fd, IPPROTO_IP, IP_TOS, &tos, sizeof(tos));

    syslog(LOG_INFO, "pkt: opened port %d", port);
}

int PacketHandler::upHandler(char serBuf[], int len)
{
    int bytesSent;

    // We should have already stripped the pktID and decoded
    // the data, so send it along!
    // Ignore any errors.
    bytesSent = sendto(_sock_fd, serBuf, len, 0, (struct sockaddr *)&_sock, sizeof(_sock));

    if (bytesSent > 0)
        return bytesSent;

    return 0;
}

void PacketHandler::downHandler(int ser_fd, uint32_t debug)
{
    char buf[BUFSIZE];
    socklen_t addrlen = sizeof(_sock);
    int recvlen;
    char msg[1024];
    int encodedLen;
    // downHandler() only called in the context of stm32.cpp::downstream_task
    // so a single instance of slipEnc is okay
    static SLIPEncoder *slipEnc = new SLIPEncoder(msg, sizeof(msg));

    // First byte is the data type.  This will be
    // left alone by the SLIP encoding, so its ok to put it in now
    buf[0] = _pktID;

    // Attempt to receive data.  This should be good since we got here from
    // a select()
    recvlen = recvfrom(_sock_fd, &buf[1], BUFSIZE, 0, (struct sockaddr *)&_sock, &addrlen);

#ifdef INCLUDE_SERIAL_LOG
    extern SerialLog *serialLog;
    serialLog->log_packet(buf, recvlen + 1, SerialLog::PKTFLG_DOWN);
#endif // INCLUDE_SERIAL_LOG

    // Pack this data with slip encoding and dump it down to the STM32
    // Remember that we prepended the packet type
    encodedLen = slipEnc->encode(buf, recvlen + 1);

    if (debug & (1 << _pktID)) {
        char buf[200];
        char *p = buf;
        int m = sizeof(buf) - 1;

        memset(buf, 0, sizeof(buf));

        for (int i = 0; i < encodedLen; i++) {
            int n = snprintf(p, m, "%02x ", (unsigned)(msg[i]));
            if (n >= m)
                break;
            p += n;
            m -= n;
        }

        syslog(LOG_INFO, "%s", buf);
    }

    if (encodedLen < 0)
        syslog(LOG_ERR, "pkt: slip error");

    if (write(ser_fd, msg, encodedLen) != encodedLen)
        syslog(LOG_ERR, "pkt: could not write to serial port");
}
