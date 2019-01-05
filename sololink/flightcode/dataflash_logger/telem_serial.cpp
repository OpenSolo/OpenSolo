#include "telem_serial.h"

#include "la-log.h"

#include <fcntl.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

#define UNUSED __attribute__((unused))

void Telem_Serial::init()
{
    open_serial_port();
}

void Telem_Serial::pack_select_fds(fd_set &fds_read, fd_set &fds_write UNUSED, fd_set &fds_err,
                                   uint8_t &nfds)
{
    FD_SET(fd, &fds_read);
    FD_SET(fd, &fds_err);

    if (fd >= nfds) {
        nfds = fd + 1;
    }
}

void Telem_Serial::handle_select_fds(fd_set &fds_read, fd_set &fds_write UNUSED, fd_set &fds_err,
                                     uint8_t &nfds UNUSED)
{
    /* check for packets from telem_forwarder */
    if (FD_ISSET(fd, &fds_err)) {
        FD_CLR(fd, &fds_err);
        la_log(LOG_ERR, "select(%d): %s", fd, strerror(errno));
    }

    if (FD_ISSET(fd, &fds_read)) {
        FD_CLR(fd, &fds_read);
        _recv_buflen_content = handle_read();
        // ::fprintf(stderr, "received %u bytes\n", _buflen_content);
    }
}

// from serial_setup in telem_forward
void Telem_Serial::open_serial_port()
{
    fd = open(serialPortName.c_str(), O_RDWR | O_NOCTTY | O_NONBLOCK);

    if (fd < 0) {
        la_log(LOG_ERR, "unable to open serial port %s", serialPortName.c_str());
        abort();
    }

    // Configure port for 8N1 transmission
    struct termios options;

    tcgetattr(fd, &options); // Gets the current options for the port
    // Set the output baud rate
    switch (serialBaud) {
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
        syslog(LOG_ERR, "unsupported baud rate %d", serialBaud);
        return;
    }
    options.c_iflag &= ~(IGNBRK | BRKINT | ICRNL | INLCR | PARMRK | INPCK | ISTRIP | IXON);
    options.c_oflag &= ~(OCRNL | ONLCR | ONLRET | ONOCR | OFILL | OPOST);
    options.c_lflag &= ~(ECHO | ECHONL | ICANON | IEXTEN | ISIG);
    options.c_cflag &= ~(CSIZE | PARENB);
    options.c_cflag |= (CS8 | CLOCAL);

    if (serialFlow) {
        options.c_cflag |= CRTSCTS; // hardware flow control
    } else {
        options.c_cflag &= ~(CRTSCTS); // no hardware flow control
    }

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
    if (serialBaud <= 115200) {
        options.c_cc[VMIN] = 10;
    } else {
        options.c_cc[VMIN] = 1;
    }
    options.c_cc[VTIME] = 0;

    tcsetattr(fd, TCSANOW, &options); // Set the new options for the port "NOW"

    la_log(LOG_INFO, "opened serial port %s", serialPortName.c_str());

    return;
}

uint32_t Telem_Serial::handle_read()
{
    ssize_t res = read(fd, _recv_buf, _recv_buflen);
    if (res == -1) {
        la_log(LOG_INFO, "Failed read: %s", strerror(errno));
    }

    return res;
}

void Telem_Serial::configure(INIReader *config)
{
    serialPortName = config->Get("solo", "telemDev", "/dev/ttymxc1");
    serialBaud = config->GetInteger("solo", "telemBaud", 57600);
    serialFlow = config->GetBoolean("solo", "telemFlow", true);
}

void Telem_Serial::do_writer_sends()
{
    while (_send_buf_start != _send_buf_stop) { // FIXME: use file descriptors!
        bool tail_first = false;
        if (_send_buf_stop < _send_buf_start) {
            tail_first = true;
        }
        uint32_t bytes_to_send =
            tail_first ? (send_buf_size() - _send_buf_start) : (_send_buf_stop - _send_buf_start);

        int32_t sent = ::write(fd, (const char *)&_send_buf[_send_buf_start], bytes_to_send);
        if (sent < 0) {
            // cry
            break;
        } else if (sent == 0) {
            break;
        } else {
            _send_buf_start += sent;
            if (_send_buf_start == send_buf_size()) {
                _send_buf_start = 0;
            }
        }
    }
}

bool Telem_Serial::send_message(const mavlink_message_t &msg)
{
    char sendbuf[1024]; // large enough...

    uint16_t messageLen = mavlink_msg_to_send_buffer((uint8_t *)sendbuf, &msg);
    if (send_buffer_space_free() < messageLen) {
        // dropped_packets++;
        return false;
    }
    if (_send_buf_stop >= _send_buf_start) {
        uint16_t to_copy = send_buf_size() - _send_buf_stop;
        if (to_copy > messageLen) {
            to_copy = messageLen;
        }
        memcpy(&_send_buf[_send_buf_stop], sendbuf, to_copy);
        _send_buf_stop += to_copy;
        if (_send_buf_stop >= send_buf_size()) {
            _send_buf_stop = 0;
        }
        to_copy = messageLen - to_copy;
        if (to_copy) {
            memcpy(&_send_buf[_send_buf_stop], &sendbuf[messageLen - to_copy], to_copy);
            _send_buf_stop += to_copy;
            if (_send_buf_stop >= send_buf_size()) {
                _send_buf_stop = 0;
            }
        }
    } else {
        memcpy(&_send_buf[_send_buf_stop], &sendbuf[0], messageLen);
        _send_buf_stop += messageLen;
        if (_send_buf_stop >= send_buf_size()) {
            _send_buf_stop = 0;
        }
    }
    return true;
}
