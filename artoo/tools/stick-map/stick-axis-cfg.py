#!/usr/bin/env python
#
# valid fields for each axis: stick_id, direction, expo (optional, defaults to 2)
#

import sys, os, struct, ConfigParser
import serial, slip

ARTOO_BAUD = 115200
DEFAULT_EXPO = 2

ARTOO_STORED_PARAMS_ID  = chr(0xb)
ARTOO_CFG_STICK_AXES_ID = chr(0xf)

def wait_for_params(slipdev):
    while True:
        slipdev.write("".join([ARTOO_STORED_PARAMS_ID]))
        pkt = slipdev.read()
        pkt = "".join(pkt)
        if pkt[0] == ARTOO_STORED_PARAMS_ID:
            return pkt[1:]

def get_field(cfg, axis, field, valid_range = None):
    # if not specified, leave uninitialized
    if not cfg.has_option(axis, field):
        return 0xff

    f = cfg.getint(axis, field)
    if valid_range:
        if f not in valid_range:
            raise ValueError("bad value for %s" % field)

    return f

def validate_and_pack_axis_info(cfg, axis):
    stick_id = get_field(cfg, axis, 'mapped_stick_id', range(5))
    # NB: direction - non-zero is Forward, 0 is Reverse
    direction = get_field(cfg, axis, 'direction', [0, 1])
    expo = get_field(cfg, axis, 'expo')

    return struct.pack("<BBBBI", stick_id, direction, expo, 0, 0xffffffff)


def mainloop(serialpath, cfg):

    serialport = serial.Serial(serialpath, ARTOO_BAUD)
    slipdev = slip.SlipDevice(serialport)

    payload = ""
    for axis in ["stick-0", "stick-1", "stick-2", "stick-3", "stick-4", "stick-5"]:
        payload += validate_and_pack_axis_info(cfg, axis)

    slipdev.write(ARTOO_CFG_STICK_AXES_ID + payload)
    print "\nverifying config..."
    params = wait_for_params(slipdev)
    # XXX: compare params...
    print "Calibration complete, values stored."


#
# main
#

if len(sys.argv) < 3:
    print "usage: stick-axis-cfg.py /dev/ttyMyDev configfile.cfg"
    sys.exit(1)

config = ConfigParser.ConfigParser()
config.optionxform = str    # don't lower case all option names
config.read(os.path.join(os.getcwd(), sys.argv[2]))

mainloop(sys.argv[1], config)
