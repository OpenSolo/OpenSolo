#!/usr/bin/env python

import sys
import ip

if len(sys.argv) < 2:
    print 'Usage: ' + sys.argv[0] + ' <ifName>'
    sys.exit(1)

oldMac = ip.getMac(sys.argv[1])
if oldMac is None:
    print 'ERROR getting MAC address for ' + sys.argv[1]
    sys.exit(1)

newMac = ip.macSetLocal(oldMac)
if newMac is None:
    print 'ERROR getting local MAC address for ' + oldMac
    sys.exit(1)

print newMac

sys.exit(0)
