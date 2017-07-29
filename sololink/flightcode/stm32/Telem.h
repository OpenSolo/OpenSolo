#ifndef _TELEM_H_
#define _TELEM_H_

#include <string>
#include <stdio.h>
#include "link_packet.h"
#include "PacketHandler.h"

/***********************************************************************
Class: The telem class.

Description:  Creates a UDP socket for telemetry data, which is sent
              bidirectionally to and from the stm32.
***********************************************************************/

class Telem : public PacketHandler
{
public:
    // Constructor.  Takes an IP address and port
    Telem(string ipaddr, int port, unsigned log_gaps_us, unsigned pkt_delay_max,
          string &pkt_delay_filename);

    // Special downhandler that checks mavlink types
    void downHandler(int ser_fd, int verbosity = 0);

private:
    void pkt_delay_open(void);
    void pkt_delay_write(LinkPacket &packet);
    unsigned _log_gap_us;
    unsigned _log_delay_max;
    string _log_delay_filename;
    FILE *_fp_delay;
    unsigned _delay_cnt;
};

#endif //_TELEM_H
