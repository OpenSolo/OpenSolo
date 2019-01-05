#include "mavlink_writer.h"

#include <algorithm>

void MAVLink_Writer::add_client(Telem_Client *client)
{
    clients.push_back(client);
}

void MAVLink_Writer::send_message(const mavlink_message_t &msg)
{
    // std::for_each(clients.begin(), clients.end(), send_message(msg));
    std::for_each(clients.begin(), clients.end(), [msg](Telem_Client *c) { c->send_message(msg); });
    // for (std::vector<Telem_Client *>::iterator it = clients.begin();
    //      it != clients.end();
    //      it++) {
    //     (*it)->send_message(msg);
    // }
}

bool MAVLink_Writer::any_data_to_send()
{
    for (std::vector< Telem_Client * >::iterator it = clients.begin(); it != clients.end(); it++) {
        if ((*it)->any_data_to_send()) {
            return true;
        }
    }
    return false;
}
