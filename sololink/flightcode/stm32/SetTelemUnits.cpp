
#include "packetTypes.h"
#include "SetTelemUnits.h"

// UDP port on local machine where downstream SetTelemUnits should be sent
unsigned SetTelemUnits::udpPort = 0;

SetTelemUnits::SetTelemUnits(int port) : PacketHandler("", port, 0x02, PKT_ID_SET_TELEM_UNITS)
{
    SetTelemUnits::udpPort = port;
}

void SetTelemUnits::set(string &setting)
{
    char buf = 1; // default is metric

    if (setting == "imperial")
        buf = 0;

    sendto(_sock_fd, &buf, 1, 0, (struct sockaddr *)&_sock, sizeof(_sock));
}
