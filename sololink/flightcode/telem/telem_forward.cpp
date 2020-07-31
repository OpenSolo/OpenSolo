#include <list>
#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/un.h>
#include <netdb.h>
#include <time.h>
#include <termios.h>
#include <sys/errno.h>
#include <sys/ioctl.h>
#include <arpa/inet.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <poll.h>
#include "util.h"
#include "RcLock.h"
#include "../mavlink/c_library/ardupilotmega/mavlink.h"
#include "../mavlink/c_library/common/mavlink.h"
#include "../ini/cpp/INIReader.h"
#include <signal.h>
#include <syslog.h>
#include "link_packet.h"
#include "net_wmm.h"

/***********************************************************************

This is the module that runs on Solo, relaying telemetry between the
Pixhawk and Artoo.

There is also a mechanism for other software on Solo to connect to
the telemetry stream.

***********************************************************************/

using namespace std;

/***********************************************************************
Timeouts
***********************************************************************/
#define LOG_DT_US 10000000         // 10s
#define CLIENT_TIMEOUT_US 10000000 // 10s
#define SEND_DT_US 100000          // 100ms

/***********************************************************************
UDP macros
***********************************************************************/
#define UDP_PORT 14560 // The incoming UDP port
#define BUFSIZE 4096

/***********************************************************************
Serial port name
***********************************************************************/
string serialPortName;

/***********************************************************************
GPS time usage control
***********************************************************************/
static bool useGpsTime = true;
static bool gotGpsTime = false;

/***********************************************************************
Thread IDs
***********************************************************************/
pthread_t upstream_ctx;
pthread_t downstream_ctx;
pthread_t logging_ctx;

static pthread_mutex_t mutex_upStats;
static pthread_mutex_t mutex_downStats;

/***********************************************************************
Thread priorities
Downstream is naturally rate-limited by receiving messages from the
UART (~200 usec for a 20 byte message at 921k baud). To avoid letting
an upstream storm block downstream messages, we make downstream
higher priority. A better arrangement might be to use a single thread
servicing both directions.
***********************************************************************/
#define UPSTREAM_PRIORITY 54
#define DOWNSTREAM_PRIORITY 55
#define LOG_PRIORITY 3

/***********************************************************************
File descriptors
***********************************************************************/
int sock_fd;
int serial_fd;
int inject_fd = -1;

/***********************************************************************
Log control (debug)
A bitmask, where each bit might enable certain things to the log file.
***********************************************************************/
static uint32_t logControl = 0;
#define LOG_CONTROL_MSG_COUNTS_DOWN 0x00000001

/***********************************************************************
List of ip/ports to send data to
***********************************************************************/
struct sockdata {
    struct sockaddr_in sa;
    uint64_t lastRecvTime_us;
};

// e.g. { 37 => { 23 => client1, 56 => client2 }, .... }
//  (seen system 37, components 23 and 56 from different clients)
pthread_mutex_t mutex_arp_table;
std::map< uint8_t, std::map< uint8_t, sockdata * > > arp_table;

list< sockdata * > clients;

/***********************************************************************
The artoo addr, which we always send to
***********************************************************************/
struct sockaddr_in artooaddr;

/***********************************************************************
Mutex for the client data

It is expected that only the upstream thread modifies the client list.
This allows the upstream thread to read the client list without
acquiring the mutex.
***********************************************************************/
pthread_mutex_t mutex_clients;

/***********************************************************************
The amount of data sent/received every cycle
***********************************************************************/

// from either pixhawk or injection port
static unsigned downMsgs = 0;
static unsigned downBytes = 0;

// from uplink UDP socket
static unsigned upMsgs = 0;
static unsigned upBytes = 0;

static unsigned upBadShort = 0;
static unsigned upBadMagic = 0;
static unsigned upBadLength = 0;

// specifically through the pixhawk serial interface
static unsigned serialDownBytes = 0;
static unsigned serialUpBytes = 0;

int serialBaud;
bool serialFlow = true;

// by mavlink ID
static const int ID_MIN = 0;
static const int ID_MAX = 256;
static unsigned downMsgsById[ID_MAX];

/* sigquit handling; we should probably join the threads and whatnot... */
void sigquit_handler(int signum)
{
    exit(0);
}

/***********************************************************************
 rc lockout
************************************************************************/
static bool rc_locked = false;

/***********************************************************************
Stream state

Monitor (downstream) message flows to detect sequence errors (dropped
messages). This is diagnostic only. Sequence is maintained per (sysid,
compid) pair.

We allow for unknown messages (those we cannot decode but will forward).
To prevent garbage data from tricking us into creating stream states
for lots of junk streams, we require a known message from a (sysid,
compid) in order to create a stream state for it. After that, we'll
accept unknown messages with that same (sysid, compid) as we check
the sequence for gaps.
***********************************************************************/

struct stream_state {
    uint8_t sysid;
    uint8_t compid;
    uint8_t seq;

    unsigned seq_err;

    stream_state(uint8_t sysid, uint8_t compid, uint8_t seq = 0)
        : sysid(sysid), compid(compid), seq(seq), seq_err(0)
    {
    }
};

// All streams we have seen messages for
list< stream_state > streams;

pthread_mutex_t mutex_streams;

/***********************************************************************
Function: int UDP_setup(void)

Description: Sets up the UDP port used for both upstream and
             downstream telemetry. Returns 0 in the event of an
             error, 1 otherwise.
***********************************************************************/
int UDP_setup(int tos)
{
    struct sockaddr_in myaddr;
    struct timeval timeout;

    /* create a UDP socket */
    if ((sock_fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        syslog(LOG_ERR, "can't create socket");
        return 0;
    }

    /* Socket timeout */
    timeout.tv_sec = 1;
    timeout.tv_usec = 0;
    if (setsockopt(sock_fd, SOL_SOCKET, SO_RCVTIMEO, (char *)&timeout, sizeof(timeout)) != 0) {
        syslog(LOG_ERR, "setsockopt (SO_RCVTIMEO) failed");
        return 0;
    }

    /* bind the socket to any valid IP address and a specific port */
    memset((char *)&myaddr, 0, sizeof(myaddr));
    myaddr.sin_family = AF_INET;

    /* Accept a connection from any IP.  */
    myaddr.sin_addr.s_addr = htonl(INADDR_ANY);
    myaddr.sin_port = htons(UDP_PORT);

    if (bind(sock_fd, (struct sockaddr *)&myaddr, sizeof(myaddr)) < 0) {
        syslog(LOG_ERR, "bind failed");
        return 0;
    }

    if (setsockopt(sock_fd, IPPROTO_IP, IP_TOS, &tos, sizeof(tos)) != 0) {
        syslog(LOG_ERR, "setsockopt (IP_TOS) failed");
        return 0;
    }

    syslog(LOG_INFO, "opened port %d", UDP_PORT);
    return 1;
}

/***********************************************************************
Function: int inject_setup(const char *sock_name)

Description: Initialize the unix-domain telemetry injection port.
             Anything sent to this port is injected into the down-
             bound telemetry stream. Packets written to this port are
             expected to be MAVLink packets, ready to copy into the
             stream. Returns 1 on success, 0 on error.
***********************************************************************/
int inject_setup(const char *sock_name)
{
    struct sockaddr_un un;

    if (strlen(sock_name) >= sizeof(un.sun_path)) {
        syslog(LOG_ERR, "inject socket name too long");
        return 0;
    }

    // If there is something already there with the socket name, it is
    // deleted. If not, unlink() fails (and we don't care).
    (void)unlink(sock_name);

    // create socket
    inject_fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (inject_fd < 0) {
        syslog(LOG_ERR, "creating inject socket");
        return 0;
    }

    // bind inject socket to address
    memset(&un, 0, sizeof(un));
    un.sun_family = AF_UNIX;
    strncpy(un.sun_path, sock_name, sizeof(un.sun_path) - 1);
    if (bind(inject_fd, (struct sockaddr *)&un, sizeof(un)) != 0) {
        syslog(LOG_ERR, "binding inject socket");
        close(inject_fd);
        inject_fd = -1;
        return 0;
    }

    return 1;
}

/***********************************************************************
Function: int serial_setup(int baud)

Description: The serial port initialization function.  This function
             initializes the serial port over which telemtry is sent
             to and received from the Pixhawk. A return of 0 indicates
             an error.
***********************************************************************/
int serial_setup(int baud)
{
    struct termios options;

    serial_fd = open(serialPortName.c_str(), O_RDWR | O_NOCTTY | O_NONBLOCK);

    if (serial_fd < 0) {
        syslog(LOG_ERR, "unable to open serial port %s", serialPortName.c_str());
        return 0;
    }

    // Configure port for 8N1 transmission
    tcgetattr(serial_fd, &options); // Gets the current options for the port
    // Set the output baud rate
    switch (baud) {
    case 1200:
        cfsetspeed(&options, B1200);
        break;
    case 2400:
        cfsetspeed(&options, B2400);
        break;
    case 4800:
        cfsetspeed(&options, B4800);
        break;
    case 9600:
        cfsetspeed(&options, B9600);
        break;
    case 19200:
        cfsetspeed(&options, B19200);
        break;
    case 38400:
        cfsetspeed(&options, B38400);
        break;
    case 57600:
        cfsetspeed(&options, B57600);
        break;
    case 115200:
        cfsetspeed(&options, B115200);
        break;
    case 500000:
        cfsetspeed(&options, B500000);
        break;
    case 921600:
        cfsetspeed(&options, B921600);
        break;
    case 1500000:
        cfsetspeed(&options, B1500000);
        break;
    default:
        syslog(LOG_ERR, "unsupported baud rate %d", baud);
        return 0;
    }
    options.c_iflag &= ~(IGNBRK | BRKINT | ICRNL | INLCR | PARMRK | INPCK | ISTRIP | IXON);
    options.c_oflag &= ~(OCRNL | ONLCR | ONLRET | ONOCR | OFILL | OPOST);
    options.c_lflag &= ~(ECHO | ECHONL | ICANON | IEXTEN | ISIG);
    options.c_cflag &= ~(CSIZE | PARENB);
    options.c_cflag |= (CS8 | CLOCAL);

    if (serialFlow)
        options.c_cflag |= CRTSCTS; // hardware flow control
    else
        options.c_cflag &= ~(CRTSCTS); // no hardware flow control

    // At 115k (87 us per char), reading 1 char at a time results in increased
    // CPU usage, since we actually can keep up with getting a small number of
    // characters per loop. At 921k (11 us per char), we get more characters
    // each time through the loop, so there is less advantage to setting VMIN
    // to more than 1.
    //
    //          CPU Usage at
    // VMIN     115k    921k
    //    1     7.0%    1.8%
    //   10     2.7%    1.6%
    //  100     1.2%    1.2%
    //
    // The problem with asking for more than 1 character per read is that each
    // message will usually not be received until some bytes in the following
    // message are available. That is often not a problem, but there are
    // sometimes gaps of several 10s of milliseconds in the telemetry stream,
    // and it is preferable to process messages as soon as they are available.
    if (baud <= 115200)
        options.c_cc[VMIN] = 10;
    else
        options.c_cc[VMIN] = 1;
    options.c_cc[VTIME] = 0;

    tcsetattr(serial_fd, TCSANOW, &options); // Set the new options for the port "NOW"

    syslog(LOG_INFO, "opened serial port %s", serialPortName.c_str());

    return 1;
}

void set_seen_sysid_compid_from_client(uint8_t target_system, uint8_t target_component,
                                       sockdata *client)
{
    pthread_mutex_lock(&mutex_arp_table);
    if (!arp_table[target_system][target_component]) {
        syslog(LOG_INFO, "ARP: Seen (%d/%d) from %s:%d client=%p", target_system, target_component,
               inet_ntoa(client->sa.sin_addr), ntohs(client->sa.sin_port), &client);
        arp_table[target_system][target_component] = client;
        arp_table[target_system][0] = client;
    }
    pthread_mutex_unlock(&mutex_arp_table);
}

bool seen_sysid_locked(uint8_t target_system)
{
    bool ret = true;
    if (arp_table.count(target_system) == 0) {
        ret = false;
    }
    if (ret && arp_table[target_system].count(0) == 0) {
        ret = false;
    }
    return ret;
}
bool seen_sysid(uint8_t target_system)
{
    bool ret;
    pthread_mutex_lock(&mutex_arp_table);
    ret = seen_sysid_locked(target_system);
    pthread_mutex_unlock(&mutex_arp_table);
    return ret;
}

bool seen_sysid_compid(uint8_t target_system, uint8_t target_component)
{
    bool ret = true;
    pthread_mutex_lock(&mutex_arp_table);
    if (!seen_sysid_locked(target_system)) {
        ret = false;
    }
    if (ret && !arp_table[target_system].count(target_component)) {
        ret = false;
    }
    pthread_mutex_unlock(&mutex_arp_table);
    return ret;
}

bool clients_match(const sockdata *a, const sockdata *b)
{
    if (a == NULL || b == NULL) {
        // should never get here
        return false;
    }
    return (a->sa.sin_port == b->sa.sin_port && a->sa.sin_addr.s_addr == b->sa.sin_addr.s_addr);
}

void purge_client_from_arp_table(sockdata *client)
{
    pthread_mutex_lock(&mutex_arp_table);
    for (std::map< uint8_t, std::map< uint8_t, sockdata * > >::iterator it = arp_table.begin();
         it != arp_table.end(); it++) {
        std::map< uint8_t, sockdata * >::iterator next = (*it).second.begin();
        for (std::map< uint8_t, sockdata * >::iterator iv = next; iv != (*it).second.end();
             iv = next) {
            next++;
            const sockdata *some_client = (*iv).second;
            if (clients_match(some_client, client)) {
                const uint8_t target_system = (*it).first;
                const uint8_t target_component = (*iv).first;
                syslog(LOG_INFO, "ARP: Purging (%d/%d) from %s:%d client=%p", target_system,
                       target_component, inet_ntoa(client->sa.sin_addr), ntohs(client->sa.sin_port),
                       &client);
                (*it).second.erase(target_component);
            }
        }
    }
    pthread_mutex_unlock(&mutex_arp_table);
}

struct sockdata *find_client(uint64_t now_us, struct sockaddr_in remaddr)
{
    // If this is a new client, add them to the send list
    // Maybe better to do this with find_if() and a search function but...
    // If we do find a match, update its latest received time

    for (list< sockdata * >::iterator it = clients.begin(); it != clients.end(); ++it) {
        if ((*it)->sa.sin_addr.s_addr == remaddr.sin_addr.s_addr &&
            (*it)->sa.sin_port == remaddr.sin_port) {
            return (*it);
        }
    }

    // Skip the artoo address
    if ((remaddr.sin_addr.s_addr == artooaddr.sin_addr.s_addr &&
         remaddr.sin_port == artooaddr.sin_port)) {
        return NULL;
    }
    syslog(LOG_INFO, "adding new client %s:%d", inet_ntoa(remaddr.sin_addr),
           ntohs(remaddr.sin_port));

    struct sockdata *client = new sockdata();
    client->sa = remaddr;

    pthread_mutex_lock(&mutex_clients);
    clients.push_back(client);
    pthread_mutex_unlock(&mutex_clients);

    return client;
}

/***********************************************************************
Function: void *upstream_task(void*)

Description: The upstream thread task. Checks for data available on the
             UDP and puts it in the serial port.

             Maintains client list: all "clients" receive the telemetry
             stream from Pixhawk. A client is added to the list by
             sending any telemetry upstream (to the UDP port). A client
             is removed from the list if it has not sent anything
             upstream for a while.
***********************************************************************/
void check_client_timeouts(uint64_t now_us);
void *upstream_task(void *)
{
    int recvlen;
    struct sockaddr_in remaddr;
    socklen_t addrlen = sizeof(remaddr);
    unsigned char buf[BUFSIZE];
    list< sockdata >::iterator it, next;
    uint64_t now_us;
    int txBufUsage;
    mavlink_message_t mav_msg;
    mavlink_status_t mav_status;
    mavlink_command_long_t mav_cmd_long;
    int i;
    bool discard;

    uint64_t next_client_timeout_check = 0;
    uint32_t client_timeout_check_interval = 5000000; // every 5 seconds

    while (true) {
        // Attempt to receive data, this will timeout
        recvlen = recvfrom(sock_fd, buf, BUFSIZE, 0, (struct sockaddr *)&remaddr, &addrlen);

        now_us = clock_gettime_us(CLOCK_MONOTONIC);

        if (recvlen < 0) {
            if (errno != EAGAIN)
                syslog(LOG_ERR, "upstream socket error: %s", strerror(errno));

            if (next_client_timeout_check < now_us) {
                check_client_timeouts(now_us);
                next_client_timeout_check = now_us + client_timeout_check_interval;
            }

            continue;
        }

        struct sockdata *client = find_client(now_us, remaddr);

        if (recvlen > 0) {

            // check that datagram can be a valid mavlink message
            bool good_stx = false;
            uint8_t framing_bytecount;
            switch (buf[0]) {
            case MAVLINK_STX:
                good_stx = true;
                framing_bytecount = MAVLINK_CORE_HEADER_LEN + MAVLINK_NUM_CHECKSUM_BYTES + 1;
                break;
            case MAVLINK_STX_MAVLINK1:
                good_stx = true;
                framing_bytecount = MAVLINK_CORE_HEADER_MAVLINK1_LEN + MAVLINK_NUM_CHECKSUM_BYTES + 1;
                break;
            default:
                break;
            }
            if (!good_stx) {
                // bad magic - first byte should always be a magic value
                pthread_mutex_lock(&mutex_upStats);
                upBadMagic++;
                pthread_mutex_unlock(&mutex_upStats);
            } else if (recvlen < framing_bytecount) {
                // too short - need enough for header and crc
                pthread_mutex_lock(&mutex_upStats);
                upBadShort++;
                pthread_mutex_unlock(&mutex_upStats);
            } else if (recvlen != (buf[1] + framing_bytecount)) {
                // bad length
                pthread_mutex_lock(&mutex_upStats);
                upBadLength++;
                pthread_mutex_unlock(&mutex_upStats);
            } else {
                // sanity checked - might be a good mavlink message

                pthread_mutex_lock(&mutex_upStats);
                upMsgs++;
                upBytes += recvlen;
                pthread_mutex_unlock(&mutex_upStats);

                uint32_t message_id;
                uint8_t source_system;
                uint8_t source_component;
                uint8_t payload_offset;
                if (buf[0] == MAVLINK_STX_MAVLINK1) {
                    message_id = buf[5];
                    source_system = buf[3];
                    source_component = buf[4];
                    payload_offset = 6;
                } else {
                    message_id = (p_payload[7]) | (p_payload[8]<<8) | p_payload[9]<<16;
                    source_system = buf[5];
                    source_component = buf[6];
                    payload_offset = 10;
                }
#if 1 // debug

                if (message_id == MAVLINK_MSG_ID_SET_MODE) {
                    syslog(LOG_INFO, "SET_MODE: from %s:%d", inet_ntoa(remaddr.sin_addr),
                           ntohs(remaddr.sin_port));
                    // we don't have a mav_msg to use for unpacking
                    // custom_mode is the first four bytes, little endian
                    syslog(LOG_INFO, "SET_MODE: len=%u src_sys=%u src_comp=%u", unsigned(buf[1]),
                           unsigned(source_system), unsigned(source_component));
                    if (unsigned(buf[1]) == MAVLINK_MSG_ID_SET_MODE_LEN)
                        syslog(LOG_INFO,
                               "SET_MODE: custom_mode=%u.%u.%u.%u target_system=%u base_mode=%u",
                               unsigned(buf[payload_offset+3]), unsigned(buf[payload_offset+2]), unsigned(buf[payload_offset+1]),
                               unsigned(buf[payload_offset]), unsigned(buf[payload_offset+4]), unsigned(buf[payload_offset+5]));
                }

#endif // debug

                // Check the amount of data in the tx buffer.
                ioctl(serial_fd, TIOCOUTQ, &txBufUsage);

                // At 921k baud, the UART send buffer holds about 44 msec of
                // data. A burst of uplink can lead to messages being dropped.
                // Since the uplink thread only relays messages from the UDP
                // port to the serial port, the possible fixes include: (a)
                // don't read from UDP until we know there's room in serial;
                // (b) read and buffer messages in the thread until there is
                // room in serial; (c) wait here until there is room. (c) is
                // chosen because it is very simple, and is equivalent to (a)
                // but with less logic. The only advantage of (b) would be a
                // bit more flexibility in how messages are buffered; here, we
                // are just leaving them in the UDP socket buffer. A still-
                // smarter option would be to handle wifi uplink and local
                // uplink differently (we can't tell the difference right
                // now), or to even choose messages to drop in the case of
                // congestion.

                if ((4000 - txBufUsage) < recvlen) {
                    // Congestion; serial port tx buffer is filling up
                    syslog(LOG_INFO, "serial port tx full; waiting for room");

                    // Worst-case wait time is if we have a long message to
                    // send and are running at a low baud rate. For a long
                    // 263-byte message and a low baud rate of 57600, that's
                    // ~50 msec. A typical wait time should be ~50 bytes at
                    // 921k baud, or ~500 usec. Allow for Pixhawk busy and not
                    // pulling messages. Reaching this timeout is a fatal
                    // error and means something is broken; err on the side of
                    // no false detections yet recovering (restarting this
                    // process) 'quicky' in human terms.
                    const unsigned serial_timeout_us = 1000000; // 1 sec
                    uint64_t start_us = clock_gettime_us(CLOCK_MONOTONIC);
                    while (true) {
                        uint64_t poll_us = clock_gettime_us(CLOCK_MONOTONIC);
                        ioctl(serial_fd, TIOCOUTQ, &txBufUsage);
                        if ((4000 - txBufUsage) >= recvlen)
                            break;
                        unsigned wait_us = poll_us - start_us;
                        if (wait_us > serial_timeout_us) {
                            // Either imx6 output serial port is stuck, or
                            // Pixhawk is not reading from its end.
                            // Restarting the process may fix the former.
                            syslog(LOG_ERR, "serial port tx stuck; exiting");
                            exit(1);
                        } else {
                            // There's close to 4000 bytes queued in the port,
                            // or over 40 msec even at 921k baud. Let some of
                            // it go.
                            usleep(10000); // 10 msec
                        }
                    }
                    syslog(LOG_INFO, "serial port tx was full; now resuming");
                }

                // If we're rc-locked, don't send an arm command
                // Check by decoding mavlink COMMAND_LONG packets when the RC is locked.

                discard = false;

                if (rc_locked) {
                    if (message_id == MAVLINK_MSG_ID_COMMAND_LONG) {
                        for (i = 0; i < recvlen; ++i) {
                            if (mavlink_parse_char(MAVLINK_COMM_0, buf[i], &mav_msg, &mav_status)) {
                                mavlink_msg_command_long_decode(&mav_msg, &mav_cmd_long);
                                if (mav_cmd_long.command == MAV_CMD_COMPONENT_ARM_DISARM &&
                                    mav_cmd_long.param1 == 1) {
                                    syslog(LOG_ERR,
                                           "arm command received but RC is locked out; ignoring");
                                    discard = true;
                                }
                            }
                        }
                    }
                }

                if (!discard) {
                    if (write(serial_fd, buf, recvlen) != recvlen) {
                        int err = errno;
                        syslog(LOG_ERR, "serial port write error: %s", strerror(err));
                    } else {
                        pthread_mutex_lock(&mutex_upStats);
                        serialUpBytes += recvlen;
                        pthread_mutex_unlock(&mutex_upStats);
                    }
                }

                if (client != NULL) {
                    set_seen_sysid_compid_from_client(source_system, source_component, client);
                }
            } // sanity checked as possibly good mavlink message

            // Client checking is done outside the sanity-checked mavlink
            // message clause so we can send a byte to the port as a way of
            // registering to receive downstream messages. Debt incurred.
            if (client != NULL) {
                client->lastRecvTime_us = now_us;
            }

            if (next_client_timeout_check < now_us) {
                check_client_timeouts(now_us);
                next_client_timeout_check = now_us + client_timeout_check_interval;
            }

        } // if (recvlen > 0)

    } // while (true)

    pthread_exit(NULL);

} // upstream_task

void check_client_timeouts(uint64_t now_us)
{
    list< sockdata * >::iterator it, next;

    // Random GCS that connect to telem_forward -
    // e.g. dataflash_logger - might suddenly go away and come
    // back again.
    // Check if any client has timed out. This is done on any message or
    // socket timeout - if done only on socket timeout, it might never be
    // done.
    pthread_mutex_lock(&mutex_clients);
    for (it = clients.begin(); it != clients.end(); it = next) {
        next = it;
        next++;

        struct sockdata *client = *it;
        uint64_t delta_us = now_us - client->lastRecvTime_us;

        if (delta_us > CLIENT_TIMEOUT_US) {
            syslog(LOG_INFO, "client %s:%d timed out after %0.3fs of inactivity; removing",
                   inet_ntoa(client->sa.sin_addr), ntohs(client->sa.sin_port), delta_us / 1.0e6);
            purge_client_from_arp_table(client);
            clients.erase(it);
            delete client;
        }
    }
    pthread_mutex_unlock(&mutex_clients);
}

/**********************************************************************
Function: int start_upstream_thread()

Description: Starts the upstream thread.
 ***********************************************************************/
int start_upstream_thread(void)
{
    int ret = 0;
    struct sched_param param;

    // Start the upstream thread
    pthread_create(&upstream_ctx, NULL, upstream_task, NULL);

    pthread_setname_np(upstream_ctx, "telem_up");

    // upstream priority and schedule
    param.sched_priority = UPSTREAM_PRIORITY;
    if ((ret = pthread_setschedparam(upstream_ctx, SCHED_FIFO, &param)))
        syslog(LOG_ERR, "could not set upstream schedule priority: %d", ret);

    return ret;
}

/**********************************************************************
Function: bool handle_system_time(const mavlink_message_t& msg)

Description: Handle a mavlink SYSTEM_TIME message. This message
             contains the GPS time (some "GPS" messages do not). The
             GPS time is always logged, and if enabled, the system
             time is set.
***********************************************************************/
static bool handle_system_time(const mavlink_message_t &msg)
{
    mavlink_system_time_t system_time;

    mavlink_msg_system_time_decode(&msg, &system_time);

    // GPS time is good if it is nonzero
    if (system_time.time_unix_usec != 0) {
        struct tm utc;
        char utc_buf[80];
        struct timeval tv;

        tv.tv_sec = system_time.time_unix_usec / 1000000ULL;
        tv.tv_usec = system_time.time_unix_usec % 1000000ULL;

        gmtime_r(&tv.tv_sec, &utc);

        strftime(utc_buf, sizeof(utc_buf), "%F %T", &utc);

        syslog(LOG_INFO, "GPS time: %s.%06ld", utc_buf, tv.tv_usec);

        if (useGpsTime) {
            int status = settimeofday(&tv, NULL);
            if (status != 0)
                syslog(LOG_ERR, "setting clock from GPS");
            else
                syslog(LOG_INFO, "clock set from GPS");
        }
        return true;
    }

    return false;

} // handle_system_time

bool get_route_targets(uint8_t &target_system, uint8_t &target_component, mavlink_message_t &msg)
{
    switch (msg.msgid) {
    case MAVLINK_MSG_ID_REMOTE_LOG_DATA_BLOCK:
        target_system = mavlink_msg_remote_log_data_block_get_target_system(&msg);
        target_component = mavlink_msg_remote_log_data_block_get_target_component(&msg);
        break;
    case MAVLINK_MSG_ID_REMOTE_LOG_BLOCK_STATUS:
        target_system = mavlink_msg_remote_log_block_status_get_target_system(&msg);
        target_component = mavlink_msg_remote_log_block_status_get_target_component(&msg);
        break;
    default:
        return false;
    }

    return true;
}

bool should_send_message_to_client(sockdata &client, mavlink_message_t &msg)
{
    // return true;

    uint8_t target_system;
    uint8_t target_component;
    if (!get_route_targets(target_system, target_component, msg)) {
        // no targets in packet - must route
        return true;
    }

    if (target_system == 0) {
        // broadcast
        return true;
    }

    if (!seen_sysid(target_system)) {
        return false;
    }

    if (target_component == 0) {
        // broadcast to specific system
        return true;
    }

    if (!seen_sysid_compid(target_system, target_component)) {
        return false;
    }

    return clients_match(arp_table[target_system][target_component], &client);
}

/**********************************************************************
Function: void *downstream_task(void*)

Description: The downstream thread task. Waits for data on either the
             serial port or inject port and outputs it to all connected
             clients on the UDP port. The inject port is a way to
             inject telemetry into the down-bound stream.
***********************************************************************/
bool artoo_should_get_msg(const mavlink_message_t &msg)
{
    switch (msg.msgid) {
    case MAVLINK_MSG_ID_REMOTE_LOG_DATA_BLOCK:
    case MAVLINK_MSG_ID_REMOTE_LOG_BLOCK_STATUS:
        return false;
    default:
        return true;
    }
    return true;
}

void *downstream_task(void *)
{
    int readlen;
    char buf[BUFSIZE];
    list< sockdata * >::iterator it;
    mavlink_message_t msg;
    mavlink_status_t mavlinkStatus;
    int i;
    LinkPacket packet;
    uint32_t link_next_seq = 0;
    int messageLen;
    const int fdn_serial = 0; // entry in fds[] used for serial
    const int fdn_inject = 1; // entry in fds[] used for inject
    const int nfds = 2;       // entries in fds[]
    struct pollfd fds[nfds];
    int pollrc;
    int poll_errno_last = 0;
    bool poll_zero = false;
    int recv_errno_last = 0;
    bool recv_zero = false;
    uint8_t *p_packet_payload = packet.payload;  // Pointer to the current payload addr
    int payload_used = 0;                        // The amount of data currently in the payload
    uint8_t mav_msg_buf[MAVLINK_MAX_PACKET_LEN]; // Temporary place to store the mavlink message

    /* Downlink logging */
    static uint64_t dl_err_logged_us = 0;
    static unsigned dl_err_interval_us = 1000000;
    static unsigned dl_err_count = 0;

    memset(&fds, 0, sizeof(fds));

    fds[fdn_serial].fd = serial_fd;
    fds[fdn_serial].events = POLLIN;

    fds[fdn_inject].fd = inject_fd;
    fds[fdn_inject].events = POLLIN;

    uint64_t now_us = clock_gettime_us(CLOCK_MONOTONIC);
    uint64_t next_send_us = now_us + SEND_DT_US;

    while (true) {

        uint64_t pre_poll_us = clock_gettime_us(CLOCK_MONOTONIC);

        // Wait for available data.  The timeout is based on the amount
        // of time until the next transmit time, as we don't want to block
        // any longer than that in order to keep sending every SEND_DT_US.
        int timeout = (next_send_us - pre_poll_us) / 1000;
        pollrc = poll(fds, nfds, (timeout < 0 ? 0 : timeout));

        now_us = clock_gettime_us(CLOCK_MONOTONIC);

        uint32_t blocked_us = now_us - pre_poll_us;

        if (pollrc < 0) {
            // print error message only when errno changes to avoid log storms
            if (errno != poll_errno_last) {
                int err = errno;
                syslog(LOG_ERR, "poll: %s", strerror(err));
                poll_errno_last = err;
            }
        } else if (pollrc == 0) {
            // used for ppoll() timeout; should not get this from poll()
            if (!poll_zero) {
                syslog(LOG_ERR, "poll returned zero");
                poll_zero = true;
            }
        } else // (pollrc > 0)
        {

            if (fds[fdn_serial].revents & POLLIN) {
                // new serial data
                readlen = read(serial_fd, buf, BUFSIZE);
                if (readlen > 0) {
                    pthread_mutex_lock(&mutex_downStats);
                    serialDownBytes += readlen;
                    pthread_mutex_unlock(&mutex_downStats);

                    for (i = 0; i < readlen; ++i) {
                        // Only send full mavlink messages at a time
                        // mavlink_frame_char is buffering up the message,
                        // so we don't have to keep buf[] data after giving
                        // it to mavlink_parse_char
                        uint8_t frame_check =
                            mavlink_frame_char(MAVLINK_COMM_0, buf[i], &msg, &mavlinkStatus);
                        /*
                          if frame_check == MAVLINK_FRAMING_BAD_CRC
                          then we got a message frame but with a bad
                          CRC. That may indicate a new message not in
                          our XML. We want to forward those, but not
                          process locally
                         */
                        if (frame_check != MAVLINK_FRAMING_INCOMPLETE) {
                            if (frame_check == MAVLINK_FRAMING_OK) {
                                if (!gotGpsTime && msg.msgid == MAVLINK_MSG_ID_SYSTEM_TIME) {
                                    // Log GPS time, and optionally set system clock
                                    gotGpsTime = handle_system_time(msg);
                                }
                            }

                            // Check sequence if we've seen this (srcid,
                            // compid) before
                            pthread_mutex_lock(&mutex_streams);
                            list< stream_state >::iterator i;
                            bool found_stream = false;
                            // This is typically a list of one, maybe two
                            for (i = streams.begin(); i != streams.end(); i++) {
                                if (msg.sysid == i->sysid && msg.compid == i->compid) {
                                    if (msg.seq != ((i->seq + 1) & 0xff))
                                        i->seq_err++;
                                    i->seq = msg.seq;
                                    found_stream = true;
                                    break;
                                }
                            }
                            // Create stream state if necessary and message is
                            // known good.
                            if (!found_stream && frame_check == MAVLINK_FRAMING_OK) {
                                stream_state new_stream(msg.sysid, msg.compid, msg.seq);
                                streams.push_back(new_stream);
                            }
                            pthread_mutex_unlock(&mutex_streams);

                            messageLen = mavlink_msg_to_send_buffer(mav_msg_buf, &msg);

                            pthread_mutex_lock(&mutex_downStats);
                            downMsgs++;
                            downMsgsById[msg.msgid]++;
                            downBytes += messageLen;
                            pthread_mutex_unlock(&mutex_downStats);

                            // Start with the artoo
                            if (artoo_should_get_msg(msg)) {
                                /* If there isn't enough room in the LinkPacket to store this
                                 * message,
                                 * send the current LinkPacket along and make this message the first
                                 * in
                                 * the next LinkPacket. Worst case, this message will get there in
                                 * another
                                 * 100ms */
                                if (messageLen > (packet.MAX_PAYLOAD - payload_used)) {
                                    /* Force a send */
                                    syslog(LOG_ERR, "Message too large for aggregate buffer, "
                                                    "sending LinkPacket first");
                                    packet.tf_send_us = clock_gettime_us(CLOCK_MONOTONIC);
                                    packet.tc_recv_us = 0;
                                    packet.tc_send_us = 0;
                                    packet.stm_recv_us = 0;
                                    packet.seq = link_next_seq++;
                                    packet.data1 = payload_used;
                                    packet.data2 = blocked_us;
                                    packet.data3 = 0;
                                    if (sendto(sock_fd, &packet, LinkPacket::HDR_LEN + payload_used,
                                               0, (struct sockaddr *)&artooaddr,
                                               sizeof(artooaddr)) < 0) {
                                        // rate-limited logging (dl = downlink)
                                        dl_err_count++;
                                        // log it if this is the first error, or if
                                        // it has been long enough since logging an error
                                        if (dl_err_logged_us == 0 ||
                                            (now_us - dl_err_logged_us) >= dl_err_interval_us) {
                                            // log error
                                            syslog(LOG_ERR, "sendto(downlink): %s (%u errors)",
                                                   strerror(errno), dl_err_count);
                                            dl_err_logged_us = now_us;
                                            dl_err_count = 0;
                                        }
                                    }

                                    /* Reset the payload info */
                                    payload_used = 0;
                                    p_packet_payload = packet.payload;
                                }

                                /* Put the packet into our packet buffer */
                                memcpy(p_packet_payload, mav_msg_buf, messageLen);
                                p_packet_payload += messageLen;

                                /* If this is the first packet, set the timestamp */
                                if (!payload_used)
                                    packet.tf_recv_us = now_us;

                                payload_used += messageLen;
                            }
                            // Continue with any other connected clients
                            pthread_mutex_lock(&mutex_clients);
                            for (it = clients.begin(); it != clients.end(); ++it) {
                                if (!should_send_message_to_client(**it, msg)) {
                                    continue;
                                }

                                if (sendto(sock_fd, mav_msg_buf, messageLen, 0,
                                           (struct sockaddr *)&((*it)->sa),
                                           sizeof((*it)->sa)) < 0) {
                                    // rate-limited logging (ll = local link)
                                    static uint64_t ll_err_logged_us = 0;
                                    static unsigned ll_err_interval_us = 1000000;
                                    static unsigned ll_err_count = 0;
                                    ll_err_count++;
                                    // log it if this is the first error, or if
                                    // it has been long enough since logging an error
                                    if (ll_err_logged_us == 0 ||
                                        (now_us - ll_err_logged_us) >= ll_err_interval_us) {
                                        // log error
                                        syslog(LOG_ERR, "sendto(local link): %s (%u errors)",
                                               strerror(errno), ll_err_count);
                                        ll_err_logged_us = now_us;
                                        ll_err_count = 0;
                                    }
                                }
                            }
                            pthread_mutex_unlock(&mutex_clients);
                        }
                    } // for (i...)
                }     // if (readlen...)
            }         // if (fds[fdn_serial]...)

            if (fds[fdn_inject].revents & POLLIN) {

                // new inject data - should get one MAVLink message per recv
                readlen = recv(inject_fd, mav_msg_buf, MAVLINK_MAX_PACKET_LEN, 0);
                if (readlen < 0) {
                    // print error message only when errno changes to avoid
                    // log storms
                    if (errno != recv_errno_last) {
                        int err = errno;
                        syslog(LOG_ERR, "recv: %s", strerror(err));
                        recv_errno_last = err;
                    }
                } else if (readlen == 0) {
                    // this means the peer has performed an orderly shutdown
                    // which does not make sense for us
                    if (!recv_zero) {
                        syslog(LOG_ERR, "recv returned zero");
                        recv_zero = true;
                    }
                } else // readlen > 0
                {
                    /* Put the packet into our packet buffer */
                    if (readlen <= (packet.MAX_PAYLOAD - payload_used)) {
                        memcpy(p_packet_payload, mav_msg_buf, readlen);
                        p_packet_payload += readlen;

                        /* If this is the first packet, set the timestamp */
                        if (!payload_used)
                            packet.tf_recv_us = now_us;

                        payload_used += readlen;
                    } else {
                        /* Whoops, we dropped one here */
                        syslog(LOG_ERR, "Inject message too large for aggregate buffer, dropping");
                    }

                    pthread_mutex_lock(&mutex_downStats);
                    downBytes += readlen;
                    // downMsgsById[msg.msgid]++; // XXX could pluck out mavlink msg id
                    downMsgs++;
                    pthread_mutex_unlock(&mutex_downStats);

                    // continue with any other connected clients
                    pthread_mutex_lock(&mutex_clients);
                    for (it = clients.begin(); it != clients.end(); ++it) {
                        if (sendto(sock_fd, mav_msg_buf, readlen, 0,
                                   (struct sockaddr *)&((*it)->sa), sizeof((*it)->sa)) < 0) {
                            // XXX
                        }
                    }
                    pthread_mutex_unlock(&mutex_clients);

                } // if (readlen...)

            } // if (fds[fdn_serial]...)

        } // if (pollrc...)

        /* Determine if it is time to send data to Artoo.  Either its been enough
         * time or we don't have enough room to store the largest mavlink message (263B).
         * Also make sure we actually have something to send. Always send if locked,
         * since we might be locked because we are running with an old controller that
         * does not understand aggregation (and we don't care about link efficiency). */
        if (rc_locked || (now_us > next_send_us) ||
            (payload_used >= (packet.MAX_PAYLOAD - MAVLINK_MAX_PACKET_LEN))) {

            if (payload_used > 0) {
                /* packet.tf_recv_us will have already been set by the first packet */
                packet.tf_send_us = clock_gettime_us(CLOCK_MONOTONIC);
                packet.tc_recv_us = 0;
                packet.tc_send_us = 0;
                packet.stm_recv_us = 0;
                packet.seq = link_next_seq++;
                packet.data1 = payload_used;
                packet.data2 = blocked_us;
                packet.data3 = 0;
                if (sendto(sock_fd, &packet, LinkPacket::HDR_LEN + payload_used, 0,
                           (struct sockaddr *)&artooaddr, sizeof(artooaddr)) < 0) {
                    // rate-limited logging (dl = downlink)
                    dl_err_count++;
                    // log it if this is the first error, or if
                    // it has been long enough since logging an error
                    if (dl_err_logged_us == 0 ||
                        (now_us - dl_err_logged_us) >= dl_err_interval_us) {
                        // log error
                        syslog(LOG_ERR, "sendto(downlink): %s (%u errors)", strerror(errno),
                               dl_err_count);
                        dl_err_logged_us = now_us;
                        dl_err_count = 0;
                    }
                }

                /* Reset the payload info */
                payload_used = 0;
                p_packet_payload = packet.payload;
            }

            /* Set the next time we should send */
            next_send_us = now_us + SEND_DT_US;
        }

    } // while (true)

    pthread_exit(NULL);
}

/**********************************************************************
Function: int start_downstream_thread()

Description: Starts the downstream thread.
 ***********************************************************************/
int start_downstream_thread(void)
{
    int ret = 0;
    struct sched_param param;

    // Start the downstream thread
    pthread_create(&downstream_ctx, NULL, downstream_task, NULL);

    pthread_setname_np(downstream_ctx, "telem_down");

    // downstream priority and schedule
    param.sched_priority = DOWNSTREAM_PRIORITY;
    if ((ret = pthread_setschedparam(downstream_ctx, SCHED_FIFO, &param)))
        syslog(LOG_ERR, "could not set downstream schedule priority: %d", ret);

    return ret;
}

/**********************************************************************
Function: void *logging_task(void*)

Description: The logging task.  Dumps logging info to our log file
             periodically.
***********************************************************************/
void *logging_task(void *)
{
    uint64_t delta_us;
    uint64_t now_us, last_log_us;

    last_log_us = clock_gettime_us(CLOCK_MONOTONIC);

    while (1) {
        // Log the amount of downstream data
        now_us = clock_gettime_us(CLOCK_MONOTONIC);

        delta_us = now_us - last_log_us;

        if (delta_us > LOG_DT_US) {
            last_log_us = now_us;

            pthread_mutex_lock(&mutex_downStats);
            pthread_mutex_lock(&mutex_upStats);

            // utilization of serial link

            // bytes/sec used = serialBytes / (delta_us / 1e6)
            // bytes/sec capacity = serialBaud / 10
            // percent utilization = [serialBytes / (delta_us / 1e6)] / (serialBaud / 10) * 100%
            //                     = (serialBytes * 1e7) / (delta_us * serialBaud) * 100%

            double downPct = (serialDownBytes * 1e9) / ((double)(delta_us * serialBaud));
            double upPct = (serialUpBytes * 1e9) / ((double)(delta_us * serialBaud));

            syslog(LOG_INFO, "down: %d m/s, %d b/s, %d%%; up: %d m/s, %d b/s, %d%%",
                   int(downMsgs * 1e6 / delta_us), int(downBytes * 1e6 / delta_us), int(downPct),
                   int(upMsgs * 1e6 / delta_us), int(upBytes * 1e6 / delta_us), int(upPct));
            if (upBadShort != 0 || upBadMagic != 0 || upBadLength != 0) {
                syslog(LOG_INFO, "up err: %u, %u, %u", upBadShort, upBadMagic, upBadLength);
                upBadShort = 0;
                upBadMagic = 0;
                upBadLength = 0;
            }

            downMsgs = 0;
            downBytes = 0;
            upMsgs = 0;
            upBytes = 0;
            serialDownBytes = 0;
            serialUpBytes = 0;

            if (logControl & LOG_CONTROL_MSG_COUNTS_DOWN) {
                ostringstream dbg;
                dbg << "by id:";
                for (int id = ID_MIN; id < ID_MAX; id++) {
                    if (downMsgsById[id] > 0) {
                        // 77:108 means there were 108 messages with id 77
                        dbg << ' ' << id << ':' << downMsgsById[id];
                        downMsgsById[id] = 0;
                    }
                }
                syslog(LOG_INFO, "%s", dbg.str().c_str());
            }

            pthread_mutex_unlock(&mutex_upStats);
            pthread_mutex_unlock(&mutex_downStats);

            // sequence errors
            bool any_errs = false;
            list< stream_state >::iterator i;
            ostringstream dbg;
            dbg << "seq errs:";
            pthread_mutex_lock(&mutex_streams);
            for (i = streams.begin(); i != streams.end(); i++) {
                // ignore gimbal (sequence is bogus)
                if ((i->sysid != 1 || i->compid != 154) && i->seq_err > 0) {
                    // cast to int is so << doesn't print a char
                    dbg << " (" << int(i->sysid) << "," << int(i->compid) << "):" << i->seq_err;
                    i->seq_err = 0;
                    any_errs = true;
                }
            }
            pthread_mutex_unlock(&mutex_streams);
            if (any_errs) {
                syslog(LOG_INFO, "%s", dbg.str().c_str());
            }
        }

        // Put a big sleep here
        sleep(1); // 1s
    }
    pthread_exit(NULL);
}

/**********************************************************************
Function: int start_logging_thread()

Description: Starts the logging thread.
 ***********************************************************************/
int start_logging_thread(void)
{
    int ret = 0;
    struct sched_param param;

    // Start the logging thread
    pthread_create(&logging_ctx, NULL, logging_task, NULL);

    pthread_setname_np(logging_ctx, "telem_log");

    // logging priority and schedule
    param.sched_priority = LOG_PRIORITY;
    if ((ret = pthread_setschedparam(logging_ctx, SCHED_FIFO, &param)))
        syslog(LOG_ERR, "could not set logging schedule priority: %d", ret);

    return ret;
}

/**********************************************************************
Function: int main(void)

Description: The main function.  Initializes and runs the serial and
             UDP threads.
***********************************************************************/
int main(void)
{
    int destPort;
    string inject_name;

    openlog("tlm", LOG_NDELAY, LOG_LOCAL4);

    syslog(LOG_INFO, "Installing SIGQUIT signal handler");
    signal(SIGQUIT, sigquit_handler);

    serialDownBytes = 0;
    serialUpBytes = 0;

    syslog(LOG_INFO, "telem_forwarder starting: built " __DATE__ " " __TIME__);

    /* Parse the sololink.conf file for serial port, source IPs and ports */
    INIReader reader("/etc/sololink.conf");

    if (reader.ParseError() < 0) {
        syslog(LOG_CRIT, "can't parse /etc/sololink.conf");
        return -1;
    }

    /* Get the serial port to output DSM data on */
    serialPortName = reader.Get("solo", "telemDev", "/dev/ttymxc1");
    serialBaud = reader.GetInteger("solo", "telemBaud", 57600);
    serialFlow = reader.GetBoolean("solo", "telemFlow", true);
    inject_name = reader.Get("solo", "injectPortName", "/run/telem_downlink");

    /* Get the udp destination port for clients */
    destPort = reader.GetInteger("solo", "telemDestPort", 14550);

    /* Whether to set system time from GPS or not */
    useGpsTime = reader.GetBoolean("solo", "useGpsTime", true);

    /* Downstream telemetry TOS */
    int tos = reader.GetInteger("solo", "telemDownTos", 0x7f);

    /* Logging control (debug) */
    logControl = reader.GetInteger("solo", "telemLogControl", 0);

    syslog(LOG_INFO, "serial port: %s", serialPortName.c_str());
    syslog(LOG_INFO, "serial baudrate: %d", serialBaud);
    syslog(LOG_INFO, "serial hw flow: %s", serialFlow ? "true" : "false");
    syslog(LOG_INFO, "UDP dest port: %d", destPort);
    syslog(LOG_INFO, "use GPS time: %s", useGpsTime ? "true" : "false");
    syslog(LOG_INFO, "tos: 0x%02x", (uint8_t)tos);
    if (logControl != 0)
        syslog(LOG_INFO, "log control: 0x%08x", logControl);

    /* Set up the various ports */

    if (!UDP_setup(tos)) {
        syslog(LOG_CRIT, "unable to initialize the UDP receive");
        return -1;
    }

    if (!serial_setup(serialBaud)) {
        syslog(LOG_CRIT, "unable to initialize the serial send");
        return -1;
    }

    if (!inject_setup(inject_name.c_str())) {
        syslog(LOG_CRIT, "unable to initialize the inject port");
        return -1;
    }

    // Set up the mutexes
    pthread_mutex_init(&mutex_upStats, NULL);
    pthread_mutex_init(&mutex_downStats, NULL);
    pthread_mutex_init(&mutex_clients, NULL);
    pthread_mutex_init(&mutex_streams, NULL);

    // Setup the Artoo address and port
    memset((char *)&artooaddr, 0, sizeof(artooaddr));
    artooaddr.sin_family = AF_INET;
    inet_aton("10.1.1.1", &artooaddr.sin_addr);
    artooaddr.sin_port = htons(destPort);

    rc_locked = RcLock::locked();

    /* Start the upstream, downstream, and logging threads */
    start_downstream_thread();
    start_upstream_thread();
    start_logging_thread();

    // The main while() loop just becomes a thread monitor.  If any thread dies,
    // exit and let inittab restart us
    while (true) {
        rc_locked = RcLock::locked();

        if (pthread_kill(upstream_ctx, 0) != 0 || pthread_kill(downstream_ctx, 0) != 0 ||
            pthread_kill(logging_ctx, 0) != 0) {
            syslog(LOG_ERR, "a thread terminated; exiting");
            exit(0);
        }

        // Long sleep
        sleep(1);
    }

    return -1;
}
