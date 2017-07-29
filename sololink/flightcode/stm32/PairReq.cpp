#include <sys/types.h>
#include <sys/socket.h>
#include <syslog.h>
#include <string.h>
#include "PairReq.h"

using namespace std;

// This is really a pair confirm message and should be a separate handler from
// pair request (down is pair request, up is pair confirm, but with different
// packet IDs).

int PairReq::upHandler(char serBuf[], int len)
{
    int nBytes;

    syslog(LOG_INFO, "pair confirm going up for \"%s\"", serBuf);

    nBytes = strlen(serBuf) + 1;

    nBytes = sendto(_sock_fd, serBuf, nBytes, 0, (struct sockaddr *)&_sock, sizeof(_sock));

    if (nBytes == -1) {
        syslog(LOG_ERR, "PairReq: sendto failed");
        nBytes = 0;
    }

    return nBytes;
}
