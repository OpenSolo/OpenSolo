#include "INIReader.h"

#include "telem_client.h"

class Telem_Serial : public Telem_Client
{
public:
    Telem_Serial(uint8_t *recv_buf, uint32_t recv_buflen) : Telem_Client(recv_buf, recv_buflen)
    {
    }

    uint32_t handle_read();

    void configure(INIReader *config);
    void init() override;

    void pack_select_fds(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err, uint8_t &nfds);
    void handle_select_fds(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err, uint8_t &nfds);

    bool send_message(const mavlink_message_t &message);

    void open_serial_port();

    void do_writer_sends();

    bool any_data_to_send()
    {
        return _send_buf_start != _send_buf_stop;
    }

private:
    int fd;

    /* send buffer stuff: */
    uint8_t _send_buf[65536]; /* way too big */
    uint32_t send_buf_size() const
    {
        return 65536;
    }

    std::string serialPortName;
    uint32_t serialBaud;
    bool serialFlow;
};
