#!/usr/bin/env python
import socket
import struct
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
confirm = struct.pack("!BBB", 3, 1, 1)
sock.sendto(confirm, ("127.0.0.1", 5501))
