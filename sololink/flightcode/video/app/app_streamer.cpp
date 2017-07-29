
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <syslog.h>
#include <unistd.h>

#include "INIReader.h"
#include "net_wmm.h"
#include "util.h"

// This is the module that runs on the controller, relaying video from Solo to
// the currently connected App.

// App's IP will appear in this file when app connects
static const char *app_ip_filename = "/var/run/solo_app.ip";

// Listen for video packets on this UDP port
static const unsigned my_port = 5550;

// Send video packets to this UDP port (in app)
static const unsigned app_port = 5600;

// Maximum packet size we will forward
// Video packets all fit in one Enet frame (~1500 bytes)
static const unsigned max_packet_bytes = 2000;

// Stats
static unsigned packet_count = 0;
static unsigned byte_count = 0;

// Frame-based transmits
static const unsigned max_frame_packets = 128;
struct pkt {
    char buf[max_packet_bytes];
    uint16_t len;
};

// Get app IP from file
// Note that returned value is network byte order
static in_addr_t get_app_ip(const char *filename)
{

    int fd = open(filename, O_RDONLY);
    if (fd < 0)
        return htonl(INADDR_NONE);

    // max reasonable IP length is 3+1+3+1+3+1+3=15
    char ip_buf[40];
    memset(ip_buf, 0, sizeof(ip_buf));
    ssize_t n_bytes = read(fd, ip_buf, sizeof(ip_buf) - 1);
    close(fd);
    if (n_bytes <= 0) {
        return htonl(INADDR_NONE);
    }

    // IP address is typically "10.1.1.10\n"; inet_addr accepts the '\n'
    return inet_addr(ip_buf);

} // get_app_ip

// Create socket used to send and receive video packets.
// To support receive, bind the socket to the video port, any interface.
// To support send, set the TOS we want for video packets.
static int create_socket(int tos)
{
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        syslog(LOG_ERR, "creating socket");
        return -1;
    }

    // bind to the input port on any interface
    struct sockaddr_in my_addr;
    memset(&my_addr, 0, sizeof(my_addr));
    my_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    my_addr.sin_port = htons(my_port);
    if (bind(fd, (struct sockaddr *)&my_addr, sizeof(my_addr)) < 0) {
        syslog(LOG_ERR, "binding socket");
        return -1;
    }

    // set TOS for output packets
    if (setsockopt(fd, IPPROTO_IP, IP_TOS, &tos, sizeof(tos)) != 0) {
        syslog(LOG_ERR, "setting socket options");
        return -1;
    }

    return fd;

} // create_socket

// Create the local socket used to send and video packets to the local stream (HDMI output).
// No need to bind as we just dump data across.
static int create_local_socket(void)
{
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        syslog(LOG_ERR, "creating local stream socket");
        return -1;
    }

    return fd;
} // create_local_socket

int main(int argc, const char *argv[])
{
    openlog("streamer", LOG_NDELAY, LOG_LOCAL3);

    syslog(LOG_INFO, "starting: built " __DATE__ " " __TIME__);

    INIReader reader("/etc/sololink.conf");

    if (reader.ParseError() < 0) {
        syslog(LOG_ERR, "can't load /etc/sololink.conf");
        return -1;
    }

    int app_check_interval_s = reader.GetInteger("video", "vidAppInt", 1);
    unsigned app_check_interval_us = app_check_interval_s * 1000000;

    int log_interval_s = reader.GetInteger("video", "vidLogInt", 10);
    unsigned log_interval_us = log_interval_s * 1000000;

    int app_video_tos = reader.GetInteger("video", "vidAppTos", 0xbf);

    int fd = create_socket(app_video_tos);
    if (fd < 0)
        return 1; // error already logged

    int local_fd = create_local_socket();
    if (local_fd < 0)
        return 1; // error already logged

    uint64_t now_us = clock_gettime_us(CLOCK_MONOTONIC);

    // most recent log time, init to "now" for calculation purposes
    // (first message might be a bit off)
    uint64_t log_last_us = now_us;

    // next log time
    uint64_t log_time_us = log_last_us + log_interval_us;

    // next time to check for app IP change
    uint64_t app_check_us = now_us;

    in_addr_t app_ip = htonl(INADDR_NONE);
    struct sockaddr_in app_addr;

    // Setup the local streaming port
    struct sockaddr_in local_addr;
    memset(&local_addr, 0, sizeof(local_addr));
    local_addr.sin_family = AF_INET;
    local_addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    local_addr.sin_port = htons(app_port); // Same port as the app

    // For sending full frame packets
    struct pkt frame_pkts[max_frame_packets];
    unsigned frame_pkt_idx = 0;
    bool frame_complete = false;
    unsigned i;
    int small_pkt_count = 0;

    // For sequence monitoring
    int seq = 0;
    int last_seq = 0;
    int drops = 0;

    const int num_fds = 1;
    struct pollfd fd_set[num_fds];
    memset(fd_set, 0, sizeof(fd_set));
    fd_set[0].fd = fd;
    fd_set[0].events = POLLIN;

    // handle downlink video packets
    while (1) {

        // Calculate timeout such that if it expires, we know that it will be
        // time to log status or check the app IP (the +1 at the end). E.g if
        // log time is 999 usec later than now, delay 1 msec (not zero).
        uint64_t now_us = clock_gettime_us(CLOCK_MONOTONIC);
        int timeout_ms;
        // timeout based on log time or app check time, whichever is sooner
        if (log_time_us < app_check_us)
            timeout_ms = (log_time_us - now_us) / 1000 + 1;
        else
            timeout_ms = (app_check_us - now_us) / 1000 + 1;
        if (timeout_ms < 0)
            // handle race condition where we check times at the bottom of
            // this loop, then calculate the delay a bit later (here)
            timeout_ms = 0;

        // If poll returns with an error, fd_set is unmodified, so let's make
        // sure we don't false-detect a ready socket
        fd_set[0].revents = 0;

        int pollrc = poll(fd_set, num_fds, timeout_ms);

        if ((pollrc > 0) && (fd_set[0].revents & POLLIN)) {
            char pkt_buf[max_packet_bytes];

            ssize_t pkt_bytes = recv(fd, pkt_buf, sizeof(pkt_buf), 0);

            now_us = clock_gettime_us(CLOCK_MONOTONIC);

            // We shouldn't get any errors from recv. If we do, something new or
            // exciting is going on. Log a message, and to avoid soaking the CPU,
            // sleep a second before looking for another packet. The sleep will
            // disrupt any video that might be playing, but again, we should not
            // get any errors here, so the main goal is to let the rest of the
            // system run, even at the cost of bad video.

            if (pkt_bytes <= 0) {
                syslog(LOG_ERR, "recv returned %d", pkt_bytes);
                sleep(1);
            } else {
                if (sendto(local_fd, pkt_buf, pkt_bytes, 0, (struct sockaddr *)&local_addr,
                           sizeof(local_addr)) != pkt_bytes) {
                    // Another error we should never see
                    syslog(LOG_ERR, "sendto local returned error");
                    sleep(1);
                }
                // Pull the sequence number off the header
                seq = pkt_buf[2] << 8 | pkt_buf[3];
                if (seq > (last_seq + 1) && last_seq && seq > last_seq)
                    drops += (seq - last_seq - 1);

                last_seq = seq;

                // Copy this packet into the frame packet buffer
                memcpy(frame_pkts[frame_pkt_idx].buf, pkt_buf, pkt_bytes);
                frame_pkts[frame_pkt_idx].len = pkt_bytes;

                // If this is a full frame send it.  Or, if its a tiny packet (black screen) send
                // it.
                // Or if we're out of space, send it all.
                if ((pkt_buf[12] == 0x5c && pkt_buf[13] == 0x81) ||
                    frame_pkt_idx == max_frame_packets - 1)
                    frame_complete = true;

                // We look for small packets.  If we get 3 in a row then we start sending them,
                // as it could be a black frame.  Otherwise, don't send them until we get a
                // new frame.  128 bytes consist a "small" packet.  Black frames tend to be <100B.
                if (pkt_bytes < 128) {
                    if (small_pkt_count >= 2)
                        frame_complete = true;
                    else
                        ++small_pkt_count;
                } else if (small_pkt_count > 0)
                    small_pkt_count = 0;

                // stats are for downlink packets (vs. forwarded packets)
                packet_count++;
                byte_count += pkt_bytes;

                // If we have a complete frame or we have no more room, send it along
                if (frame_complete) {
                    if (app_ip != htonl(INADDR_NONE)) {
                        // Send the entire frame of packets
                        for (i = 0; i <= frame_pkt_idx; ++i) {
                            if (sendto(fd, frame_pkts[i].buf, frame_pkts[i].len, 0,
                                       (struct sockaddr *)&app_addr,
                                       sizeof(app_addr)) != frame_pkts[i].len) {
                                // Another error we should never see, even if the app has
                                // disconnected.
                                syslog(LOG_ERR, "sendto returned error");
                                sleep(1);
                            }
                        }
                    }
                    // Reset the frame pkt index, frame_complete flag
                    frame_pkt_idx = 0;
                    frame_complete = false;
                } else {
                    // Check if our buffer is full, discard if so
                    ++frame_pkt_idx;
                    if (frame_pkt_idx >= max_frame_packets) {
                        frame_pkt_idx = 0;
                        continue;
                    }
                }

            } // if (pkt_bytes...)

        } else // if ((pollrc > 0) && (fd_set[0].revents & POLLIN))
        {
            // Timeout or error. In either case, we log or check app if it is
            // time then just try again.
            now_us = clock_gettime_us(CLOCK_MONOTONIC);
        }

        // log stats if it is time
        if (now_us > log_time_us) {
            uint64_t interval_us = now_us - log_last_us;
            unsigned packets_sec = (packet_count * 1000000ULL) / interval_us;
            unsigned bytes_sec = (byte_count * 1000000ULL) / interval_us;

            syslog(LOG_INFO, "pkts=%i bytes=%i drops=%i", packets_sec, bytes_sec, drops);

            packet_count = 0;
            byte_count = 0;
            drops = 0;

            log_last_us = now_us;
            log_time_us += log_interval_us;
        }

        // check for change in app IP if it is time
        if (now_us > app_check_us) {
            in_addr_t ip = get_app_ip(app_ip_filename);
            if (app_ip != ip) {
                app_ip = ip;
                if (app_ip == htonl(INADDR_NONE)) {
                    syslog(LOG_INFO, "app disconnected");
                } else {
                    memset(&app_addr, 0, sizeof(app_addr));
                    app_addr.sin_addr.s_addr = app_ip;
                    app_addr.sin_port = htons(app_port);
                    struct in_addr app_in_addr = {app_ip};
                    syslog(LOG_INFO, "app connected at %s", inet_ntoa(app_in_addr));
                }
            }
            app_check_us = now_us + app_check_interval_us;
        }

    } // while (1)

} // main
