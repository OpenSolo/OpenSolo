
import struct

"""
Pair Request/Confirm message sent between pairing and stm32 modules.

Start
Byte    Size    Description
0       4       ID (not used)
4       4       Length following (56)
8       4       Flags
12      20      MAC address, ASCII string (e.g. "02:1F:09:03:00:08")
32      32      Friendly name (e.g. "Solo Mynis")
64 (total packet length)
"""

MAC_LENGTH = 20
NAME_LENGTH = 32
BODY_LENGTH = 56
TOTAL_LENGTH = 64

FLAGS_REQUEST = 1
FLAGS_CONFIRM = 2
FLAGS_RESULT = 3

fmt_string = "<III%ds%ds" % (MAC_LENGTH, NAME_LENGTH)

MSG_ID = 0

# struct.pack/unpack and strings
#
# struct.pack will truncate the string to fit in the specified length, or pad
# it with \0 bytes to the specified length, e.g.
#   struct.pack("3s", "Hello") -> "Hel"
#   struct.pack("8s", "Hello") -> "Hello\0\0\0"
#
# struct.unpack will return a string of exactly the specified length, e.g.
#   struct.unpack("8s", "Hello\0\0\0") -> "Hello\0\0\0"

def unpack(s):
    if len(s) != TOTAL_LENGTH:
        return None
    hdr_id, hdr_len, mac, name, flags = struct.unpack(fmt_string, s)
    mac = mac.strip("\0")
    name = name.strip("\0")
    return mac, name, flags

def pack(mac, name, flags=0):
    # truncate MAC and Name if necessary so packed strings are \0 terminated
    if len(mac) > (MAC_LENGTH - 1):
        mac = mac[:(MAC_LENGTH - 1)]
    if len(name) > (NAME_LENGTH - 1):
        name = name[:(NAME_LENGTH - 1)]
    return struct.pack(fmt_string, MSG_ID, BODY_LENGTH, mac, name, flags)
