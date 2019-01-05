#!/usr/bin/env python

import socket
import struct

# Must match flightcode/stm32 and/or config/sololink.orig
CONFIG_STICK_AXES_PORT = 5010

# Send message to STM32 via stm32 process
#
# Message is packed stick config data, but does not have the one-byte
# packet ID at the start.
def send(msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(msg, ("127.0.0.1", CONFIG_STICK_AXES_PORT))
    s.close()

def pack_stick(stick_id, direction, expo):
    return struct.pack("<BBBBI", stick_id, direction, expo, 0xff, 0xffffffff)

def unpack(msg):
    x = 0
    rcSticks = []
    for i in range(6):
        rcStick = struct.unpack("<BBBBI", msg[x:x+8])
        x += 8
        rcSticks.append(rcStick)
    return rcSticks
