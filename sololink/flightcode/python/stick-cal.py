#!/usr/bin/env python

import sys, os, struct
import serial, slip

ARTOO_BAUD = 115200

ARTOO_RAW_IO_ID         = chr(0x5)
ARTOO_RAW_IO_REPORT_ID  = chr(0x6)
ARTOO_SYSINFO_ID        = chr(0x3)
ARTOO_CALIBRATE_ID      = chr(0x2)
ARTOO_DSM_ID            = chr(0x1)

class Axis():
    def __init__(self):
        self.min = sys.maxint
        self.trim = 0
        self.max = 0
        self.current = 0

    def update(self, val):
        self.min = min(self.min, val)
        self.max = max(self.max, val)
        self.current = val

    def extremes(self):
        return "%04d:%04d" % (self.min, self.max)
    
    def vals(self):
        return [self.min, self.trim, self.max]

    def latch_trim(self):
        self.trim = self.current

def get_and_print_sysinfo(slipdev):
    while True:
        slipdev.write("".join([ARTOO_SYSINFO_ID]))
        pkt = slipdev.read()
        pkt = "".join(pkt)
        if pkt[0] == ARTOO_SYSINFO_ID:
            uid = "".join(["{:02x}".format(ord(c)) for c in pkt[:12]])
            hw_version = struct.unpack_from('<H', pkt, 12)[0]
            sw_version = pkt[14:]
            print "calibrating artoo (UID: %s, hw version %d, sw version %s)" % (uid, hw_version, sw_version)
            return


def mainloop(serialpath):

    serialport = serial.Serial(serialpath, ARTOO_BAUD)
    slipdev = slip.SlipDevice(serialport)

    axes = [Axis() for n in range(6)]
    get_and_print_sysinfo(slipdev)

    try:
        # enter raw io mode
        slipdev.write("".join([ARTOO_RAW_IO_ID, chr(1)]))

        while True:
            pkt = slipdev.read()
            if pkt[0] == ARTOO_RAW_IO_REPORT_ID:
                # XXX: this will only work for BB03 hw or later at the moment.
                #      too lazy to switch based on hw version...
                vals = struct.unpack("<HHHHHHHHHHHH", "".join(pkt[1:]))
                for i, v in enumerate(vals[:len(axes)]):
                    axes[i].update(v)

                print(("throttle: %s, roll %s, pitch %s, yaw %s cam pitch %s, cam rate %s\r") % (axes[0].extremes(), axes[1].extremes(), axes[2].extremes(), axes[3].extremes(), axes[4].extremes(), axes[5].extremes())),
                sys.stdout.flush();

    except KeyboardInterrupt:
        pass

    vals = []
    for a in axes:
        a.latch_trim()
        vals.extend(a.vals())
    packed_vals = struct.pack("<HHHHHHHHHHHHHHHHHH", *vals)
    slipdev.write("".join([ARTOO_CALIBRATE_ID, packed_vals]))
    print "\nCalibration complete, values stored."


#
# main
#

if len(sys.argv) < 2:
    print "usage: stick-cal.py /dev/ttyMyDev"
    sys.exit(1)

mainloop(sys.argv[1])
