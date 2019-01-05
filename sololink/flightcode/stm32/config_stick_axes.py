#!/usr/bin/env python

import pprint
import ConfigParser
import sys
import config_stick_axes_msg
import param_stored_vals_msg


def usage():
    print "usage: config_stick_axes.py set <config file>"
    print "           set stick mapping using config file"
    print "       config_stick_axes.py get <config file>"
    print "           get stick mapping and compare to config file (\"true\", \"false\")"


# read one field from config file and return as integer
def get_field(cfg, axis, field, valid_range=None):
    # if not specified, leave uninitialized
    if not cfg.has_option(axis, field):
        return 0xff
    f = cfg.getint(axis, field)
    if valid_range:
        if f not in valid_range:
            raise ValueError("bad value for %s" % field)
    return f


# read a single axis from config file and return it as packed string
def validate_and_pack_axis_info(cfg, axis):
    stick_id = get_field(cfg, axis, 'mapped_stick_id', range(5))
    # NB: direction - non-zero is Forward, 0 is Reverse
    direction = get_field(cfg, axis, 'direction', [0, 1])
    expo = get_field(cfg, axis, 'expo')
    return config_stick_axes_msg.pack_stick(stick_id, direction, expo)


# read a stick config file and return a message ready to send to STM32
def msg_from_cfg(cfg):
    msg = ""
    for axis in ["stick-0", "stick-1", "stick-2", "stick-3", "stick-4", "stick-5"]:
        msg += validate_and_pack_axis_info(cfg, axis)
    return msg


# config_stick_axes.py set <config_file>
#   configure stick axes using the specified config file.
#
# config_stick_axes.py get <config_file>
#   read the stick axes configuration, and if they match the config file, return True

if __name__ == "__main__":

    verbose = False # True for debug

    pp = pprint.PrettyPrinter()

    # two required arguments: set or get, and config file to use
    if len(sys.argv) != 3:
        usage()
        sys.exit(1)

    if sys.argv[1] != "set" and sys.argv[1] != "get":
        usage()
        sys.exit(1)

    # read stick configuration
    cfg = ConfigParser.ConfigParser()
    try:
        cfg.read(sys.argv[2])
    except:
        print "%s: error opening %s" % (sys.argv[0], sys.argv[2])
        sys.exit(1)

    # convert stick configuration to "config stick axes" message
    try:
        request = msg_from_cfg(cfg)
    except:
        print "%s: error converting %s to request" % (sys.argv[0], sys.argv[2])
        sys.exit(1)

    if sys.argv[1] == "set":
        # send message to stm32
        config_stick_axes_msg.send(request)

    # unpack request to dictionary for verification or compare below
    request = config_stick_axes_msg.unpack(request)
    if verbose:
        print "request message:"
        pp.pprint(request)

    # retrieve parameters
    params = param_stored_vals_msg.fetch()

    # params is a string; unpack to a dictionary
    params = param_stored_vals_msg.unpack(params)
    if verbose:
        print "params message:"
        pp.pprint(params)

    # verify that the request matches the params read back
    if request == params['rcSticks']:
        match = True
    else:
        match = False
        if sys.argv[1] == "set":
            print "stick mapping returned does not match requested"
            print "request:"
            pp.pprint(request)
            print "params:"
            pp.pprint(params['rcSticks'])
            sys.exit(1)

    if sys.argv[1] == "get":
        if match:
            print "true"
        else:
            print "false"

    sys.exit(0)
