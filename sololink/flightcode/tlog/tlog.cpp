#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <sched.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netdb.h>
#include <time.h>
#include <sys/time.h>
#include <termios.h>
#include <sys/mman.h>
#include <fstream>
#include <sstream>
#include <vector>
#include <arpa/inet.h>
#include <cmath>
#include <iomanip>
#include <signal.h>
#include <sys/stat.h>
#include "Log.h"
#include "../mavlink/c_library/common/mavlink.h"
#include "../mavlink/c_library/ardupilotmega/mavlink.h"
#include "util.h"

using namespace std;

/***********************************************************************
UDP macros
***********************************************************************/
#define BUFSIZE 4096

/***********************************************************************
File descriptors
***********************************************************************/
int sock_fd;

/***********************************************************************
TLOG source port from telem_ctrl.py
***********************************************************************/
#define TLOG_SOURCE_PORT 14583

/***********************************************************************
Log file
***********************************************************************/
Log *logfile;

/***********************************************************************
Max log file size
***********************************************************************/
#define MAX_LOGFILE_SIZE 100000000 // 100MB
#define MAX_LOG_FILES 9

/***********************************************************************
Log check timeout
***********************************************************************/
#define LOG_CHECK_US 5000000 // Check every 5s

/***********************************************************************
 Logfile directory and name
 (directory can come from environment)
***********************************************************************/
#define LOGFILE_DIR "/log"
#define LOGFILE_NAME "solo.tlog"

/***********************************************************************
Function: int UDP_setup(void)

Description: Sets up the UDP receive port.  Returns 0 in the event of
             an error, 1 otherwise.
***********************************************************************/
int UDP_setup(void)
{
    struct sockaddr_in myaddr; /* our address */
    struct timeval timeout;
    int sourcePort = TLOG_SOURCE_PORT;

    /* create a UDP socket */
    if ((sock_fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        cerr << "cannot create socket" << endl;
        return 0;
    }

    /* Socket timeout */
    timeout.tv_sec = 0;
    timeout.tv_usec = 1000; // 1ms
    setsockopt(sock_fd, SOL_SOCKET, SO_RCVTIMEO, (char *)&timeout, sizeof(timeout));

    /* Bind the socket to any IP, but we'll check the source later */
    memset((char *)&myaddr, 0, sizeof(myaddr));
    myaddr.sin_family = AF_INET;
    myaddr.sin_addr.s_addr = htonl(INADDR_ANY);
    myaddr.sin_port = htons(sourcePort);

    if (bind(sock_fd, (struct sockaddr *)&myaddr, sizeof(myaddr)) < 0) {
        cerr << "bind failed" << endl;
        return 0;
    }

    cout << "Successfully opened port " << sourcePort << endl;
    return 1;
}

/***********************************************************************
Function: void dump_versions(void)

Description: Reads the sololink, artoolink, artoo, and pixhawk versions
             and dumps them into the tlog as statustext
***********************************************************************/
void dump_versions(void)
{
    string s_sl_ver("UNK");                                // Sololink version
    string s_pix_ver("UNK");                               // Pixhawk version
    string s_al_ver("UNK");                                // Artoolink version
    string s_a_ver("UNK");                                 // Artoo (STM32) version
    string s_all_vers;                                     // The whole statustext string
    char stringbuf[MAVLINK_MSG_STATUSTEXT_FIELD_TEXT_LEN]; // String buffer for mav pack
    ifstream infile;                                       // File for reading
    mavlink_message_t mav_msg;  // Mavlink message for statustext versions
    uint64_t usec;              // Timestamp
    char msg[BUFSIZE + 8];      // Message including timestamp to dump to file
    unsigned char buf[BUFSIZE]; // mavlink message in char buffer
    unsigned len;

    // Read the Pixhawk verison number
    infile.open("/tmp/PEER_FW_VERSION", ifstream::in);
    if (!infile)
        cerr << "Unable to open pixhawk firmware version file" << endl;
    else {
        getline(infile, s_pix_ver);
        if (!infile)
            cerr << "Error reading Pixhawk firmware version" << endl;
        infile.close();
    }

    // Read the SoloLink version number
    infile.open("/tmp/PEER_SL_VERSION", ifstream::in);
    if (!infile)
        cerr << "Unable to open Sololink firmware version file" << endl;
    else {
        getline(infile, s_sl_ver);
        if (!infile)
            cerr << "Error reading Sololink firmware version" << endl;
        infile.close();
    }

    // Read the Artoolink version number
    infile.open("/VERSION", ifstream::in);
    if (!infile)
        cerr << "Unable to open Artoolink firmware version file" << endl;
    else {
        getline(infile, s_al_ver);
        if (!infile)
            cerr << "Error reading Artoolink firmware version" << endl;
        infile.close();
    }

    // Read the Artoo (STM32) version number
    infile.open("/STM_VERSION", ifstream::in);
    if (!infile)
        cerr << "Unable to open Artoo STM32 firmware version file" << endl;
    else {
        getline(infile, s_a_ver);
        if (!infile)
            cerr << "Error reading Artoo STM32 firmware version" << endl;
        infile.close();
    }

    // Create a STATUSTEXT mavlink message to dump in the log.
    s_all_vers = "P:" + s_pix_ver + " SL:" + s_sl_ver + " AL:" + s_al_ver + " A:" + s_a_ver;

    // Copy 49 characters (save room for a null terminator), truncating.
    memset(stringbuf, 0, sizeof(stringbuf));
    len = s_all_vers.length();
    if (len >= 50)
        len = 49;
    memcpy(stringbuf, s_all_vers.c_str(), len);

    // Pack into a statustext message
    mavlink_msg_statustext_pack(0, 0, &mav_msg, MAV_SEVERITY_INFO, stringbuf, 0, 0);

    // Pull the char buffer out of the mavlink message (len reused here)
    len = mavlink_msg_to_send_buffer((uint8_t *)buf, &mav_msg);

    // This should be thread safe, it happens atomically in UDP_task or
    // before UDP_task is started
    usec = clock_gettime_us(CLOCK_REALTIME);

    for (int i = 0; i < 8; ++i)
        msg[i] = usec >> (8 - (i + 1)) * 8;

    memcpy(msg + sizeof(uint64_t), buf, len);
    logfile->log_fd.write((const char *)msg, len + sizeof(uint64_t));
    logfile->log_fd.flush();
}

/***********************************************************************
Function: void UDP_task(void)

Description: The main UDP task.  Waits for data on the telem UDP
             and just dumps it into the tlog file.
***********************************************************************/
void UDP_task(void)
{
    int recvlen;                /* # bytes received */
    unsigned char buf[BUFSIZE]; /* receive buffer */
    unsigned char *buf_ptr;
    int msglen;
    struct sockaddr_in srcAddr;
    socklen_t slen = sizeof(srcAddr);
    uint64_t usec;
    char msg[BUFSIZE + 8];
    mavlink_message_t mav_msg;
    mavlink_status_t mav_status;
    mavlink_heartbeat_t heartbeat;
    bool armedState = false;
    uint64_t last, now;

    last = clock_gettime_us(CLOCK_MONOTONIC);

    while (true) {
        // Attempt to receive data
        recvlen = recvfrom(sock_fd, buf, BUFSIZE, 0, (sockaddr *)&srcAddr, &slen);

        // TODO:we should check that this only comes from the Artoo
        if (recvlen > 0) {
            /* We can get multiple messages per udp datagram, so run through them all */
            buf_ptr = buf;
            while (1) {
                /*Make sure this is a mavlink message.  If its not, bail out of this whole thing */
                if (buf_ptr[0] != 0xFE)
                    break;

                msglen = buf_ptr[1] + 8;

                // If we get a "disarm" from MAVLINK, roll the log here
                if (buf_ptr[5] == MAVLINK_MSG_ID_HEARTBEAT) {
                    for (int i = 0; i < msglen; ++i) {
                        if (mavlink_parse_char(MAVLINK_COMM_0, buf_ptr[i], &mav_msg, &mav_status)) {
                            mavlink_msg_heartbeat_decode(&mav_msg, &heartbeat);
                            if (heartbeat.base_mode & MAV_MODE_FLAG_SAFETY_ARMED) {
                                if (!armedState)
                                    armedState = true;
                            } else {
                                if (armedState) {
                                    logfile->forceRoll();
                                    dump_versions(); // Dump the versions into each new file
                                    armedState = false;
                                }
                            }
                        }
                    }
                }

                usec = clock_gettime_us(CLOCK_REALTIME);

                for (int i = 0; i < 8; ++i)
                    msg[i] = usec >> (8 - (i + 1)) * 8;

                memcpy(msg + sizeof(uint64_t), buf_ptr, msglen);

                logfile->log_fd.write((const char *)msg, msglen + sizeof(uint64_t));
                logfile->log_fd.flush();

                buf_ptr += msglen;
                if (buf_ptr >= (buf + recvlen))
                    break;
            }
        }

        now = clock_gettime_us(CLOCK_MONOTONIC);

        // Check if we need to roll the logfile
        if ((now - last) > LOG_CHECK_US) {
            logfile->checkSizeAndRoll();
            last = now;
        }
    }
}

/**********************************************************************
Function: int main(void)

Description: The main function.  Initializes and runs the serial and
             UDP threads.
***********************************************************************/
int main(void)
{
    logfile = new Log("/log/solo.tlog", MAX_LOGFILE_SIZE, MAX_LOG_FILES, true);

    if (!logfile->log_fd) {
        cerr << "Unable to open logfile" << endl;
        return -1;
    }

    // Dump the versions of each system into the log file
    dump_versions(); // Dump the versions into each new file

    /* Set up the UDP and serial ports */
    if (!UDP_setup()) {
        cerr << "Unable to initialize the UDP receive" << endl;
        return -1;
    }

    // We'll enter an infinite loop here
    UDP_task();

    return -1;
}
