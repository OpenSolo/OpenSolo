import struct

"""
RC packet sent over network looks as follows. All fields are little-endian.

Start
Byte    Size    Description
0       8       Timestamp, usec since some epoch
8       2       Sequence number
10      2       Channel 1
12      2       Channel 2
14      2       Channel 3
16      2       Channel 4
18      2       Channel 5
20      2       Channel 6
22      2       Channel 7
24      2       Channel 8
26 (packet length)
"""

LENGTH = 26

# Input is binary packet (string)
# Output is tuple (timestamp, sequence, channels[])
def unpack(s):
    if len(s) != LENGTH:
        return None
    ts, seq = struct.unpack("<QH", s[:10])
    ch = []
    for i in range(10, 26, 2):
        ch.extend(struct.unpack("<H", s[i:i+2]))
    return (ts, seq, ch)

# Input is tuple (timestamp, sequence, channels[])
# Output is binary packet (string)
def pack(p):
    if type(p) != tuple or len(p) != 3 or \
        (type(p[0]) != int and type(p[0]) != long) or \
        (type(p[1]) != int and type(p[1]) != long) or \
        type(p[2]) != list or len(p[2]) != 8:
        print "expect tuple, 3:", type(p), len(p)
        print "expect int/long, int/long, list:", type(p[0]), type(p[1]), type(p[2])
        print "expect 8:", len(p[2])
        return None
    s = struct.pack('<QHHHHHHHHH', p[0], p[1],
                    p[2][0], p[2][1], p[2][2], p[2][3],
                    p[2][4], p[2][5], p[2][6], p[2][7])
    return s
