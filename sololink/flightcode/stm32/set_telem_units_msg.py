#!/usr/bin/env python

import socket

# Must match flightcode/stm32 and/or config/sololink.orig
SET_TELEM_UNITS_PORT = 5024

# Send message to STM32 via stm32 process
#
# Message is a single byte: 0=imperial, 1=metric;
# does not have the one-byte packet ID at the start.

def send(msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(msg, ("127.0.0.1", SET_TELEM_UNITS_PORT))
    s.close()

def pack_msg(is_metric):
    if is_metric:
        return chr(1)
    else:
        return chr(0)

def unpack(msg):
    return (ord(msg[0]) != 0)
