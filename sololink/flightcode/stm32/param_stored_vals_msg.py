#!/usr/bin/env python

# Send PARAM_STORED_VALS message
#
# The request is the message ID only
# The response is a complex structure (not handled here)

##import datetime
import socket
import struct
import sys
import pprint

# must match flightcode/stm32
PARAM_STORED_VALS_PORT = 5011

def send():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto("", ("127.0.0.1", PARAM_STORED_VALS_PORT))
    s.close()

##max_delay = 0.0

# send request, wait for response
def fetch():
    ##global max_delay
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Most of the time we get a response in <17 msec.
    # In one run of 10,000 fetches, the longest delay was <82 msec.
    s.settimeout(0.2)
    # send request
    ##start_time = datetime.datetime.now()
    s.sendto("", ("127.0.0.1", PARAM_STORED_VALS_PORT))
    # wait for response
    try:
        msg = s.recv(256)
    except:
        msg = ""
    ##else:
    ##    delta_time = datetime.datetime.now() - start_time
    ##    delta_time = delta_time.total_seconds()
    ##    if max_delay < delta_time:
    ##        max_delay = delta_time
    ##    print "response in %f sec" % (delta_time, )
    s.close()
    return msg

# parse string msg to dictionary
#
# {
#   'stickCals' : [ stickCal0, ... stickCal5 ],
#   'presets' : [ preset0, preset1 ],
#   'rcSticks' : [ rcStick0, ... rcStick5 ],
#   'buttonConfigs' : [ buttonConfig0, ... buttonConfig2 ],
#   'sweepConfig' : [ sweepConfig0 ]
# }
#
# stickCalN =
# (
#   <int>,      # minVal
#   <int>,      # trim
#   <int>       # maxVal
# )
# presetN =
# (
#   <float>
# )
# rcStickN =
# (
#   <int>,      # input
#   <int>,      # direction
#   <int>       # expo
# )
# buttonConfigN =
# (
#   <int>,      # buttonID
#   <int>,      # buttonEvt
#   <int>,      # shotID
#   <int>,      # state
#   <string>    # descriptor
# )
# sweepConfigN =
# (
#   <int>,      # minSweepSec
#   <int>       # maxSweepSec
# )
def unpack(msg):
    x = 0

    stickCals = []
    for i in range(6):
        stickCal = struct.unpack("<HHH", msg[x:x+6])
        x += 6
        stickCals.append(stickCal)

    presets = []
    for i in range(2):
        preset = struct.unpack("<f", msg[x:x+4])
        x += 4
        presets.append(preset)

    rcSticks = []
    for i in range(6):
        rcStick = struct.unpack("<BBBBI", msg[x:x+8])
        x += 8
        rcSticks.append(rcStick)

    buttonConfigs = []
    for i in range(3):
        buttonConfig = struct.unpack("<BBbB20s", msg[x:x+24])
        x += 24
        # clean up the string (last element in tuple)
        buttonConfig = ( buttonConfig[0],
                         buttonConfig[1],
                         buttonConfig[2],
                         buttonConfig[3],
                         buttonConfig[4].partition("\0")[0] )
        buttonConfigs.append(buttonConfig)

    sweepConfigs = []
    for i in range(1):
        sweepConfig = struct.unpack("<II", msg[x:x+8])
        x += 8
        sweepConfigs.append(sweepConfig)

    return { 'stickCals' : stickCals,
             'presets' : presets,
             'rcSticks' : rcSticks,
             'buttonConfigs' : buttonConfigs,
             'sweepConfigs' : sweepConfigs }


def usage():
    print "usage: param_stored_vals_msg.py"


if __name__ == "__main__":
    # no arguments
    if len(sys.argv) != 1:
        usage()
    else:
        msg = fetch()
        msg = unpack(msg)
        pprint.PrettyPrinter().pprint(msg)
        ##for i in range(10000):
        ##    fetch()
        ##print "max_delay = %f" % max_delay
