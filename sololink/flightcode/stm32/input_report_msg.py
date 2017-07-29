
import struct

"""
Input Report message as received from the controller's input report message
server. All fields are little-endian.

Start
Byte    Size    Description
0       4       Message ID = 2003
4       4       Length (bytes following)
8       8       Timestamp, usec since epoch
16      2       Gimbal Y
18      2       Gimbal Rate
20      2       Battery
22      2       Spare
24 (packet length)

The timestamp is in microseconds since the Unix epoch. Note that it is set
when the message is first created on the controller, whose time is not
synchronized to anything in particular. At the moment it is only useful if
comparing timestamps to each other.
"""

SOLO_MESSAGE_INPUT_REPORT = 2003

LENGTH = 24


def unpack(s):
    if len(s) != LENGTH:
        return None
    (msg_id, length, timestamp, gimbal_y, gimbal_rate, battery, spare) = \
            struct.unpack("<IIQHHHH", s)
    return (msg_id, timestamp, gimbal_y, gimbal_rate, battery)


# Reads message from stream and returns it.
#   's' is expected to be a stream-oriented socket
#   returned message is tuple:
#     (msg_id, timestamp, gimbal_y, gimbal_rate, battery)

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
        if len(msg_buf) > 0 and len(msg_buf) < LENGTH:
            msg_buf_short = len(msg_buf)
        elif len(msg_buf) > LENGTH:
            msg_buf_long = len(msg_buf)
        # got enough data yet?
        if len(msg_buf) >= LENGTH:
            # use the first LENGTH bytes in the buffer
            msg = msg_buf[:LENGTH]
            msg_buf = msg_buf[LENGTH:]
            return unpack(msg)
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
