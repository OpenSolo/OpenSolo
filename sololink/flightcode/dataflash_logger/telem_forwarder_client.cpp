#include "telem_forwarder_client.h"

#include <string.h>
// #include <sys/socket.h>
// #include <netinet/in.h>
// #include <arpa/inet.h>

#include "la-log.h"

#define UNUSED __attribute__((unused))

void Telem_Forwarder_Client::pack_select_fds(fd_set &fds_read, fd_set &fds_write UNUSED,
                                             fd_set &fds_err, uint8_t &nfds)
{
    FD_SET(fd_telem_forwarder, &fds_read);
    FD_SET(fd_telem_forwarder, &fds_err);

    if (fd_telem_forwarder >= nfds) {
        nfds = fd_telem_forwarder + 1;
    }
}

void Telem_Forwarder_Client::handle_select_fds(fd_set &fds_read, fd_set &fds_write UNUSED,
                                               fd_set &fds_err, uint8_t &nfds UNUSED)
{
    /* check for packets from telem_forwarder */
    if (FD_ISSET(fd_telem_forwarder, &fds_err)) {
        FD_CLR(fd_telem_forwarder, &fds_err);
        la_log(LOG_ERR, "select(fd_telem_forwarder): %s", strerror(errno));
    }

    if (FD_ISSET(fd_telem_forwarder, &fds_read)) {
        FD_CLR(fd_telem_forwarder, &fds_read);
        _recv_buflen_content = handle_recv();
        // ::fprintf(stderr, "received %u bytes\n", _buflen_content);
    }
}

/*
* create_and_bind - create a socket and bind it to a local UDP port
*
* Used to create the socket on the upstream side that receives from and sends
* to telem_forwarder
*
* Returns fd on success, -1 on error.
*/
void Telem_Forwarder_Client::create_and_bind()
{
    int fd;
    struct sockaddr_in sa;

    fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        perror("socket");
        abort();
    }

    memset(&sa, 0, sizeof(sa));
    sa.sin_family = AF_INET;
    sa.sin_addr.s_addr = htonl(INADDR_ANY);
    sa.sin_port = 0; // we don't care what our port is

    if (bind(fd, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
        perror("bind");
        abort();
    }

    fd_telem_forwarder = fd;
} /* create_and_bind */

void Telem_Forwarder_Client::pack_telem_forwarder_sockaddr(INIReader *config)
{
    // uint16_t tf_port = config->GetInteger("solo", "telem_forward_port", 14560);
    // std::string ip = config->Get("solo", "soloIp", "10.1.1.10");
    uint16_t tf_port = config->GetInteger("solo", "telem_forward_port", 14560);
    std::string ip = config->Get("solo", "soloIp", "127.0.0.1");

    la_log(LOG_INFO, "df-tfc: connecting to telem-forwarder at %s:%u", ip.c_str(), tf_port);
    memset(&sa_tf, 0, sizeof(sa_tf));
    sa_tf.sin_family = AF_INET;
    //    sa_tf.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    inet_aton(ip.c_str(), &sa_tf.sin_addr); // useful for debugging
    sa_tf.sin_port = htons(tf_port);
}

bool Telem_Forwarder_Client::sane_telem_forwarder_packet(uint8_t *pkt, uint16_t pktlen)
{
    if (sa.sin_addr.s_addr != sa_tf.sin_addr.s_addr) {
        la_log(LOG_ERR, "received packet not from solo (0x%08x)", sa.sin_addr.s_addr);
        return false;
    }
    if (pktlen < 8) {
        la_log(LOG_ERR, "received runt packet (%d bytes)", pktlen);
        return false;
    }
    if (pkt[0] != 0xFE && pkt[0] != 0xFD) {
        la_log(LOG_ERR, "received bad magic (0x%02x)", pkt[0]);
        return false;
    }
    return true;
}

uint32_t Telem_Forwarder_Client::handle_recv()
{
    // ::printf("Receiving packet into position %u\n", _buflen_content);
    /* packet from telem_forwarder */
    socklen_t sa_len = sizeof(sa);
    uint16_t res =
        recvfrom(fd_telem_forwarder, &_recv_buf[_recv_buflen_content],
                 _recv_buflen - _recv_buflen_content, 0, (struct sockaddr *)&sa, &sa_len);

    /* We get one mavlink packet per udp datagram. Sanity checks here
       are: must be from solo's IP and have a valid mavlink header. */
    // FIXME: we don't necessarily get just one packet/buffer!
    // ::fprintf(stderr, "handle_recv\n");
    if (!sane_telem_forwarder_packet(_recv_buf, res)) {
        return 0;
    }

    return res;
}

bool Telem_Forwarder_Client::send_message(const mavlink_message_t &msg)
{
    if (send_buffer_space_free() < 1) {
        // dropped_packets++;
        return false;
    }
    memcpy(&_send_buf[_send_buf_stop++], (char *)&msg, sizeof(msg));
    if (_send_buf_stop >= send_buf_size()) {
        _send_buf_stop = 0;
    }
    return true;
}

void Telem_Forwarder_Client::do_writer_sends()
{
    char buf[1024]; // large enough...

    while (_send_buf_start != _send_buf_stop) {
        mavlink_message_t &msg = _send_buf[_send_buf_start];
        uint16_t messageLen = mavlink_msg_to_send_buffer((uint8_t *)buf, &msg);

        int32_t bytes_sent = sendto(fd_telem_forwarder, buf, messageLen, 0,
                                    (struct sockaddr *)&sa_tf, sizeof(struct sockaddr));
        if (bytes_sent == -1) {
            la_log(LOG_INFO, "Failed sendto: %s", strerror(errno));
            // we drop the message anyway!
        }
        _send_buf_start++;
        if (_send_buf_start >= send_buf_size()) {
            _send_buf_start = 0;
        }
    }

    return;
}

void Telem_Forwarder_Client::configure(INIReader *config)
{
    /* prepare sockaddr used to contact telem_forwarder */
    pack_telem_forwarder_sockaddr(config);
}

void Telem_Forwarder_Client::init()
{
    /* Prepare a port to receive and send data to/from telem_forwarder */
    /* does not return on failure */
    create_and_bind();
}
