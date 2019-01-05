#!/usr/bin/python

# This uses the above '#!' instead of '#!/usr/bin/env python' so that the
# busybox 'pidof' can find this process by name.

import ConfigParser
import logging
import logging.config
import optparse
import os
import socket
import struct
import sys
sys.path.append("/usr/bin")
import app_connected_msg

solo_conf = "/etc/sololink.conf"

# items read from solo_conf
app_server_port = 0
app_address_file = ""



def get_request(sock):
    """get one request from socket

    A request is a 32-bit byte count followed by opaque data. The byte count
    includes itself, i.e. the minimum byte count is four. The request is
    returned as a string, with the initial byte count still included. The
    purpose of "requests" at this level is really to just provide for reliable
    datagrams over TCP.
    """

    # Read byte count
    # XXX This is inefficient but simple; we never want to read beyond the end
    # of the request we are receiving, to avoid needing to save state between
    # calls to get_request.
    pkt = ""
    while len(pkt) < 4:
        try:
            b = sock.recv(1)
        except socket.error as se:
            # Android app: disconnect wifi without closing app and you get:
            # socket.error: [Errno 110] Connection timed out
            logger.info("socket.error: %s", str(se))
            return None
        except socket.timeout as st:
            # Has not been observed to happen.
            logger.info("socket.timeout: %s", str(st))
            return None
        if not b:
            return None
        pkt += b

    (pkt_len, ) = struct.unpack("!I", pkt)

    logger.debug("packet length %d", pkt_len)

    # Read the rest of the packet
    # XXX Super-inefficient. Don't read beyond the end of the current packet.
    while len(pkt) < pkt_len:
        try:
            b = sock.recv(1)
        except socket.error as se:
            logger.info("socket.error: %s", str(se))
            return None
        except socket.timeout as st:
            logger.info("socket.timeout: %s", str(st))
            return None
        if not b:
            return None
        pkt += b

    return pkt



def set_app_ip(app_ip):
    f = open(app_address_file, "w")
    f.write(app_ip + "\n")
    f.close()



def unset_app_ip():
    # allow it to not exist (unlink fails)
    try:
        os.unlink(app_address_file)
    except:
        pass



# app server connection loop
def app_server():

    # socket we will use to listen for connections
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    # After 1 second, start KEEPALIVE
    listen_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
    # 5 seconds in between keepalive pings
    listen_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
    # 5 max fails
    listen_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
    listen_sock.bind(("", app_server_port))

    # only allow one connection
    listen_sock.listen(0)

    while True:

        logger.info("waiting for connection")

        # wait for connection
        (sock, address) = listen_sock.accept()

        logger.info("connection from %s", str(address))

        set_app_ip(address[0])
        logger.info("app IP is %s", address[0])

        app_connected_msg.send_connected()

        # process requests from the client
        while True:
            # Get one request. We don't yet use these; it is the existence of
            # the connection that is meaningful.
            pkt = get_request(sock)
            if not pkt:
                # Remote end closed the connection
                break
            logger.info("received request: %s", str([hex(ord(x)) for x in pkt]))
        ### end while True

        app_connected_msg.send_disconnected()

        unset_app_ip()

        logger.info("closing connection")
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except socket.error as se:
            # Android app: disconnect wifi without closing app and you get:
            # socket.error: [Errno 107] Transport endpoint is not connected
            logger.info("socket.error: %s", str(se))
        except socket.timeout as st:
            # Has not been observed to happen.
            logger.info("socket.timeout: %s", str(st))
        sock.close()

    ### end while True

### end app_server()



if __name__ == "__main__":

    logging.config.fileConfig(solo_conf)
    logger = logging.getLogger("app")

    logger.info("starting")

    config = ConfigParser.SafeConfigParser()

    # if the config file is not found, and empty list is returned and the
    # "get" operations later fail
    config.read(solo_conf)

    # read configuration items
    try:
        app_server_port = config.getint("solo", "appServerPort")
        app_address_file = config.get("solo", "appAddressFile")
    except:
        logger.error("error reading config from %s", solo_conf)
        sys.exit(1)

    parser = optparse.OptionParser("app_server [options]")

    (opts, args) = parser.parse_args()

    app_server()
    # app_server never returns
