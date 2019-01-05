#!/usr/bin/env python

import sys, os, struct
import serial, slip

ARTOO_BAUD = 115200

ARTOO_OUTPUT_TEST_ID = chr(0xc)


def int_with_default(s, d):
    if s == "":
        return d
    return int(s, 0)

def mainloop(serialpath):

    serialport = serial.Serial(serialpath, ARTOO_BAUD)
    slipdev = slip.SlipDevice(serialport)

    while True:
        try:
            w = raw_input('white led mask (0xff): ')
            w = int_with_default(w, 0xff)

            g = raw_input('green led mask (0xff): ')
            g = int_with_default(g, 0xff)

            b = raw_input('buzzer hz (0): ')
            b = int_with_default(b, 0x0)

            m = raw_input('motor duration (0): ')
            m = int_with_default(m, 0x0)

            print "setting vals: white LEDs 0x%x, green LEDs 0x%x, buzzer hz %d, motor duration %d" % (w, g, b, m)
            packed_vals = struct.pack("<BBHB", w, g, b, m)
            
            slipdev.write("".join([ARTOO_OUTPUT_TEST_ID, packed_vals]))

        except KeyboardInterrupt:
            print "\ndone."
            break

        except:
            print "\ninvalid input, try again."

#
# main
#

if len(sys.argv) < 2:
    print "usage: output-test.py /dev/ttyMyDev"
    sys.exit(1)

mainloop(sys.argv[1])
