
import struct

"""
Button Message as received from the controller's button message server.

Start
Byte    Size    Description
0       8       Timestamp, usec since epoch
8       1       Button ID
9       1       Button event
10      2       Buttons-pressed mask
12 (packet length)

The buttons-pressed mask indicates all of the buttons that are pressed at
the time of the event, e.g. if it is 0x0012, then the "A" (1 << 4 = 0x0010)
and "Fly" (1 << 1 = 0x0002) buttons are pressed.

The timestamp is in microseconds since the Unix epoch. Note that it is set
when the message is first created on the controller, whose time may not be
synchronized to anything in particular. At the moment it is only useful when
comparing event timestamps to each other.
"""

LENGTH = 12

# Button IDs
# match artoo/src/io.h and SoloLink/flightcode/stm32/ButtonEventHandler.h
ButtonPower = 0
ButtonFly = 1
ButtonRTL = 2
ButtonLoiter = 3
ButtonA = 4
ButtonB = 5
ButtonPreset1 = 6
ButtonPreset2 = 7
ButtonCameraClick = 8
# index of each name expected to match IDs above
ButtonName = ["Power", "Fly", "RTL", "Loiter", "A", "B",
              "Preset1", "Preset2", "CameraClick"]

# Button Events
# match artoo/src/button.h and SoloLink/flightcode/stm32/ButtonEventHandler.h
Press =  0
Release = 1
ClickRelease = 2
Hold = 3
LongHold = 4
DoubleClick = 5
# index of each name expected to match events above
EventName = ["Press", "Release", "ClickRelease",
             "Hold", "LongHold", "DoubleClick"]


# packet type ids
# starting these at 2000 to avoid any collisions with app_packet,
# even though they are different connections so it won't matter
ARTOO_MSG_BUTTON_EVENT = 2000
ARTOO_MSG_SET_BUTTON_STRING = 2001
ARTOO_MSG_SET_SHOT_STRING = 2002

# values for bitmask to send to Artoo
ARTOO_BITMASK_ENABLED = 1
ARTOO_BITMASK_HIGHLIGHTED = 2


# Returns tuple:
#   (timestamp_us, button_id, button_event, pressed_mask)
def unpack(s):
    if len(s) != LENGTH:
        return None
    return struct.unpack("<QBBH", s)


# Reads message from stream and returns it.
#   's' is expected to be a stream-oriented socket
#   returned message is tuple:
#     (timestamp_us, button_id, button_event, pressed_mask)

# Buffer for accumulated data. It has been observed that we can get multiple
# events in the same socket read. It is possible that we could get a message
# split across two socket reads (although that has not been observed).
msg_buf = ""

# Debug flags
msg_buf_short = 0   # if nonzero, have seen msg_buf with this many bytes
msg_buf_long = 0    # if nonzero, have seen msg_buf with this many bytes

def recv(s):
    global msg_buf
    global msg_buf_short
    global msg_buf_long
    while True:
        # debug
        if len(msg_buf) > 0 and len(msg_buf) < 12:
            msg_buf_short = len(msg_buf)
        elif len(msg_buf) > 12:
            msg_buf_long = len(msg_buf)
        # got enough data yet?
        if len(msg_buf) >= 12:
            # return the first 12 bytes in the buffer
            msg = msg_buf[:12]
            msg_buf = msg_buf[12:]
            return struct.unpack("<QBBH", msg)
        else:
            # not enough yet; wait for more
            data = s.recv(1024)
            if data is None:
                # this case has not been observed to happen
                continue
            elif data == "":
                # this happens if the other end closes
                return None
            else:
                # append it to what we have then loop back and check for
                # complete message
                msg_buf = msg_buf + data
        # end if
    # end while

# Sends a button string to Artoo
# in the format (little-endian):
# Message ID : 4 bytes
# Length:  N (4 bytes)
# Button ID: unsigned char
# Button event: unsigned char
# shot ID:  signed char (-1 for none)
# bitmask: char :
#       Lowest bit is "enabled" where "disabled" is greyed out on Artoo
#       2nd lowest bit is "lit up"
# string descriptor:  n bytes
def sendArtooString(s, button_id, shot, mask, artooStr):
    length = 4 + len(artooStr)
    packstr = "<IIBBbb%ds"%(len(artooStr),)
    pkt = struct.pack(packstr, ARTOO_MSG_SET_BUTTON_STRING, length, button_id, 
            Press, shot, mask, artooStr)
    s.send(pkt)

# Sends a shot string to Artoo 
# in the format (little-endian):
# Message ID : 4 bytes
# Length:  N (4 bytes)
# string descriptor:  n bytes
def sendShotString(s, shotStr):
    length = len(shotStr)
    packstr = "<II%ds"%(len(shotStr),)
    pkt = struct.pack(packstr, ARTOO_MSG_SET_SHOT_STRING, length, shotStr)
    s.send(pkt)
