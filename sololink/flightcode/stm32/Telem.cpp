#include <string>
#include <unistd.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <syslog.h>
#include <arpa/inet.h>
#include "Telem.h"
#include "SerialLog.h"
#include "packetTypes.h"
#include "net_wmm.h"
#include "../mavlink/c_library/common/mavlink.h"
#include "SLIP.h"
#include "util.h"
#include "link_packet.h"

Telem::Telem(string ipaddr, int port, unsigned log_gap_us, unsigned log_delay_max,
             string &log_delay_filename)
    : PacketHandler(ipaddr, port, 0xe0, PKT_ID_MAVLINK), _log_gap_us(log_gap_us),
      _log_delay_max(log_delay_max), _log_delay_filename(log_delay_filename), _fp_delay(NULL),
      _delay_cnt(0)
{
    pkt_delay_open();
}

/***********************************************************************
Method: Telem data handler

Description: Transmits telem data from UDP to STM32 via serial
***********************************************************************/
void Telem::downHandler(int ser_fd, int verbosity)
{
    LinkPacket packet;
    socklen_t addrlen = sizeof(_sock);
    int recvlen;
    char msg[1024];
    int encodedLen;
    SLIPEncoder *slipEnc = new SLIPEncoder(msg, sizeof(msg));
    static uint64_t last_stm_recv_us = 0;

    // Attempt to receive data.  This should be good since we got here from
    // a select()
    recvlen = recvfrom(_sock_fd, &packet, sizeof(packet), 0, (struct sockaddr *)&_sock, &addrlen);

    packet.stm_recv_us = clock_gettime_us(CLOCK_MONOTONIC);

    // Log any gaps in telemetry >= _log_gap_us
    if (last_stm_recv_us != 0) {
        unsigned gap_us = packet.stm_recv_us - last_stm_recv_us;
        if (gap_us >= _log_gap_us)
            syslog(LOG_INFO, "telem gap %u msec", (gap_us + 500) / 1000);
    }
    last_stm_recv_us = packet.stm_recv_us;

    pkt_delay_write(packet);

#ifdef INCLUDE_SERIAL_LOG
    extern SerialLog *serialLog;
#endif

    char *b;
    uint8_t *p_payload = packet.payload;
    while (p_payload < ((uint8_t *)&packet + recvlen)) {

        /* Make sure this is a mavlink packet */
        if (p_payload[0] != 0xFE) {
            syslog(LOG_ERR, "pkt: Got a bad mavlink packet in the LinkPacket");
            break;
        }

        // Since this should always be mavlink, make sure its not a dataflash log type
        // Check index 5 for the message type
        if (p_payload[5] == MAVLINK_MSG_ID_LOG_DATA ||
            p_payload[5] == MAVLINK_MSG_ID_LOG_DATA_LEN ||
            p_payload[5] == MAVLINK_MSG_ID_LOG_DATA_CRC)
            goto move_on;

        /* Use the existing packet, even though we'll lose some data.
         * Stick the id type before the start of the mavlink message.*/
        b = (char *)(p_payload - 1);
        b[0] = _pktID;
        encodedLen = slipEnc->encode(b, (p_payload[1] + 8) + 1);

#ifdef INCLUDE_SERIAL_LOG
        // Note that dataflash downlink is not logged,
        // since it is not sent to the STM32
        serialLog->log_packet(b, encodedLen, SerialLog::PKTFLG_DOWN);
#endif // INCLUDE_SERIAL_LOG

        if (write(ser_fd, msg, encodedLen) != encodedLen)
            syslog(LOG_ERR, "pkt: error writing to serial port");
    move_on:
        p_payload += p_payload[1] + 8;
    }
}

void Telem::pkt_delay_open(void)
{

    // packet time delay log enabled by setting _log_delay_filename != ""
    if (_log_delay_filename != "") {
        // If the file exists, this truncates it and starts over ("w", not "a").
        // The edge case to avoid is if the rename below fails for whatever
        // reason, this file does not grow forever (eating RAM).
        _fp_delay = fopen(_log_delay_filename.c_str(), "w");
        if (_fp_delay != NULL) {
            char time_buf[40];
            fprintf(_fp_delay, "\n");
            fprintf(_fp_delay, "starting: %s\n", clock_gettime_str_r(CLOCK_REALTIME, time_buf));
            fprintf(_fp_delay, "seq,read_len,blocked,tf_recv,tf_send,tc_recv,tc_send,stm_recv\n");
            fflush(_fp_delay);
        }
    }

} // Telem::pkt_delay_open

void Telem::pkt_delay_write(LinkPacket &packet)
{
    if (_fp_delay == NULL)
        return;

    fprintf(_fp_delay, "%u,%u,%u,%llu,%llu,%llu,%llu,%llu\n", packet.seq, packet.data1,
            packet.data2, packet.tf_recv_us, packet.tf_send_us, packet.tc_recv_us,
            packet.tc_send_us, packet.stm_recv_us);

    _delay_cnt++;
    if (_delay_cnt < _log_delay_max) {
        fflush(_fp_delay);
        return;
    }

    // move file.csv to file.csv.1 (losing the old .1 if it exists),
    // and open a new file.csv

    fclose(_fp_delay);
    _fp_delay = NULL;
    _delay_cnt = 0;

    string fn_new = _log_delay_filename + ".1";

    // if the rename fails, we lose the .1 file and start over with the new one
    (void)rename(_log_delay_filename.c_str(), fn_new.c_str());

    pkt_delay_open();

} // Telem::pkt_delay_write
