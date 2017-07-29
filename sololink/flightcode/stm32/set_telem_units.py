#!/usr/bin/env python

import sys
import set_telem_units_msg


def usage():
    print "usage: set_telem_units.py [metric|imperial]"


if __name__ == "__main__":

    # one required argument: "metric" or "imperial"
    if len(sys.argv) != 2:
        usage()
        sys.exit(1)

    if sys.argv[1] == "metric":
        msg = set_telem_units_msg.pack_msg(True)
    elif sys.argv[1] == "imperial":
        msg = set_telem_units_msg.pack_msg(False)
    else:
        usage()
        sys.exit(1)

    # send message to stm32
    set_telem_units_msg.send(msg)

    sys.exit(0)
