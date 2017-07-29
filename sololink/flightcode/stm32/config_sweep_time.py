#!/usr/bin/env python

import pprint
import sys
import config_sweep_time_msg
import param_stored_vals_msg


def usage():
    print "usage: config_sweep_time.py"
    print "           get sweep time settings"
    print "       config_sweep_time.py <min_sweep_sec> <max_sweep_sec>"
    print "           set sweep time settings"


if __name__ == "__main__":

    verbose = False # True for debug

    pp = pprint.PrettyPrinter()

    # if two arguments, we are setting, and they are min and max
    if len(sys.argv) == 1:
        # getting
        min_sweep_s = None
        max_sweep_s = None
    elif len(sys.argv) == 3:
        # setting - arguments must be integers
        try:
            min_sweep_s = int(sys.argv[1])
            max_sweep_s = int(sys.argv[2])
        except:
            usage()
            sys.exit(1)

    if min_sweep_s is not None and max_sweep_s is not None:
        # create "config sweep time" message
        msg = config_sweep_time_msg.pack(min_sweep_s, max_sweep_s)

        # send message to stm32
        config_sweep_time_msg.send(msg)

    # retrieve parameters to verify
    params = param_stored_vals_msg.fetch()

    # params is a string; unpack to a dictionary
    params = param_stored_vals_msg.unpack(params)
    if verbose:
        print "params message:"
        pp.pprint(params)

    if min_sweep_s is not None and max_sweep_s is not None:
        # verify that sweep times are as requested
        if params['sweepConfigs'][0] != (min_sweep_s, max_sweep_s):
            print "requested sweep times (%d, %d); not returned in params" % \
                    (min_sweep_s, max_sweep_s)
            print "returned params:"
            pp.pprint(params['sweepConfigs'])
            sys.exit(1)

    print "%d %d" % (params['sweepConfigs'][0][0], params['sweepConfigs'][0][1])

    sys.exit(0)
