
#include <syslog.h>
#include <errno.h>
#include <unistd.h>
#include <stddef.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <iostream>
#include "RcCommander.h"

using namespace std;

// Handle ATTACH or DETACH command.
//
// This overrides Commander::handle_attach() to allow for attaching/detaching
// the RC uplink. If the optional argument does not specify the uplink (or is
// not present), Commander::handle_attach() is called to take care of things.
void RcCommander::handle_attach(const struct sockaddr *src_addr, socklen_t src_addr_len,
                                const char *client, bool attach)
{

    // If the optional argument is not present or does not specify the uplink
    // Commander::handle_attach() is called to take care of things.
    if (client == NULL || strcasecmp(client, "UPLINK") != 0) {
        Commander::handle_attach(src_addr, src_addr_len, client, attach);
    } else {
        // Attach/detach the uplink
        uplink_attached = attach;

        if (uplink_attached)
            syslog(LOG_INFO, "cmd: uplink attached");
        else
            syslog(LOG_INFO, "cmd: uplink detached");

        send_response(src_addr, src_addr_len, "OK\n");
    }

} // RcCommander::handle_attach
