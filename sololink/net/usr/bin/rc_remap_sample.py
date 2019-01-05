#!/usr/bin/env python

import os
import socket
import threading
import time
from sololink import rc_ipc
from sololink import rc_pkt

# Sample RC remapper. This does the following:
# - detaches the uplink so it does not write packets to shared memory.
# - attaches itself to pixrc so it receives rc packets
# - for each received packet:
#   - change the gimbal channel
#   - write the packet to shared memory (so it goes to pixhawk)

# If the RC uplink stops, the packets received by the remapper will contain
# the throttle failsafe value. Since throttle is passed through unchanged,
# pixhawk will failsafe.

# If the remapper dies, nothing is updating the shared memory. The pixrc
# serial thread now detects this and injects a failsafe to pixhawk (sets
# throttle to zero).


# Read packets from pixrc. Replace the gimbal channel with values slewing
# up and down and output the packet to the shared memory. Sticks go through
# unchanged.
def remap_thread(sock):
    gimbal = 1000
    up = True
    while True:
        s = sock.recv(1000)
        if len(s) == rc_pkt.LENGTH:
            # assume it's RC
            timestamp, sequence, channels = rc_pkt.unpack(s)
            if up:
                gimbal += 10
                if gimbal >= 1520:
                    up = False
            else: # down
                gimbal -= 10
                if gimbal <= 1000:
                    up = True
            #print channels[5], "->", gimbal
            channels[5] = gimbal
            if not rc_ipc.put((timestamp, sequence, channels)):
                print "ERROR returned from rc_ipc.put"
        # end if len(s)...
    # end while True


sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
sock.bind("/tmp/rc_remap." + str(os.getpid()))

remap_id = threading.Thread(target=remap_thread, args=(sock,))
remap_id.daemon = True
remap_id.start()


# Read from standard input and write whatever is received to the pixrc
# command socket. Intercept "start" and "stop" and send command sequences
# to the command socket starting and stopping the remapping.
while True:
    s = raw_input()
    if s == "START" or s == "start":
        rc_ipc.attach()
        # remapper thread is waiting for packets from the cmd socket but
        # none come in because we have not done the "attach" yet
        sock.sendto("detach uplink", "/run/rc_uplink_cmd")
        # at this point nothing is writing to the packet shm
        sock.sendto("attach", "/run/rc_uplink_cmd")
        # now the remapper should be receiving packets on the command socket
        # and for each one received, modifying it and writing it to the shm
    elif s == "STOP" or s == "stop":
        sock.sendto("detach", "/run/rc_uplink_cmd")
        sock.sendto("attach uplink", "/run/rc_uplink_cmd")
        # let the thread finish processing any queued rc packets
        time.sleep(0.1)
        # ...then detach the IPC
        rc_ipc.detach()
    else:
        sock.sendto(s, "/run/rc_uplink_cmd")
