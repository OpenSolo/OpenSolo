#!/usr/bin/env python

import sys, os, struct, datetime
import serial, slip

ARTOO_BAUD = 115200
SOLO_NAME = "SOLOLINK_12345"
SOLO_NAME_LONG = "mock vehicle with a name that is just waaaaaaaaaaaaaaay too lonnnnnnnnggggggggggg"

ARTOO_SYSINFO_ID        = chr(0x3)
ARTOO_PAIR_REQUEST_ID   = chr(0x7)
ARTOO_PAIR_CONFIRM_ID   = chr(0x8)
ARTOO_PAIR_RESULT_ID    = chr(0x9)
ARTOO_STORED_PARAMS_ID  = chr(0xb)

def mainloop(serialpath):

    serialport = serial.Serial(serialpath, ARTOO_BAUD)
    slipdev = slip.SlipDevice(serialport)

    msg = "".join([ARTOO_PAIR_REQUEST_ID, SOLO_NAME, chr(0)])
    slipdev.write(msg)

    t = datetime.datetime.now()

    while True:
        pkt = slipdev.read()
        if pkt[0] == ARTOO_PAIR_CONFIRM_ID:
            print "pair confirmed", len(pkt[1:]), pkt[1:]
            payload = [ARTOO_PAIR_RESULT_ID]
            payload.extend(pkt[1:])
            slipdev.write("".join(payload))
            break

        dt = datetime.datetime.now() - t
        if dt.seconds > 10:
            print "timeout"
            slipdev.write("".join([ARTOO_PAIR_RESULT_ID, chr(0)]))
            break

    while True:
        slipdev.write("".join([ARTOO_STORED_PARAMS_ID]))
        pkt = slipdev.read()
        pkt = "".join(pkt)
        if pkt[0] == ARTOO_STORED_PARAMS_ID:
            break

    print "pairing complete."

#
# main
#

if len(sys.argv) < 2:
    print "usage: pair.py /dev/ttyMyDev"
    sys.exit(1)

mainloop(sys.argv[1])
