#!/usr/bin/env python

# Show update status screens: updating system, update complete, update failed

import socket
import struct
import sys

START = 0
SUCCESS = 1
FAIL = 2

# must match flightcode/stm32
UPDATER_PORT = 5019

def send(id):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = struct.pack("!B", id)
    s.sendto(msg, ("127.0.0.1", UPDATER_PORT))
    s.close()

def send_start():
    send(START)

def send_success():
    send(SUCCESS)

def send_fail():
    send(FAIL)

def usage():
    print "usage: updater_msg.py <status>"
    print "        where <status> is one of"
    print "        start   show \"updating system\" screen"
    print "        success show \"update complete\" screen"
    print "        fail    show \"update failed\" screen"

if __name__ == "__main__":
    # one required argument: "start", "success", or "fail"
    if len(sys.argv) != 2:
        usage()
    elif sys.argv[1] == "start":
        send_start()
    elif sys.argv[1] == "success":
        send_success()
    elif sys.argv[1] == "fail":
        send_fail()
    else:
        usage()
