#!/usr/bin/env python

# Send "app connected" message
# Required artoo 0.7.9 or later.

import socket
import struct
import sys

DISCONNECTED = 0
CONNECTED = 1

# Must match flightcode/stm32
APP_CONNECTED_PORT = 5026

def send(app_connected):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = struct.pack("!B", app_connected)
    s.sendto(msg, ("127.0.0.1", APP_CONNECTED_PORT))
    s.close()

def send_connected():
    send(CONNECTED)

def send_disconnected():
    send(DISCONNECTED)

def usage():
    print "usage: app_connected.py <connected>"
    print "        where <connected> is one of"
    print "        c[onnected]     tell stm32 app is connected"
    print "        d[isconnected]  tell stm32 app is disconnected"

if __name__ == "__main__":
    # one required argument: "c[onnected]" or "d[isconnected]"
    if len(sys.argv) != 2:
        usage()
    elif sys.argv[1][0] == "c":
        send_connected()
    elif sys.argv[1][0] == "d":
        send_disconnected()
    else:
        usage()
