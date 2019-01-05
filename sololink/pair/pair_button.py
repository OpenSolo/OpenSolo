#!/usr/bin/env python

# Run this to simulate pressing the pair button on Solo.

import struct
import sys

button_filename = "/dev/input/event0"
button_error = False
button_file = None

# event is:
#   struct input_event {
#       struct timeval time;
#       unsigned short type;
#       unsigned short code;
#       unsigned int value;
#   };
# time:  8 bytes, not used here
# type:  EV_SYN=0x0000, EV_KEY=0x0001
# code:  KEY_WPS_BUTTON=0x0211
# value: 1 on push, 0 on release
# Fields are little endian.
#
# button push:
# xx xx xx xx xx xx xx xx 01 00 11 02 01 00 00 00
#     type=0x0001 code=0x0211 value=0x00000001
# xx xx xx xx xx xx xx xx 00 00 00 00 00 00 00 00
#     type=0x0000 code=0x0000 value=0x00000000
#
# button release:
# xx xx xx xx xx xx xx xx 01 00 11 02 00 00 00 00
#     type=0x0001 code=0x0211 value=0x00000000
# xx xx xx xx xx xx xx xx 00 00 00 00 00 00 00 00
#     type=0x0000 code=0x0000 value=0x00000000

try:
    f = open(button_filename, "w")
except:
    print "can't open %s for writing" % button_filename
    sys.exit(1)

evt = struct.pack("@QHHi", 0, 0x0001, 0x0211, 1)
f.write(evt)

evt = struct.pack("@QHHi", 0, 0, 0, 0)
f.write(evt)

evt = struct.pack("@QHHi", 0, 0x0001, 0x0211, 0)
f.write(evt)

evt = struct.pack("@QHHi", 0, 0, 0, 0)
f.write(evt)

f.close()
