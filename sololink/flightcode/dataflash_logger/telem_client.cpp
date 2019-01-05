#include "telem_client.h"

uint32_t Telem_Client::send_buffer_used()
{
    if (_send_buf_stop >= _send_buf_start) {
        return _send_buf_stop - _send_buf_start;
    }
    return send_buf_size() - _send_buf_start + _send_buf_stop;
}
uint32_t Telem_Client::send_buffer_space_free()
{
    return send_buf_size() - send_buffer_used();
}
