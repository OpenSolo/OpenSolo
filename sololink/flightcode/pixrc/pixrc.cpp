#include <syslog.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netdb.h>
#include <time.h>
#include <termios.h>
#include <sys/mman.h>
#include <fstream>
#include "INIReader.h"
#include <sstream>
#include <vector>
#include <arpa/inet.h>
#include <cmath>
#include <iomanip>
#include <signal.h>
#include <sys/stat.h>
#include "util.h"
#include "RcLock.h"
#include "mutex.h"
#include "net_stats.h"
#include "RcCommander.h"
#include "rc_ipc.h"
#include "file_util.h"

using namespace std;

/***********************************************************************
Timeouts

NOTE on times:
Timeout detection is all done using CLOCK_MONOTONIC, while packet
timestamps originate (on the controller) from CLOCK_REALTIME. When the
system time is set (normally via GPS some time after startup), the
packet timestamps will generally jump in time, but timeout detection
should not be affected.
***********************************************************************/
#define LOG_DT_US 10000000   // 10s
#define RC_TIMEOUT_US 400000 // 400ms
#define SM_TIMEOUT_US 400000 // 400ms

// Used as the socket timeout on the RC uplink socket. This determines the
// resolution with which we will detect timeouts; it does not affect packet
// latency. It could be probably be longer.
// NOTE: The socket timeout appears to work such that the return from
// recvfrom happens on the next kernel tick after the requested timeout.
#define UDP_PERIOD_US 50000 // 50 msec

// Thread is stuck if it does not run for this long. This won't trigger if
// we have a long gap between packets since the recvfrom timeout should let
// the thread run.
#define UDP_STUCK_US 1000000 // 1 sec

// Time the udp thread was last activated. The thread should run every
// UDP_PERIOD_US (allowing for scheduling slop).
// This is shared with the main thread. Writes from this thread and reads
// from the main thread must be atomic.
static volatile uint64_t udp_run_us = 0;

static volatile uint64_t udp_run_interval_max_us = 0;

// Sleep delay in serial thread. This is approximately how often the
// serial thread will wake up and send whatever is in the packet
// shared memory to the Pixhawk.
#define SER_PERIOD_US 20000 // 20 msec

// Thread is stuck if it does not run for this long
#define SER_STUCK_US 1000000 // 1 sec

// Time the serial thread was last activated. The thread should run every
// SER_PERIOD_US (allowing for scheduling slop).
// This is shared with the main thread. Writes from this thread and reads
// from the main thread must be atomic.
static volatile uint64_t ser_run_us = 0;

// This should be mutex-protected, but we are trying to avoid blocking.
// The worst that can happen, which is astronomically unlikely, is a
// bogus interval might be printed.
static volatile uint64_t ser_run_interval_max_us = 0;

/***********************************************************************
RC timeout max.  This is pulled from sololink.conf or defaults to
RC_TIMEOUT_US
***********************************************************************/
static uint64_t rc_timeout_max_us;

// Shotmanager timeout - if the shared mem packet is not updated in
// this long, trigger failsafe.
static uint64_t sm_timeout_max_us;

/***********************************************************************
Serial macros
***********************************************************************/
static string serialPortName;

/***********************************************************************
Thread IDs
***********************************************************************/
static pthread_t serial_ctx;
static pthread_t UDP_ctx;

/***********************************************************************
Thread priorities - these are used with SCHED_FIFO. A higher number is a
higher priority. When priorities are viewed on the target (in /proc, or
using lsproc.py), the number seen there will be (1 - number_here), so
e.g. if PRIORITY is 50, it will show up as priority -51.
***********************************************************************/
#define UDP_PRIORITY 59
#define SERIAL_PRIORITY 58

/***********************************************************************
File descriptors
***********************************************************************/
static int sock_fd;
static int serial_fd;

/***********************************************************************
A vector of IPs from whom the artoo will accept RC data
***********************************************************************/
static vector< string > sourceIPs;

/***********************************************************************
The port which we accept RC data from
***********************************************************************/
static int sourcePort;

/***********************************************************************
 Commander processor
***********************************************************************/
static RcCommander *command = NULL;

/***********************************************************************
 rc lockout
***********************************************************************/
static bool rc_locked = false;

/***********************************************************************
Function: void lock_thread_mem(uint32_t memsize)

Description: Locks memory in the thread so that stack faults don't cause
             timing jitter.
***********************************************************************/
static void lock_thread_mem(uint32_t memsize)
{
    uint8_t stackmem[memsize];

    mlockall(MCL_CURRENT | MCL_FUTURE);

    memset(stackmem, 0, sizeof(stackmem));
}

/***********************************************************************
Task debug options
***********************************************************************/

//#define INCLUDE_BUG_SIM

#ifdef INCLUDE_BUG_SIM

#pragma message("BUILDING WITH INCLUDE_BUG_SIM")

// Detect bug simulation trigger.
// To simulate a bug, log in and (e.g.) "touch /tmp/pixrc_udp_bug"
static bool test_bug_trigger(const char *trigger_file)
{
    if (file_exists(trigger_file)) {
        unlink(trigger_file);
        return true;
    } else {
        return false;
    }
}

// Simulate crash on trigger
static void test_bug_exit(const char *trigger_file)
{
    if (test_bug_trigger(trigger_file)) {
        syslog(LOG_INFO, "udp: injecting crash");
        pthread_exit(NULL);
    }
}

// Simulate hang on trigger
static void test_bug_hang(const char *trigger_file)
{
    if (test_bug_trigger(trigger_file)) {
        syslog(LOG_INFO, "udp: injecting hang");
        while (1)
            sleep(1);
    }
}

#else // INCLUDE_BUG_SIM

#define test_bug_exit(A)
#define test_bug_hang(A)

#endif // INCLUDE_BUG_SIM

/***********************************************************************
Function: int UDP_setup(void)

Description: Sets up the UDP receive port.  Returns 0 in the event of
             an error, 1 otherwise.
***********************************************************************/
static int UDP_setup(void)
{
    struct sockaddr_in myaddr; /* our address */
    struct timeval timeout;

    /* create a UDP socket */
    if ((sock_fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        syslog(LOG_ERR, "udp: can't create socket");
        return 0;
    }

    /* Socket timeout */
    timeout.tv_sec = UDP_PERIOD_US / 1000000;
    timeout.tv_usec = UDP_PERIOD_US % 1000000;
    if (setsockopt(sock_fd, SOL_SOCKET, SO_RCVTIMEO, (char *)&timeout, sizeof(timeout)) != 0) {
        syslog(LOG_ERR, "udp: setsockopt: %s", strerror(errno));
        return 0;
    }

    /* Bind the socket to any IP, but we'll check the source later */
    memset((char *)&myaddr, 0, sizeof(myaddr));
    myaddr.sin_family = AF_INET;
    myaddr.sin_addr.s_addr = htonl(INADDR_ANY);
    myaddr.sin_port = htons(sourcePort);

    if (bind(sock_fd, (struct sockaddr *)&myaddr, sizeof(myaddr)) < 0) {
        syslog(LOG_ERR, "udp: bind: %s", strerror(errno));
        return 0;
    }

    syslog(LOG_INFO, "udp: listening on port %d", sourcePort);
    return 1;
}

/***********************************************************************
Function: void *UDP_task(void*)

Description: The main UDP thread task.  This runs every 20ms and checks
             for the right amount of RC channel data on the UDP port.
             It issues a timeout (setting throttle low and all other
             stick values to mid) if no new data is received.  Incoming
             data is also timestamped and recorded for logging.
***********************************************************************/
static void *UDP_task(void *)
{
    void *rc_ipc_id;
    unsigned put_err = 0;
    uint64_t put_err_time_us = 0;
    unsigned recv_err = 0;
    uint64_t recv_err_time_us = 0;
    int recvlen; /* # bytes received */
    struct rc_pkt pkt;
    uint16_t lastSequence = 0;
    uint64_t last_us, now_us;
    uint64_t last_run_us = 0;
    bool timeout = false; /* indicates an RC failsafe */
    struct sockaddr_in srcAddr;
    socklen_t slen;
    vector< string >::iterator it;
    bool sourceOK;
    int interval_us;
    uint64_t last_pkt_timestamp = 0;
    struct stats {
        long int max;
        long int avg;
        long int avg_n;
        long int unknown; // Packet from an unknown sender
        long int outOfOrder;
        long int dropped;
    } packetStats;
    unsigned udp_rx_queue_max = 0; // max udp receive queue
    uint64_t log_time_us = 0;

    test_bug_exit("/tmp/pixrc_udp_bug"); // simulate crash on startup

    lock_thread_mem(32768);

    // Attach to shared packet memory
    rc_ipc_id = rc_ipc_attach(1);
    if (rc_ipc_id == NULL) {
        syslog(LOG_ERR, "udp: can't attach to rc packet shared memory");
        pthread_exit(NULL);
    }

    memset(&pkt, 0, sizeof(pkt));

    memset(&packetStats, 0, sizeof(packetStats));

    last_us = clock_gettime_us(CLOCK_MONOTONIC);

    log_time_us = last_us + LOG_DT_US;

    bool is_attached_last = true;

    while (true) {
        test_bug_hang("/tmp/pixrc_udp_bug"); // simulate hang

        // If there are packets waiting at this point, then they are being delayed
        udp_info_t udp_info;
        if (udp_info_get(sourcePort, &udp_info) != 0) {
            // log this error once
            static bool logged = false;
            if (!logged) {
                logged = true;
                syslog(LOG_ERR, "udp: can't get udp stats");
            }
        } else {
            if (udp_rx_queue_max < udp_info.rx_queue)
                udp_rx_queue_max = udp_info.rx_queue;
        }

        // Attempt to receive data
        slen = sizeof(srcAddr);
        recvlen = recvfrom(sock_fd, &pkt, sizeof(pkt), 0, (sockaddr *)&srcAddr, &slen);

        // Time packet received or timeout detected
        now_us = clock_gettime_us(CLOCK_MONOTONIC);
        if (last_run_us != 0 && udp_run_interval_max_us < (now_us - last_run_us))
            udp_run_interval_max_us = now_us - last_run_us;
        last_run_us = now_us;
        __atomic_store_n(&udp_run_us, now_us, __ATOMIC_RELAXED);

        if (recvlen == sizeof(pkt)) {
            // check the source address to make sure its in our list of source IPs.
            sourceOK = false;
            for (it = sourceIPs.begin(); it != sourceIPs.end(); ++it) {
                // strcmp to avoid creating string object for srcAddr.sin_addr
                if (strcmp(it->c_str(), inet_ntoa(srcAddr.sin_addr)) == 0) {
                    sourceOK = true;
                    break;
                }
            }

            // Add it to the stats if its a bad IP
            if (!sourceOK) {
                packetStats.unknown++;
            } else {
                // Store some packet statistics
                interval_us = now_us - last_us;
                packetStats.avg =
                    (interval_us + (packetStats.avg_n * packetStats.avg)) / (packetStats.avg_n + 1);
                ++packetStats.avg_n;
                packetStats.max = (interval_us > packetStats.max ? interval_us : packetStats.max);

                // if (interval_us > 100000)
                //    syslog(LOG_INFO, "udp: packet interval %d usec", interval_us);

                last_us = now_us;

                // Check our failsafe status
                if (timeout) {
                    // Since we got the right amount of data, we assume its OK
                    syslog(LOG_INFO, "udp: failsafe end after %d ms", interval_us / 1000);
                    timeout = false;
                }

                // See if we dropped one. This doesnt mean we shouldn't
                // use the data, because its probably the latest
                if (pkt.sequence - lastSequence > 1) // Ignoring the out-of-order
                {
                    packetStats.dropped++;
                }
                lastSequence = pkt.sequence;

                // Check to see if the data is in the correct order. If it
                // appears to be out of order, just log it in the stats,
                // but still use it. Out of order should be extremely
                // unlikely, and reliably discarding packets that appear
                // old - and correctly resuming when they are not - seems
                // more complicated (prone to error) than it is worth.
                if (pkt.timestamp < last_pkt_timestamp) {
                    packetStats.outOfOrder++;
                }

                // Only write to shared memory if the uplink has not been
                // detached by some external client (who should be taking
                // the packets received via send_clients, fiddling with
                // them, then writing them to shared memory itself).
                if (command->is_attached()) {
                    // Write it to shared memory for serial thread
                    if (rc_ipc_put(rc_ipc_id, &pkt, 1) != 0) {
                        put_err++;
                        if (now_us - put_err_time_us > 10000000) {
                            syslog(LOG_ERR,
                                   "udp: can't write to rc packet shared memory (count=%d)",
                                   put_err);
                            put_err_time_us = now_us;
                        }
                    }
                    if (!is_attached_last) {
                        // just transitioned to attached
                        syslog(LOG_INFO, "udp: attached");
                        is_attached_last = true;
                    }
                } else {
                    // not attached, don't send it to shared memory
                    if (is_attached_last) {
                        // just transitioned to not attached
                        syslog(LOG_INFO, "udp: detached");
                        is_attached_last = false;
                    }
                }

                // Send it to other solo-resident clients
                command->send_clients(&pkt, sizeof(pkt));

                last_pkt_timestamp = pkt.timestamp;
            }
        } else {
            // timeout is the only non-pktlen return we expect
            // (recvlen == 1 && errno == EAGAIN)
            // if anything else, log it
            int err = errno;
            if (recvlen != -1 || err != EAGAIN) {
                // mystery error
                recv_err++;
                // Log once per second max. Note if there is more than one
                // kind of error happening (multiple combos of recvlen, err),
                // not all will necessarily be logged.
                if (now_us - recv_err_time_us > 1000000) {
                    syslog(LOG_ERR, "udp: recv returned %d; errno=%d; recv_err=%d", recvlen, err,
                           recv_err);
                    recv_err_time_us = now_us;
                    recv_err = 0;
                }
            }
        }

        if (!timeout) {
            uint64_t age_us;

            // last_us gets updated when we have a good set of data

            age_us = now_us - last_us;
            if (age_us > rc_timeout_max_us) {
                pkt.channel[0] = 900; // Throttle failsafe value
                // Center the stick
                pkt.channel[1] = 1500;
                pkt.channel[2] = 1500;
                pkt.channel[3] = 1500;
                // Leave all other channels at their current state

                if (command->is_attached()) {
                    // Write it to shared memory for serial thread
                    if (rc_ipc_put(rc_ipc_id, &pkt, 1) != 0) {
                        put_err++;
                        if (now_us - put_err_time_us > 10000000) {
                            syslog(LOG_ERR,
                                   "udp: can't write to rc packet shared memory (error %d)",
                                   put_err);
                            put_err_time_us = now_us;
                        }
                    }
                }

                // Send it to other solo-resident clients
                command->send_clients(&pkt, sizeof(pkt));

                timeout = true;

                syslog(LOG_INFO, "udp: failsafe start after %llu ms of inactivity", age_us / 1000);
            }
        }

        // log time?
        if (now_us >= log_time_us) {
            syslog(LOG_INFO, "a:%ld,m:%ld,n:%ld,u:%ld,d:%ld,o:%ld,q:%u,udp=%llu,ser=%llu",
                   (packetStats.avg + 500) / 1000, // a:
                   (packetStats.max + 500) / 1000, // m:
                   packetStats.avg_n,              // n:
                   packetStats.unknown,            // u:
                   packetStats.dropped,            // d:
                   packetStats.outOfOrder,         // o:
                   udp_rx_queue_max,               // q:
                   udp_run_interval_max_us,        // udp=
                   ser_run_interval_max_us);       // ser=

            memset(&packetStats, 0, sizeof(packetStats));
            udp_rx_queue_max = 0;
            udp_run_interval_max_us = 0;
            ser_run_interval_max_us = 0;

            log_time_us += LOG_DT_US;
        }

    } // while (true)

    pthread_exit(NULL);

} // UDP_task

/**********************************************************************
Function: int start_UDP_thread()

Description: Starts the UDP thread.
***********************************************************************/
static int start_UDP_thread(void)
{
    int ret = 0;

    // Start the UDP thread
    pthread_create(&UDP_ctx, NULL, UDP_task, NULL);

    pthread_setname_np(UDP_ctx, "pixrc_udp");

#ifdef UDP_PRIORITY
    // UDP priority and schedule
    struct sched_param param;
    memset(&param, 0, sizeof(param));
    param.sched_priority = UDP_PRIORITY;
    if ((ret = pthread_setschedparam(UDP_ctx, SCHED_FIFO, &param))) {
        syslog(LOG_ERR, "udp: pthread_setschedparam returned %d", ret);
    }
#endif // UDP_PRIORITY

    return ret;
}

/*
Convert PWM to DSM. The objective is to convert PWM to a DSM value such that
the inverse conversion done in the Pixhawk results in a different PWM range;
i.e. we are remapping the PWM and converting to DSM at the same time.

The inverse conversion done on Pixhawk is as follows:
  dsm 0..2047 maps to pwm 900..2100

src/modules/px4iofirmware/dsm.c, line ~390:
  pwm = ((((int)dsm - 1024) * 1000) / 1700) + 1500;

We want to control that output PWM range as calculated on Pixhawk:

PWM_in ---> DSM ------> PWM_out
       done     done on
       here     Pixhawk

To do that, we specify a PWM_in range and a PWM_out range, and calculate DSM
values accordingly.

The approach is to use the PWM_out range to precalculate a DSM range
(inverting the fixed Pixhawk calculation). Each conversion is then just a
linear mapping from the PWM_in range to the DSM range.

Pixhawk conversion from DSM to PWM:
  pwm = ((((int)dsm - 1024) * 1000) / 1700) + 1500;

Inverse of that:
  dsm = (((int)pwm - 1500) * 1700) / 1000 + 1024;
  dsm = (1700 * pwm - 1526000) / 1000

Using the desired PWM_out range on Pixhawk, calculate DSM_min and DSM_max.

The the conversion from PWM_in to DSM is:

dsmRange = dsmMax - dsmMin
pwmInRange = pwmInMax - pwmInMin

dsm = ((pwmIn - pwmInMin) / pwmInRange) * dsmRange + dsmMin
    = ((pwmIn - pwmInMin) * dsmRange + dsmMin * pwmInRange) / pwmInRange

Adding rounding for the integer math:

dsm = ((pwmIn - pwmInMin) * dsmRange + dsmMin * pwmInRange + pwmInRange/2) / pwmInRange
*/

// This class converts from PWM to DSM values. The "complication" is that we
// want to scale the conversion such that an input PWM range maps to a
// different output PWM range when the DSM->PWM conversion is done on Pixhawk.
//
// There will normally be two of these: one to handle the throttle channel
// (where we want a very specific PWM output range on Pixhawk) and one for all
// other channels (where it will be 1:1).
//
// This does _not_ handle ensuring that a throttle failsafe PWM value of 900
// maps to a DSM value of zero; in fact it generally will not, and whether it
// does or not depends on the PWM parameters given to the constructor. It is
// expected that whoever calls the 'encode' method will handle the special
// case of throttle failsafe.
class PwmToDsm
{
public:
    // constructor (precalculate some constants)
    PwmToDsm(int pwmInMin, int pwmInMax, int pwmOutMin, int pwmOutMax)
        : _pwmInMin(pwmInMin), _pwmInMax(pwmInMax), _pwmOutMin(pwmOutMin), _pwmOutMax(pwmOutMax)
    {
        _pwmInRange = _pwmInMax - _pwmInMin;

        // inverse of what Pixhawk does to convert DSM to PWM (with rounding)
        _dsmMin = ((_pwmOutMin * 1700 - 1526000) + 500) / 1000;
        _dsmMax = ((_pwmOutMax * 1700 - 1526000) + 500) / 1000;

        _dsmRange = _dsmMax - _dsmMin;

        _k = _dsmMin * _pwmInRange + _pwmInRange / 2;
    }

    // convert pwm value to dsm
    uint16_t encode(int channel, int pwm)
    {
        int dsm = ((pwm - _pwmInMin) * _dsmRange + _k) / _pwmInRange;

        // range check
        if (dsm < 0)
            dsm = 0;
        if (dsm > 2047)
            dsm = 2047;

        // stuff channel
        dsm |= (channel << 11);

        return dsm;
    }

    // decode dsm to pwm
    // This is only here for diagnostic purposes;
    // this is intended to be what the Pixhawk will do
    int decode(uint16_t dsm)
    {
        dsm &= 0x7ff;
        return ((((int)dsm - 1024) * 1000) / 1700) + 1500;
    }

private:
    // specified values
    int _pwmInMin;
    int _pwmInMax;
    int _pwmOutMin;
    int _pwmOutMax;

    // precalculated values
    int _pwmInRange; // pwmInMax - pwmInMin
    int _dsmMin;     // calculated from pwmOutMin
    int _dsmMax;     // calculated from pwmOutMax
    int _dsmRange;   // dsmMax - dsmMin
    int _k;          // (dsmMin * pwmInRange) + (pwmInRange / 2)

}; // class PwmToDsm

static PwmToDsm *pwmToDsmThrottle = NULL;
static PwmToDsm *pwmToDsmOther = NULL;

#if 0
static void pwmToDsmDiag(PwmToDsm *p2d)
{
    static int pwm_in[] = { 900, 1000, 1100, 1500, 1900, 2000 };
    int pwm_in_max = sizeof(pwm_in) / sizeof(pwm_in[0]);

    for (int i = 0; i < pwm_in_max; i++)
    {
        uint16_t dsm = p2d->encode(0, pwm_in[i]);
        int pwm_out = p2d->decode(dsm);
        syslog(LOG_INFO, "main: %4d -> 0x%04x -> %d", pwm_in[i], dsm, pwm_out);
    }
}
#endif

/**********************************************************************
Function: int encode_DSM()

Description: Encodes channel values (*channels) into a dsm string for
             transmission over the DSM serial port.  Returns the length
             of the string in bytes
***********************************************************************/
static int encode_DSM(char dsmstr[], uint16_t channels[], int num_channels)
{
    int i;
    uint16_t dsm;
    uint16_t chNum = 0;
    char *str = dsmstr;

    // Encode 16 bytes at a time, with a magic at the start of each
    // Empty channels get filled with 0xFF
    while (num_channels > 0) {
        // The first bytes are identification bytes, we use 0x00AB
        *str++ = 0x00;
        *str++ = 0xAB;

        // Put 7 channels in the remaining 8 bytes
        for (i = 0; i < 7; ++i) {
            if (num_channels > 0) {
                if (chNum == 0) {
                    // Handle the special case of throttle failsafe;
                    // PWM=900 must map to DSM=0
                    if (channels[chNum] == 900)
                        dsm = 0;
                    else
                        dsm = pwmToDsmThrottle->encode(chNum, channels[chNum]);
                } else {
                    dsm = pwmToDsmOther->encode(chNum, channels[chNum]);
                }
                *str++ = dsm >> 8;
                *str++ = dsm;
                ++chNum;
            }
            // Empty channels get filled with 0xFF
            else {
                *str++ = 0xFF;
                *str++ = 0xFF;
            }

            --num_channels;
        }
    }

    return (int)(str - dsmstr);
}

/***********************************************************************
Function: int serial_setup(void)

Description: The serial port initialization function.  This function
             initializes the serial port over which DSM data is sent to
             the pixhawk.  A return of 0 indicates an error.
***********************************************************************/
static int serial_setup(void)
{
    struct termios options;

    serial_fd = open(serialPortName.c_str(), O_RDWR | O_NOCTTY | O_NDELAY);

    if (serial_fd < 0) {
        syslog(LOG_ERR, "serial: can't open %s", serialPortName.c_str());
        return 0;
    }

    // Configure port for 8N1 transmission
    tcgetattr(serial_fd, &options); // Gets the current options for the port
    cfsetospeed(&options, B115200); // Sets the Output Baud Rate

    options.c_iflag &= ~(IGNBRK | BRKINT | ICRNL | INLCR | PARMRK | INPCK | ISTRIP | IXON);
    options.c_oflag &= ~(OCRNL | ONLCR | ONLRET | ONOCR | OFILL | OPOST);
    options.c_lflag &= ~(ECHO | ECHONL | ICANON | IEXTEN | ISIG);
    options.c_cflag &= ~(CSIZE | PARENB);
    options.c_cflag |= CS8;

    tcsetattr(serial_fd, TCSANOW, &options); // Set the new options for the port "NOW"
    return 1;
}

/**********************************************************************
Function: void *serial_task(void*)

Description: The main serial thread task.  This function outputs the
             latest RC channel data over the DSM serial port, after
             converting the RC channel data to DSM format.

Failsafe detection

This thread checks to see if the packet in shared memory is changing.
If it does not change within the failsafe timeout, start sending a
failsafe packet until the packet in shared memory starts changing
again.

Any change in the packet prevents failsafe. Normally the timestamp and
sequence change, but even if those don't change but some channel data
is changing, we don't failsafe (that behavior can be debated).

Failsafe timeouts are based on the time the packet was fetched from
shared memory. The timestamp in the packet is not used for failsafe
detection.

Startup - nothing is sent to the Pixhawk until we see the packet in
shared memory change at least once. This is to avoid a startup
condition where this thread runs first (for whatever reason), sees an
unchanging packet in shared memory, and failsafes when we are really
just trying to start everything up.

***********************************************************************/
static void *serial_task(void *)
{
    bool started = false; // set true when we see a change in shm
    char dsmStr[32];
    uint64_t now_us;
    uint64_t last_run_us = 0;
    int num_bytes;
    void *rc_ipc_id;
    struct rc_pkt pkt = {0};
    struct rc_pkt last_pkt = {0};
    unsigned get_err = 0;
    uint64_t get_err_time_us = 0;
    uint64_t last_good_us = 0;
    bool failsafing = false;
#undef DUMP_DSM
#ifdef DUMP_DSM
    unsigned decimate = 0;
#endif

    test_bug_exit("/tmp/pixrc_ser_bug"); // simulate crash on startup

    lock_thread_mem(32768);

    // Attach to shared packet memory
    rc_ipc_id = rc_ipc_attach(1);
    if (rc_ipc_id == NULL) {
        syslog(LOG_ERR, "serial: can't attach to rc packet shared memory");
        pthread_exit(NULL);
    }

    while (true) {
        test_bug_hang("/tmp/pixrc_ser_bug"); // simulate hang

        usleep(SER_PERIOD_US);

        // Get packet from shared memory. This normally does not block, but
        // can if someone else is holding the shared memory semaphore.
        int get_status = rc_ipc_get(rc_ipc_id, &pkt, 1);

        now_us = clock_gettime_us(CLOCK_MONOTONIC);
        if (last_run_us != 0 && ser_run_interval_max_us < (now_us - last_run_us))
            ser_run_interval_max_us = now_us - last_run_us;
        last_run_us = now_us;
        __atomic_store_n(&ser_run_us, now_us, __ATOMIC_RELAXED);

        if (get_status != 0) {
            // Error getting packet from shared memory.
            // Failure to get one is probably due to corruption somewhere.
            get_err++;
            if (now_us - get_err_time_us > 10000000) {
                syslog(LOG_ERR, "serial: can't read from rc packet shared memory (count=%d)",
                       get_err);
                get_err_time_us = now_us;
            }
            // Use the last good packet retrieved. This will be seen as an
            // unchanging packet, so if it continues it will cause failsafe.
            pkt = last_pkt;
        }

        // At this point, pkt is either the packet as retrieved from shared
        // memory, or is a copy of the last packet retrieved if we didn't get
        // one.

        if (memcmp(&pkt, &last_pkt, sizeof(pkt)) == 0) {
            // packet has not changed; check for failsafe timeout
            // (we also get here if we could not get one from shared mem)
            if ((now_us - last_good_us) > sm_timeout_max_us) {
                // packet has not changed for failsafe timeout
                pkt.channel[0] = 900; // throttle failsafe value
                // center the sticks
                pkt.channel[1] = 1500;
                pkt.channel[2] = 1500;
                pkt.channel[3] = 1500;
                // other channels (e.g. gimbal) not touched

                // Note that this is fairly likely to happen the first time
                // through the loop if nothing is writing to shared memory
                // yet, since the last_good_us is initted to zero, so it will
                // look like a timeout. The 'started' flag will be false, so
                // this bogus initial failsafe packet will not get sent to
                // the Pixhawk.
            }
        } else {
            // packet changed; we got one from shared memory and it is different
            // from the previous one
            last_good_us = now_us; // used to detect failsafe timeout
            last_pkt = pkt;        // used to detect changing packet
            if (!started) {
                syslog(LOG_INFO, "serial: started");
            }
            started = true;
        }

        // At this point, either the packet changed in shared memory and we're
        // using it, or it did not change and (a) it is not too old so we are
        // still using it or (b) it has been replaced by the failsafe packet.

        if (started) {

            memset(dsmStr, 0, sizeof(dsmStr));
            num_bytes = encode_DSM(dsmStr, &pkt.channel[0], 8);

            // Check for the rc lockout
            if (rc_locked)
                continue;

            if (write(serial_fd, dsmStr, num_bytes) != num_bytes) {
                syslog(LOG_ERR, "serial: port write error");
            }

            // log failsafe start/stop at the latest possible point (here)
            if (failsafing && (dsmStr[2] != 0 || dsmStr[3] != 0)) {
                // ending failsafe
                syslog(LOG_INFO, "serial: failsafe end");
                failsafing = false;
            } else if (!failsafing && (dsmStr[2] == 0 && dsmStr[3] == 0)) {
                // starting failsafe
                syslog(LOG_INFO, "serial: failsafe start");
                failsafing = true;
            }

#ifdef DUMP_DSM
            const unsigned nth = 10; // dump every Nth packet
            if (++decimate >= nth) {
                for (int i = 0; i < 32; i += 2) {
                    uint16_t c;
                    c = (unsigned(dsmStr[i]) << 8) | unsigned(dsmStr[i + 1]);
                    c &= 0x7ff;
                    cout << setw(5) << c;
                }
                cout << endl;
                decimate = 0;
            }
#endif

        } // if (started)

    } // while

    pthread_exit(NULL);
}

/**********************************************************************
Function: void start_serial_thread

Description: Starts the serial thread
***********************************************************************/
static int start_serial_thread(void)
{
    int ret = 0;

    pthread_create(&serial_ctx, NULL, serial_task, NULL);

    pthread_setname_np(serial_ctx, "pixrc_ser");

#ifdef SERIAL_PRIORITY
    // Set the priority and scheduler
    struct sched_param param;
    memset(&param, 0, sizeof(param));
    param.sched_priority = SERIAL_PRIORITY;
    if ((ret = pthread_setschedparam(serial_ctx, SCHED_FIFO, &param))) {
        syslog(LOG_ERR, "serial: pthread_setschedparam returned %d", ret);
    }
#endif // SERIAL_PRIORITY

    return ret;
}

/**********************************************************************
Function: bool thread_ok

Description: Returns true if thread appears to be running, false otherwise
***********************************************************************/
static bool thread_ok(const char *name, volatile uint64_t *thread_us, uint64_t max_us)
{

    // Ensure now_us is set before reading thread_us. If thread_us were read
    // first, a long preemption of this (low priority) thread could cause a
    // mistaken timeout event. The __ATOMIC_SEQ_CST in the thread_us read is
    // part of this enforcement (prevents code reordering).

    uint64_t now_us = clock_gettime_us(CLOCK_MONOTONIC);

    // note thread could run here, making thread_us > now_us

    // get the last time the thread ran
    uint64_t last_us = __atomic_load_n(thread_us, __ATOMIC_SEQ_CST);

    if (last_us > now_us)
        // thread ran between reading now_us and loading last_us
        return true;

    if ((now_us - last_us) <= max_us)
        // thread has run recently enough to be ok
        return true;

    // too long since thread ran

    // this should be exceptional (bug indicator)
    syslog(LOG_ERR, "%s: thread not running", name);
    syslog(LOG_ERR, "%s: now=%llu, ran@%llu, delta=%llu", name, now_us, last_us, now_us - last_us);

    return false;

} // thread_ok

/**********************************************************************
Function: bool thread_started

Description: Returns true if thread appears to be running, false
             otherwise.

This waits up to a timeout to let the thread get started.

A thread is deemed "running" if its last activation time is nonzero.
This depends on the activation time being statically initialized to
zero, but means we don't have to wait for an entire thread activation
period to know it is running. For example, the logging task may only
run once per second, so we don't really want to wait for its activation
time to change.
***********************************************************************/
static bool thread_started(const char *name, volatile uint64_t *thread_us, uint64_t timeout_us)
{

    // Verify thread_us becomes nonzero, waiting up to timeout_us.

    // This is done at startup to make sure the thread is running, and
    // to know that we can start monitoring thread_us to detect thread
    // stoppage.

    uint64_t start_us = clock_gettime_us(CLOCK_MONOTONIC);
    uint64_t now_us = start_us;

    while (now_us - start_us <= timeout_us) {
        if (__atomic_load_n(thread_us, __ATOMIC_SEQ_CST) != 0)
            return true;
        usleep(1000);
        now_us = clock_gettime_us(CLOCK_MONOTONIC);
    }

    // at this point it has been 1 usleep since we last checked
    if (__atomic_load_n(thread_us, __ATOMIC_SEQ_CST) != 0)
        return true;

    // this should be exceptional (bug indicator)
    syslog(LOG_ERR, "%s: thread failed to start", name);

    return false;

} // thread_started

/**********************************************************************
Function: int main(void)

Description: The main function.  Initializes and runs the serial and
             UDP threads.
***********************************************************************/
int main(void)
{
    string ipstr;

    openlog("pixrc", LOG_NDELAY, LOG_LOCAL0);

    syslog(LOG_INFO, "main: built " __DATE__ " " __TIME__);

    /* Parse the sololink.conf file for serial port, source IPs and ports */
    INIReader reader("/etc/sololink.conf");

    if (reader.ParseError() < 0) {
        std::cout << "Can't load /etc/sololink.conf\n";
        return -1;
    }

    /* Generate a vector of IP addresses that we can accept RC data from */
    string rcSourceIps = reader.Get("solo", "rcSourceIps", "10.1.1.1");
    istringstream ss(rcSourceIps);
    while (getline(ss, ipstr, ','))
        sourceIPs.push_back(ipstr);

    /* The incoming UDP port from which we accept data */
    sourcePort = reader.GetInteger("solo", "rcDestPort", 5005);

    /* Get the serial port to output DSM data on */
    serialPortName = reader.Get("solo", "rcDsmDev", "/dev/ttymxc2");

    // PWM mappings
    // throttle channel
    int pwmInMinThrottle = reader.GetInteger("solo", "pwmInMinThrottle", 1000);
    int pwmInMaxThrottle = reader.GetInteger("solo", "pwmInMaxThrottle", 2000);
    int pwmOutMinThrottle = reader.GetInteger("solo", "pwmOutMinThrottle", 1000);
    int pwmOutMaxThrottle = reader.GetInteger("solo", "pwmOutMaxThrottle", 1900);
    // all other channels
    int pwmInMinOther = reader.GetInteger("solo", "pwmInMinOther", 1000);
    int pwmInMaxOther = reader.GetInteger("solo", "pwmInMaxOther", 2000);
    int pwmOutMinOther = reader.GetInteger("solo", "pwmOutMinOther", 1000);
    int pwmOutMaxOther = reader.GetInteger("solo", "pwmOutMaxOther", 2000);

    /* RC timeout in microseconds */
    rc_timeout_max_us = reader.GetInteger("solo", "rcTimeoutUS", RC_TIMEOUT_US);

    /* Shotmgr timeout in microseconds */
    sm_timeout_max_us = reader.GetInteger("solo", "smTimeoutUS", SM_TIMEOUT_US);

    // create the mappers
    pwmToDsmThrottle = new (std::nothrow)
        PwmToDsm(pwmInMinThrottle, pwmInMaxThrottle, pwmOutMinThrottle, pwmOutMaxThrottle);
    if (pwmToDsmThrottle == NULL) {
        syslog(LOG_ERR, "main: can't create pwmToDsmThrottle");
        return -1;
    }
    pwmToDsmOther =
        new (std::nothrow) PwmToDsm(pwmInMinOther, pwmInMaxOther, pwmOutMinOther, pwmOutMaxOther);
    if (pwmToDsmOther == NULL) {
        syslog(LOG_ERR, "main: can't create pwmToDsmOther");
        return -1;
    }

    syslog(LOG_INFO, "main: rcSourceIps: %s", rcSourceIps.c_str());
    syslog(LOG_INFO, "main: rcDestPort:  %d", sourcePort);
    syslog(LOG_INFO, "main: rcDsmDev:    %s", serialPortName.c_str());
    syslog(LOG_INFO, "main: Throttle PWM in  %4d...%4d", pwmInMinThrottle, pwmInMaxThrottle);
    syslog(LOG_INFO, "main:          PWM out %4d...%4d", pwmOutMinThrottle, pwmOutMaxThrottle);
    // pwmToDsmDiag(pwmToDsmThrottle);
    syslog(LOG_INFO, "main: Other    PWM in  %4d...%4d", pwmInMinOther, pwmInMaxOther);
    syslog(LOG_INFO, "main:          PWM out %4d...%4d", pwmOutMinOther, pwmOutMaxOther);
    // pwmToDsmDiag(pwmToDsmOther);

    /* Set up the UDP and serial ports */
    if (!UDP_setup()) {
        // specific error already logged
        return -1;
    }

    if (!serial_setup()) {
        // specific error already logged
        return -1;
    }

    // Start the command processor
    command = new RcCommander("/run/rc_uplink_cmd");

    rc_locked = RcLock::locked();

    // Start the UDP and serial threads. UDP is started first so if the uplink
    // is already streaming, we won't get an initial throttle failsafe.
    start_UDP_thread();
    usleep(100000); // 0.1 sec
    start_serial_thread();

    // Wait for all to be running so we can't possibly detect a dead thread on
    // the first check below. It would be possible to guarantee they run first
    // (based on priorities) but that would be a fragile dependence.
    if (!thread_started("udp", &udp_run_us, UDP_STUCK_US) ||
        !thread_started("serial", &ser_run_us, SER_STUCK_US)) {
        // thread_started logs the error
        exit(0);
    }

    // The main while() loop just becomes a thread monitor.  If any thread dies,
    // exit and let inittab restart us
    while (true) {
        rc_locked = RcLock::locked();

        // Check that all threads are running (and not stuck).

        if (!thread_ok("udp", &udp_run_us, UDP_STUCK_US) ||
            !thread_ok("serial", &ser_run_us, SER_STUCK_US)) {
            // thread_ok logs the error
            exit(0);
        }

        usleep(100000); // check every 0.1 sec
    }

    return -1;

} // main
