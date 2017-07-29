#ifndef _TELEM_CLIENT_H
#define _TELEM_CLIENT_H

#include "../mavlink/c_library/ardupilotmega/mavlink.h"
#include <sys/select.h>
#include "INIReader.h"

class Telem_Client
{
public:
    Telem_Client(uint8_t *recv_buf, uint32_t recv_buflen)
        : _recv_buf(recv_buf), _recv_buflen(recv_buflen)
    {
    }

    virtual void pack_select_fds(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err,
                                 uint8_t &nfds) = 0;
    virtual void configure(INIReader *config) = 0;
    virtual void handle_select_fds(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err,
                                   uint8_t &nfds) = 0;

    virtual void init() = 0;

    virtual void do_writer_sends() = 0;
    virtual bool send_message(const mavlink_message_t &message) = 0;
    virtual bool any_data_to_send() = 0;

    virtual uint32_t send_buffer_space_free();
    virtual uint32_t send_buffer_used();

    uint32_t _send_buf_start = 0;
    uint32_t _send_buf_stop = 0;

    // FIXME: scope
    uint8_t *_recv_buf;    // receive buffer
    uint32_t _recv_buflen; // receive buffer len
    uint32_t _recv_buflen_content = 0;

    virtual uint32_t send_buf_size() const = 0;

private:
};

#endif
