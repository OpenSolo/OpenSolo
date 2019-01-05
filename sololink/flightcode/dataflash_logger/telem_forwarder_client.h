#include "INIReader.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include "telem_client.h"

class Telem_Forwarder_Client : public Telem_Client
{
public:
    Telem_Forwarder_Client(uint8_t *recv_buf, uint32_t recv_buflen)
        : Telem_Client(recv_buf, recv_buflen)
    {
    }

    uint32_t handle_recv();
    void init() override;

    void configure(INIReader *config);
    void pack_select_fds(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err, uint8_t &nfds);
    void handle_select_fds(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err, uint8_t &nfds);

    void do_writer_sends();
    bool send_message(const mavlink_message_t &msg);
    bool any_data_to_send()
    {
        return _send_buf_start != _send_buf_stop;
    }

private:
    int fd_telem_forwarder = -1;

    struct sockaddr_in sa;    // our send-from address
    struct sockaddr_in sa_tf; /* telem_forwarder's address */

    void create_and_bind();
    void pack_telem_forwarder_sockaddr(INIReader *config);
    bool sane_telem_forwarder_packet(uint8_t *pkt, uint16_t bpktlen);

    /* send buffer stuff: */
    mavlink_message_t _send_buf[256]; // way too bug?
    uint32_t send_buf_size() const
    {
        return 256;
    }
};
