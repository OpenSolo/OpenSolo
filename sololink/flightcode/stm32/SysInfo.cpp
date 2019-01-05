#include <iostream>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <syslog.h>
#include <arpa/inet.h>
#include "SysInfo.h"
#include "packetTypes.h"

using namespace std;

/*
The packet ID has already been stripped from the front. The packet as
received here looks like this (names are from artoo source):

    --DATA--------------  --LENGTH--------------------  --AS OF 9/25/14---
    Sys::UniqueId         Sys::UniqueIdLen              12 bytes
    Sys::HardwareVersion  sizeof(Sys::HardwareVersion)  2 bytes
    Version::str()        strlen(Version::str())        variable
    --------------------  ----------------------------  ------------------

The UniqueId and HardwareVersion are (9/25/14) compiled-in, and the
version string is generated at build time from `git describe --tags`.
*/

static unsigned pingCount = 0;

int SysInfo::upHandler(char serBuf[], int len)
{
    const unsigned uniqueIdLen = 12; // match artoo/src/stm32/sys.h
    uint8_t uniqueId[uniqueIdLen];
    uint16_t hardwareVersion; // match artoo/src/hostprotocol.cpp, hwversion
    char version[64];         // typically around 8 chars
    static bool infoLogged = false;

    if (len < 14)
        syslog(LOG_ERR, "sys: message too short (%d)", len);

    memcpy(uniqueId, &serBuf[0], sizeof(uniqueId));

    memcpy(&hardwareVersion, &serBuf[12], sizeof(hardwareVersion));

    // make sure version is \0 terminated
    // variable length, from 14 to end of message
    unsigned copyLen = len - 14;
    if (copyLen > (sizeof(version) - 1))
        copyLen = sizeof(version) - 1;
    memset(version, 0, sizeof(version));
    memcpy(version, &serBuf[14], copyLen);

    if (!infoLogged) {
        char uid[40]; // need 36
        snprintf(uid, sizeof(uid), "%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x",
                 uniqueId[0], uniqueId[1], uniqueId[2], uniqueId[3], uniqueId[4], uniqueId[5],
                 uniqueId[6], uniqueId[7], uniqueId[8], uniqueId[9], uniqueId[10], uniqueId[11]);
        syslog(LOG_INFO, "sys: unique id: %s", uid);
        syslog(LOG_INFO, "sys: hardware ver: %u", hardwareVersion);
        syslog(LOG_INFO, "sys: software ver: %s", version);
        syslog(LOG_INFO, "sys: (try %u)", pingCount);
        infoLogged = true;
    }

    return 0; // we don't send anything
}

// Sends a blank byte to the STM32 as a "ping"
// Note that this send is using a socket to send to itself; seems odd, but the
// point is to enqueue the message for the downstream thread to send over
// serial, i.e. the send is generally from a different thread than the receive
// will be.
void SysInfo::ping(void)
{
    char buf = ' ';
    sendto(_sock_fd, &buf, 1, 0, (struct sockaddr *)&_sock, sizeof(_sock));
    pingCount++;
}
