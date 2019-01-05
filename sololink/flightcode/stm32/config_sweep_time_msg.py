#!/usr/bin/env python

import socket
import struct

# Must match flightcode/stm32 and/or config/sololink.orig
CONFIG_SWEEP_TIME_PORT = 5022

# Send message to STM32 via stm32 process
#
# Message is packed sweep time data, but does not have the one-byte
# packet ID at the start.
def send(msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(msg, ("127.0.0.1", CONFIG_SWEEP_TIME_PORT))
    s.close()

def pack(min_sweep_s, max_sweep_s):
    return struct.pack("<II", min_sweep_s, max_sweep_s)

# returns tuple: (min_sweep_s, max_sweep_s)
def unpack(msg):
    return struct.unpack("<II", msg)
