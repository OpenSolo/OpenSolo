
#include <fcntl.h>
#include <stdio.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>
#include <netinet/in.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/types.h>

#include "mavlink.h"

#include "util.h"

#if (defined __MACH__ && defined __APPLE__)
#define B460800	460800
#define B921600	921600
#endif

// mavpkt
//
// Receive byte stream and output complete mavlink packets
//
// Input can be any file descriptor (i.e. stdin, file, serial port).
// Output is normally a datagram-ish file descriptor.

static void usage(void)
{
    fprintf(stderr, "mavpkt\n");
    fprintf(stderr, "                           input defaults to stdin\n");
    fprintf(stderr, "  -i tlog                  input is tlog format (default no)\n");
    fprintf(stderr, "  -i udp://0.0.0.0:7007    input from the specified UDP port\n");
    fprintf(stderr, "                           output defaults to stdout\n");
    fprintf(stderr, "  -o tlog                  output is tlog format (default no)\n");
    fprintf(stderr, "  -o udp://127.0.0.1:6006  output to the specified UDP port\n");
    fprintf(stderr, "  -r                       realtime (requires tlog input)\n");
    fprintf(stderr, "  -s                       print stats to stderr at end\n");
    fprintf(stderr, "  -v                       print input packets to stderr\n");
    exit(1);
}

// 'tlog' format means each mavlink packet is preceeded by the time since the
// epoch in microseconds as a 64-bit big-endian unsigned.

// 'realtime' means packets will be emitted in approximately real time,
// according to the timestamps in the input (which must be tlog). Allows
// "playing back" a tlog.

// -i udp://0.0.0.0:7007 means mavpkt will read packets from this UDP port.
// This example means the read socket will be bound to INADDR_ANY, port 7007,
// so an external program should send packets to that port on this machine.

// -o udp://127.0.0.1:6006 means mavpkt will send to this UDP port. This
// example means an ouput socket will be created and bound to a system-
// supplied port, and will send packets to localhost, port 6006.

// -i serial:///dev/ttymxc1?baud=115200,flow=1 reads from the given serial
// port with a specified baud rate. flow=1 enables hardware flow control.

// Examples:
//
// Read raw packets from a port and write a tlog:
// mavpkt -i udp://0.0.0.0:9000 -o tlog > packets.tlog
//
// Read raw packets from a port and write a raw data file:
// mavpkt -i udp://0.0.0.0:9000 > packets.bin
//
// Play a tlog to UDP port 8800 in real time:
// mavpkt -i tlog -o udp://127.0.0.1:8800 -r < packets.tlog
//
// Show stats for a tlog file:
// mavpkt -i tlog -s < packets.tlog > /dev/null


// MAVLINK_MESSAGE_INFO has 256 elements; sizeof(mavlink_info)=528384
static mavlink_message_info_t mavlink_info[] = MAVLINK_MESSAGE_INFO;

// MAVLINK_MESSAGE_CRCS is an array of 256 bytes
static uint8_t mavlink_crc[] = MAVLINK_MESSAGE_CRCS;

// A mavlink packet is limited to 6+255+2 = 263 bytes
// 6 byte header, 255 max bytes in payload, 2 byte crc

#ifndef MAVLINK_STX
#define MAVLINK_STX     254
#endif

// input stream bytes to read at once
#define READ_MAX        1024

static uint8_t data_in[READ_MAX];


// unpack_uint64 - unpack uint64_t from byte stream
static uint64_t unpack_uint64(const uint8_t* p)
{
    uint64_t d = 0;
    for (int i = 0; i < 8; i++)
        d = (d << 8) | *p++;
    return d;
}


// pack_uint64 - pack uint64_t into byte stream
static void pack_uint64(uint64_t d, uint8_t* p)
{
    for (int i = 56; i >= 0; i -= 8)
        *p++ = d >> i;
}


// calc_crc - calculate the CRC of a mavlink message
//
// CRC is seeded, then starts with the byte after the magic, continues through
// the payload up to the CRC in the message, then add the message-id-specific
// byte.
//
// Returns the 16-bit CRC.
static uint16_t calc_crc(const uint8_t* p)
{
    uint8_t payload_len = p[1];
    uint8_t msg_id = p[5];
    unsigned crc_len = 5 + payload_len;

    uint16_t crc = crc_calculate(p + 1, crc_len);

    crc_accumulate(mavlink_crc[msg_id], &crc);

    return crc;

} // calc_crc


// get_crc - get (extract) the CRC of a mavlink message
//
// Returns the 16-bit CRC.
static uint16_t get_crc(const uint8_t* p)
{
    uint8_t payload_len = p[1];

    uint16_t crc = p[6 + payload_len + 1];  // msb
    crc <<= 8;
    crc |= p[6 + payload_len];              // lsb

    return crc;

} // get_crc


// check_crc - check the crc of a mavlink message
//
// Returns true if CRC correct, else false.
static bool check_crc(const uint8_t* p)
{
    return calc_crc(p) == get_crc(p);
}


// When accumulating statistics, we keep track of messages received from each
// (system, comeonent). Rather than allowing for all combinations (65536 of
// them) we just keep track of the first SOURCES_MAX we see. If there are more
// than that, the stats will be wrong. Dynamic allocation might be better, but
// really if there are more than a handful, the input data is probably junk.
#define SOURCES_MAX 10

static struct
{
    unsigned total;
    unsigned crc_err;
    unsigned bytes_discarded;
    uint64_t first_us;
    uint64_t last_us;
    unsigned num_sources;
    struct
    {
        unsigned total;
        unsigned crc_err;
    } by_id[256];
    struct
    {
        uint8_t in_use;
        uint8_t sys;
        uint8_t comp;
        unsigned total;
        unsigned crc_err;
        struct
        {
            unsigned total;
            unsigned crc_err;
        } by_id[256];
    } by_src[SOURCES_MAX];
} pkt_stats;


static void pkt_stats_init(void)
{
    memset(&pkt_stats, 0, sizeof(pkt_stats));
}


// pkt_stats_add - add packet to statistics
static void pkt_stats_add(uint8_t* p)
{
    // 0..7 timestamp
    //    8 magic
    //    9 length
    //   10 sequence

    uint64_t pkt_us = unpack_uint64(p);
    uint8_t sys = p[11];
    uint8_t comp = p[12];
    uint8_t id = p[13];

    // 1 if crc bad, 0 if crc good
    unsigned crc_err = check_crc(p + 8) ? 0 : 1;

    pkt_stats.total++;
    pkt_stats.crc_err += crc_err;
    pkt_stats.by_id[id].total++;
    pkt_stats.by_id[id].crc_err += crc_err;

    if (pkt_stats.first_us == 0)
        pkt_stats.first_us = pkt_us;
    pkt_stats.last_us = pkt_us;

    for (int s = 0; s < SOURCES_MAX; s++)
    {
        if (!pkt_stats.by_src[s].in_use)
        {
            pkt_stats.by_src[s].in_use = true;
            pkt_stats.by_src[s].sys = sys;
            pkt_stats.by_src[s].comp = comp;
            pkt_stats.num_sources++;
        }
        if (pkt_stats.by_src[s].sys == sys &&
            pkt_stats.by_src[s].comp == comp)
        {
            pkt_stats.by_src[s].total++;
            pkt_stats.by_src[s].crc_err += crc_err;
            pkt_stats.by_src[s].by_id[id].total++;
            pkt_stats.by_src[s].by_id[id].crc_err += crc_err;
            return;
        }
    }
    pkt_stats.num_sources++;
} // pkt_stats_add


// pkt_stats_print - print accumulated statistics to stderr
static void pkt_stats_print(void)
{

    fprintf(stderr, "\n");
    fprintf(stderr, "packets:         %u\n", pkt_stats.total);
    fprintf(stderr, "crc errors:      %u\n", pkt_stats.crc_err);
    fprintf(stderr, "bytes discarded: %u\n", pkt_stats.bytes_discarded);
    char ts_buf[32];
    fprintf(stderr, "first packet:    %s\n", clock_tostr_r(pkt_stats.first_us, ts_buf));
    fprintf(stderr, "last packet:     %s\n", clock_tostr_r(pkt_stats.last_us, ts_buf));
    fprintf(stderr, "sources:         %u\n", pkt_stats.num_sources);
    uint64_t span_us = pkt_stats.last_us - pkt_stats.first_us;
    uint64_t us_per_s = 1000000;
    uint64_t us_per_m = 60 * us_per_s;
    uint64_t us_per_h = 60 * us_per_m;
    unsigned span_h = span_us / us_per_h;
    span_us -= (span_h * us_per_h);
    unsigned span_m = span_us / us_per_m;
    span_us -= (span_m * us_per_m);
    unsigned span_s = span_us / us_per_s;
    span_us -= (span_s * us_per_s);
    unsigned span_ms = span_us / 1000;
    fprintf(stderr, "time span:       %02u:%02u:%02u.%03u\n", span_h, span_m, span_s, span_ms);
    fprintf(stderr, "\n");
    // table heading, e.g.
    // " id     0,0         1,1        10,0         1,154      total"
    fprintf(stderr, " id");
    for (int s = 0; s < SOURCES_MAX && pkt_stats.by_src[s].in_use; s++)
        fprintf(stderr, " %5u,%-5u", pkt_stats.by_src[s].sys, pkt_stats.by_src[s].comp);
    fprintf(stderr, "    total\n");
    // print row for each id we got any packets for
    for (int id = 0; id < 256; id++)
    {
        if (pkt_stats.by_id[id].total == 0)
            continue;
        // table row, e.g.
        // "  0     -/-        22/0         -/-         -/-        22/0      HEARTBEAT"
        fprintf(stderr, "%3d", id);
        for (int s = 0; s < SOURCES_MAX && pkt_stats.by_src[s].in_use; s++)
        {
            if (pkt_stats.by_src[s].by_id[id].total > 0)
                fprintf(stderr, " %5u/%-5u", pkt_stats.by_src[s].by_id[id].total,
                        pkt_stats.by_src[s].by_id[id].crc_err);
            else
                fprintf(stderr, " %5s/%-5s", "-", "-");
        }
        fprintf(stderr, " %5d/%-5d", pkt_stats.by_id[id].total, pkt_stats.by_id[id].crc_err);
        fprintf(stderr, "  %-s\n", mavlink_info[id].name);
    }

} // pkt_stats_print


// udp_uri - parse uri for udp address and create socket for it
//
// is_dest determines whether the parsed address is where we send packets
// (is_dest true), or it is our local address, which we will bind to and read
// packets from (is_dest false).
//
// is_dest true: create a socket and connect it to the parsed address
// is_dest false: create a socket and bind it to the parsed address
//
// Note that for UDP sockets, 'connect' to an address saves the address as the
// destination to use in future send() calls.
//
// Returns: fd of socket on success, or -1 on error
static int udp_uri(const char* uri, bool is_dest)
{

    if (strncmp(uri, "udp:", 4) != 0)
        return -1;

    unsigned int ip1, ip2, ip3, ip4, port;
    if (sscanf(uri, "udp://%u.%u.%u.%u:%u", &ip1, &ip2, &ip3, &ip4, &port) != 5 ||
               ip1 > 255 || ip2 > 255 || ip3 > 255 || ip4 > 255 || port > 65535)
    {
        fprintf(stderr, "error parsing \"%s\"\n", uri);
        return -1;
    }

    uint32_t ip = (ip1 << 24) | (ip2 << 16) | (ip3 << 8) | ip4;
    struct sockaddr_in sa_uri;
    memset(&sa_uri, 0, sizeof(sa_uri));
    sa_uri.sin_family = AF_INET;
    sa_uri.sin_addr.s_addr = htonl(ip);
    sa_uri.sin_port = htons(port);

    struct sockaddr_in sa_any;
    memset(&sa_any, 0, sizeof(sa_any));
    sa_any.sin_family = AF_INET;
    sa_any.sin_addr.s_addr = htonl(INADDR_ANY);
    sa_any.sin_port = htons(0);

    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0)
    {
        perror("socket");
        return -1;
    }

    // is_dest = false means the uri is the address of this socket
    // is_dest = true means the uri is where we send packets

    if (is_dest)
    {
        if (bind(fd, (struct sockaddr*)&sa_any, sizeof(sa_any)) != 0)
        {
            perror("bind");
            close(fd);
            return -1;
        }
        // connect sets the default destination address
        if (connect(fd, (struct sockaddr*)&sa_uri, sizeof(sa_uri)) != 0)
        {
            perror("connect");
            close(fd);
            return -1;
        }
    }
    else
    {
        // just bind to specified uri
        if (bind(fd, (struct sockaddr*)&sa_uri, sizeof(sa_uri)) != 0)
        {
            perror("bind");
            close(fd);
            return -1;
        }
    }

    return fd;

} // udp_uri


// serial_uri - parse uri for serial port and create fd for it
//
// Returns: fd of port on success, or -1 on error
static int serial_uri(const char* uri)
{

    if (strncmp(uri, "serial:", 7) != 0)
        return -1;

    char dev_opts[80];
    if (sscanf(uri, "serial://%s", dev_opts) != 1)
    {
        fprintf(stderr, "error parsing \"%s\"\n", uri);
        return -1;
    }

    // /dev/ttyS0?baud=115200,flow=1
    char *str = dev_opts;
    char *dev_name = strsep(&str, "?");
    unsigned int baud = 0;
    unsigned int flow = 0; // 0=none, 1=hw (2=sw TBD)
    while (str != NULL && *str != '\0')
    {
        char *opt = strsep(&str, ",");
        if (sscanf(opt, "baud=%u", &baud) == 1)
            continue;
        else if (sscanf(opt, "flow=%u", &flow) == 1)
            continue;
        else
        {
            fprintf(stderr, "error parsing \"%s\"\n", uri);
            return -1;
        }
    }

    int fd = open(dev_name, O_RDWR | O_NOCTTY);
    if (fd < 0)
    {
        perror("open");
        return -1;
    }

    struct termios options;

    memset(&options, 0, sizeof(options));

    tcgetattr(fd, &options);

    switch (baud)
    {
        case 57600: cfsetspeed(&options, B57600); break;
        case 115200: cfsetspeed(&options, B115200); break;
        case 230400: cfsetspeed(&options, B230400); break;
        case 460800: cfsetspeed(&options, B460800); break;
        case 921600: cfsetspeed(&options, B921600); break;
        default:
            fprintf(stderr, "unsupported baudrate %u", baud);
            return -1;
    }

    options.c_iflag &= ~(IGNBRK | BRKINT | ICRNL | INLCR | PARMRK | INPCK | ISTRIP | IXON);
    options.c_oflag &= ~(OCRNL | ONLCR | ONLRET | ONOCR | OFILL | OPOST);
    options.c_lflag &= ~(ECHO | ECHONL | ICANON | IEXTEN | ISIG);
    options.c_cflag &= ~(CSIZE | PARENB);
    options.c_cflag |= CS8;
    options.c_cc[VMIN]  = 20;
    options.c_cc[VTIME] = 0;

    if (flow == 1)
    {
        options.c_cflag |= CRTSCTS;
    }
    else
    {
        options.c_cflag &= ~CRTSCTS;
        options.c_cflag |= CLOCAL;
    }

    tcflush(fd, TCIFLUSH);

    tcsetattr(fd, TCSANOW, &options);

    return fd;

} // serial_uri


// print_pkt - print packet to stderr
static void print_pkt(const uint8_t* p, bool tlog)
{

    uint64_t ts = unpack_uint64(p);
    char ts_buf[32];
    fprintf(stderr, "%s ", clock_tostr_r(ts, ts_buf));

    p += 8;
    unsigned num_bytes = 6 + p[1] + 2;
    for (unsigned i = 0; i < (num_bytes - 1); i++)
        fprintf(stderr, "%02x ", *p++);
    fprintf(stderr, "%02x\n", *p);

} // print_pkt


// emit_packet - emit packet to file descriptor
//
// Packet can be emitted raw (just a write) or it can be emitted to a tlog
// (preceeded by timestamp).
//
// pkt supplied always has 8 bytes at the start for the timestamp. If not
// tlog, they are simply skipped.
static int emit_packet(int fd, const uint8_t* pkt, bool tlog, bool verbose)
{
    if (verbose)
        print_pkt(pkt, tlog);

    int bytes;
    if (tlog)
        bytes = 8 + 6 + pkt[9] + 2;
    else
    {
        bytes = 6 + pkt[9] + 2;
        pkt += 8;
    }

    if (write(fd, pkt, bytes) != bytes)
        return -1;

    return bytes;

} // emit_packet


int main(int argc, char* argv[])
{
    int fd;
    int fd_in = STDIN_FILENO;
    int fd_out = STDOUT_FILENO;
    bool tlog_in = false;
    bool tlog_out = false;
    unsigned data_in_bytes;
    bool verbose = false;
    bool realtime = false;
    bool stats = false;
    uint64_t rt_first_us = 0;   // real time first packet emitted
    int opt;

    //fprintf(stderr, "sizeof(mavlink_info) = %ld\n", sizeof(mavlink_info));
    //fprintf(stderr, "nelems(mavlink_info) = %ld\n", sizeof(mavlink_info)/sizeof(mavlink_info[0]));

    //
    // Parse arguments
    //

    while ((opt = getopt(argc, argv, "hi:o:rsv")) != -1)
    {
        switch (opt)
        {
        case 'h':
            usage();
            break;
        case 'i':
            if (strcmp(optarg, "tlog") == 0)
                tlog_in = true;
            else if ((fd = udp_uri(optarg, false)) != -1)
                fd_in = fd;
            else if ((fd = serial_uri(optarg)) != -1)
                fd_in = fd;
            else
                usage();
            break;
        case 'o':
            if (strcmp(optarg, "tlog") == 0)
                tlog_out = true;
            else if ((fd = udp_uri(optarg, true)) != -1)
                fd_out = fd;
            else
                usage();
            break;
        case 'r':
            realtime = true;
            break;
        case 's':
            stats = true;
            break;
        case 'v':
            verbose = true;
            break;
        default:
            usage();
        }
    }

    //
    // Initialize data structures
    //

    pkt_stats_init();

    memset(data_in, 0, sizeof(data_in));
    data_in_bytes = 0;

    // If the input data does not have a timestamp, leave space at the start
    // to insert a timestamp in the output packet
    if (!tlog_in)
        data_in_bytes = 8;

    //
    // Process input bytes, writing output packets
    //

    while (1)
    {

        unsigned read_max = READ_MAX - data_in_bytes;
        int num_read = read(fd_in, data_in + data_in_bytes, read_max);

        if (num_read == 0)
        {
            // eof
            break;
			// XXX Needs fixing for serial input
        }

        if (num_read < 0)
        {
            // error
            perror("read");
            break;
        }

        data_in_bytes += num_read;

        // Outer loop is in case we have more than one packet
        bool emitted;
        do
        {
            emitted = false;

            // Throw away data from the start until there's magic in the right
            // place. This loop should almost never have to execute.
            while (data_in_bytes > 8 && data_in[8] != MAVLINK_STX)
            {
                memmove(data_in, data_in + 1, --data_in_bytes);
                pkt_stats.bytes_discarded++;
            }

            // emit packet if we have one
            if (data_in_bytes > 9 && data_in_bytes >= (unsigned)(8 + 6 + data_in[9] + 2))
            {
                uint64_t now_us = clock_gettime_us(CLOCK_REALTIME);

                uint64_t ts_pkt_us; // timestamp of this packet
                if (tlog_in)
                {
                    // get timestamp from packet
                    ts_pkt_us = unpack_uint64(data_in);
                }
                else
                {
                    // use timestamp from clock; save it in packet
                    ts_pkt_us = now_us;
                    pack_uint64(ts_pkt_us, data_in);
                }

                pkt_stats_add(data_in);

                // if simulating realtime, delay until it is time for this packet to go
                if (tlog_in && realtime)
                {
                    if (rt_first_us == 0)
                    {
                        // real time first packet emitted
                        rt_first_us = now_us;
                    }
                    else
                    {
                        // delay until time for this packet to go
                        int64_t delay_us = (ts_pkt_us - pkt_stats.first_us) - (now_us - rt_first_us);
                        if (delay_us > 0)
                            usleep(delay_us);
                    }
                }

                emit_packet(fd_out, data_in, tlog_out, verbose);

                // If the input is not tlog, we still leave space at front for
                // timestamp, making it so we can stuff in the timestamp and
                // write the output without needing a separate output buffer.
                if (tlog_in)
                {
                    // consume timestamp; copy data to very start of buffer
                    unsigned consume_bytes = 8 + 6 + data_in[9] + 2;
                    data_in_bytes -= consume_bytes;
                    memmove(data_in, data_in + consume_bytes, data_in_bytes);
                }
                else
                {
                    // don't consume timestamp; copy data to right after timestamp
                    unsigned consume_bytes = 6 + data_in[9] + 2;
                    data_in_bytes -= consume_bytes;
                    memmove(data_in + 8, data_in + 8 + consume_bytes, data_in_bytes);
                }
                // This flag makes it so we'll check the input buffer again,
                // in case we got more than one packet in the last read
                // (which is common).
                emitted = true;
            }

        }
        while (emitted);

    } // while (1)

    //
    // Print statistics if requested
    //

    if (stats)
        pkt_stats_print();

    exit(0);

} // main
