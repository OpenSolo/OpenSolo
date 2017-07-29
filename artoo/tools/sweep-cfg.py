#!/usr/bin/env python

import sys, os, struct, datetime
import serial, slip

from msg_id import MsgID

ARTOO_BAUD = 115200

def mainloop(serialpath):

    serialport = serial.Serial(serialpath, ARTOO_BAUD)
    slipdev = slip.SlipDevice(serialport)
    
    FORMAT_ID = '<B'
    FORMAT_SWEEP_TIME = 'II'

    config_sweep_id = MsgID.index('ConfigSweepTime')
    MIN_SWEEP_DEFAULT = 0
    MAX_SWEEP_DEFAULT = 90

    s = struct.pack("".join([FORMAT_ID,FORMAT_SWEEP_TIME]), config_sweep_id, MIN_SWEEP_DEFAULT, MAX_SWEEP_DEFAULT)

    print "[sweep-cfg] Serial write returned: ", slipdev.write(s)

#
# main
#

if len(sys.argv) < 2:
    print "usage: sweep-cfg.py /dev/ttyMyDev"
    sys.exit(1)

mainloop(sys.argv[1])
