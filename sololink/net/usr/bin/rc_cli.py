#!/usr/bin/env python

import os
import socket
import threading
from sololink import rc_pkt

def in_thread(sock):
    while True:
        pkt = sock.recv(1000)
        if len(pkt) == rc_pkt.LENGTH:
            # assume it's RC
            timestamp, sequence, channels = rc_pkt.unpack(pkt)
            pkt = "%d %d %d %d %d %d %d %d %d %d" % \
                (timestamp, sequence,
                 channels[0], channels[1], channels[2], channels[3],
                 channels[4], channels[5], channels[6], channels[7])
        print pkt

sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
sock.bind("/tmp/rc_cli." + str(os.getpid()))

in_id = threading.Thread(target=in_thread, args=(sock,))
in_id.daemon = True
in_id.start()

while True:
    s = raw_input()
    sock.sendto(s, "/run/rc_uplink_cmd")
