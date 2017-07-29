
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <stddef.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

#include "mavlink.h"


#define SERIAL_DEV_NAME "/dev/ttymxc1"


// Needs to match pixhawk's setting
#define SERIAL_DEV_BAUD 921600
#define SERIAL_DEV_BAUD_CODE B921600
//#define SERIAL_DEV_BAUD 460800
//#define SERIAL_DEV_BAUD_CODE B460800
//#define SERIAL_DEV_BAUD 230400
//#define SERIAL_DEV_BAUD_CODE B230400
//#define SERIAL_DEV_BAUD 115200
//#define SERIAL_DEV_BAUD_CODE B115200

#define SERIAL_TX_BUF_SIZE 4096

// MAVLINK_MESSAGE_INFO has 256 elements; sizeof(mavlink_info)=528384
//static mavlink_message_info_t mavlink_info[] = MAVLINK_MESSAGE_INFO;

// MAVLINK_MESSAGE_CRCS is an array of 256 bytes
static uint8_t mavlink_crc[] = MAVLINK_MESSAGE_CRCS;

// A mavlink packet is limited to 6+255+2 = 263 bytes
// 6 byte header, 255 max bytes in payload, 2 byte crc

static volatile bool restart = false;

static pthread_t downstream_id;


// mode = O_RDONLY or O_WRONLY
static int serial_setup(int mode)
{
    int fd;
    struct termios options;

    fd = open(SERIAL_DEV_NAME, mode | O_NOCTTY | O_NONBLOCK);
    if (fd < 0)
    {
        perror("open");
        return -1;
    }

    tcgetattr(fd, &options);

    cfsetspeed(&options, SERIAL_DEV_BAUD_CODE);

    options.c_iflag &= ~(IGNBRK | BRKINT | ICRNL | INLCR | PARMRK | INPCK | ISTRIP | IXON);
    options.c_oflag &= ~(OCRNL | ONLCR | ONLRET | ONOCR | OFILL | OPOST);
    options.c_lflag &= ~(ECHO | ECHONL | ICANON | IEXTEN | ISIG);
    options.c_cflag &= ~(CSIZE | PARENB);
    options.c_cflag |= CS8;
#if 1
    options.c_cflag |= CLOCAL;
    options.c_cflag &= ~(CRTSCTS);
#else
    options.c_cflag |= CRTSCTS;
#endif
    options.c_cc[VMIN]  = 17;
    options.c_cc[VTIME] = 0;

    tcsetattr(fd, TCSANOW, &options);

    return fd;

} // serial_setup


// Downstream thread reads from the serial port, doing just enough mavlink
// synchronization to allow packet counting. The only thing packet counting
// does is verify we're at the right baud rate.
static void* downstream(void* arg)
{
    const unsigned READ_MAX = 500;
    uint8_t data_in[READ_MAX];
    unsigned data_in_bytes = 0;
    unsigned bytes_dropped = 0;
    unsigned pkts_received = 0;
    const int nfds = 1;
    struct pollfd fds[nfds];
    int dn_fd = -1;

    dn_fd = serial_setup(O_RDONLY);
    if (dn_fd < 0)
        exit(1);
    printf("dn_fd=%d\n", dn_fd);

    while (1)
    {

        if (restart)
        {
            fprintf(stderr, "down: restarting...\n");
            close(dn_fd);
            fprintf(stderr, "down: restart = false\n");
            restart = false;
            dn_fd = serial_setup(O_RDONLY);
            if (dn_fd < 0)
                exit(1);
            printf("new dn_fd=%d\n", dn_fd);
        }

        fds[0].fd = dn_fd;
        fds[0].events = POLLIN;

        if (poll(fds, nfds, -1) <= 0)
        {
            perror("poll");
            sleep(1);
            continue;
        }

        unsigned read_max = READ_MAX - data_in_bytes;
        int num_read = read(dn_fd, data_in + data_in_bytes, read_max);

        if (num_read == 0)
        {
            // eof
            break;
        }

        if (num_read < 0)
        {
            // error
            perror("read");
            break;
        }

        data_in_bytes += num_read;

        bool emitted;

        do
        {

            emitted = false;

            // Throw away data from the start until there's magic in the right
            // place. This loop should almost never have to execute.
            while (data_in_bytes > 0 && data_in[0] != MAVLINK_STX)
            {
                memmove(data_in, data_in + 1, --data_in_bytes);
                bytes_dropped++;
            }

            // consume packet if we have one
            if (data_in_bytes > 1 && data_in_bytes >= (unsigned)(6 + data_in[1] + 2))
            {
                pkts_received++;
                unsigned consume_bytes = 6 + data_in[1] + 2;
                data_in_bytes -= consume_bytes;
                memmove(data_in, data_in + consume_bytes, data_in_bytes);
                emitted = true;

                if (pkts_received >= 100)
                {
                    printf("%d packets received, %d bytes dropped\n", pkts_received, bytes_dropped);
                    pkts_received -= 100;
                }
            }

        }
        while (emitted);

    } // while (1)

    return NULL;

} // downstream


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
}


// set_crc - set the CRC in a mavlink message
static void set_crc(uint8_t* p, uint16_t crc)
{
    unsigned payload_len = p[1];
    p[6 + payload_len] = crc;
    p[6 + payload_len + 1] = crc >> 8;
}


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


// Start downstream thread, then do upstream loop here.
// The upstream loop just sends the same mavlink packet out as fast as it can.
int main(int argc, char* argv[])
{
    int num_bytes;
    int tot_bytes = 0;
    uint8_t msg[300];
    int msg_bytes;
    uint16_t crc;
    const int nfds = 1;
    struct pollfd fds[nfds];
    int poll_rc;
    int up_fd = -1;

    pthread_create(&downstream_id, NULL, downstream, NULL);

    memset(&msg, 0, sizeof(msg));
#if 0
    // version request message
    msg[0] = MAVLINK_STX;                                   // sync
    msg[1] = MAVLINK_MSG_ID_AUTOPILOT_VERSION_REQUEST_LEN;  // msg length
    msg[2] = 0;                                             // sequence
    msg[3] = 10;                                            // src id
    msg[4] = 10;                                            // src component
    msg[5] = MAVLINK_MSG_ID_AUTOPILOT_VERSION_REQUEST;      // msg id
    msg[6] = 1;                                             // target system
    msg[7] = 1;                                             // target component
    msg_bytes = 6 + MAVLINK_MSG_ID_AUTOPILOT_VERSION_REQUEST_LEN + 2;
#elif 1
    // encapsulated data message
    msg[0] = MAVLINK_STX;                                   // sync
    msg[1] = MAVLINK_MSG_ID_ENCAPSULATED_DATA_LEN;          // msg length
    msg[2] = 0;                                             // sequence
    msg[3] = 10;                                            // src id
    msg[4] = 10;                                            // src component
    msg[5] = MAVLINK_MSG_ID_ENCAPSULATED_DATA;              // msg id
    msg_bytes = 6 + MAVLINK_MSG_ID_ENCAPSULATED_DATA_LEN + 2;
#endif

    crc = calc_crc(msg);
    set_crc(msg, crc);
    if (!check_crc(msg))
    {
        fprintf(stderr, "CRC ERROR\n");
        exit(1);
    }

    up_fd = serial_setup(O_WRONLY);
    if (up_fd < 0)
        exit(1);
    printf("up_fd=%d\n", up_fd);

    fds[0].fd = up_fd;
    fds[0].events = POLLOUT;

    while (1)
    {

        poll_rc = poll(fds, nfds, 1000);
        if (poll_rc < 0)
        {
            perror("poll");
            sleep(1);
            continue;
        }
        else if (poll_rc == 0)
        {
            // timeout
            fprintf(stderr, "up: write stuck\n");

            // super hacky restart
            close(up_fd);
            restart = true;
            fprintf(stderr, "up: waiting for restart false...\n");
            // wait for downstream to see restart and close its file descriptor
            while (restart)
                usleep(100000);
            fprintf(stderr, "up: ok\n");
            // downstream is now reopening its file descriptor
            up_fd = serial_setup(O_WRONLY);
            if (up_fd < 0)
                exit(1);
            printf("new up_fd=%d\n", up_fd);
            fds[0].fd = up_fd;
            continue;
        }

        num_bytes = write(up_fd, &msg, msg_bytes);

        tot_bytes += num_bytes;

        if (num_bytes < msg_bytes)
        {
            fprintf(stderr, "write: returned %d at tot_bytes=%d\n", num_bytes, tot_bytes);
            sleep(1);
            continue;
        }

#define PRINT_COUNT 5000
        if (tot_bytes >= PRINT_COUNT)
        {
            printf("sent %d bytes\n", PRINT_COUNT);
            tot_bytes -= PRINT_COUNT;
        }

    } // while (1)

} // main
