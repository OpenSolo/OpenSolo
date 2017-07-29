#!/usr/bin/env python

# Show/hide "update required" screen.
# Required artoo 0.7.0 or later.

import socket
import struct
import sys

UNLOCK = 0
LOCK = 1

# Must match flightcode/stm32
LOCKOUT_STATE_PORT = 5020

def send(lock_state):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = struct.pack("!B", lock_state)
    s.sendto(msg, ("127.0.0.1", LOCKOUT_STATE_PORT))
    s.close()

def send_lock():
    send(LOCK)

def send_unlock():
    send(UNLOCK)

def usage():
    print "usage: lockout_msg.py <lockout>"
    print "        where <lockout> is one of"
    print "        lock    show \"update required\" screen"
    print "        unlock  hide \"update required\" screen"

if __name__ == "__main__":
    # one required argument: "lock" or "unlock"
    if len(sys.argv) != 2:
        usage()
    elif sys.argv[1] == "lock":
        send_lock()
    elif sys.argv[1] == "unlock":
        send_unlock()
    else:
        usage()
