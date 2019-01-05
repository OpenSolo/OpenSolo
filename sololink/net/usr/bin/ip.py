#!/usr/bin/env python

import re
import subprocess


# ip expected output:
#
# $ ip link
# 1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue 
#     link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
# 2: sit0: <NOARP> mtu 1480 qdisc noop 
#     link/sit 0.0.0.0 brd 0.0.0.0
# 3: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq qlen 1000
#     link/ether 00:02:60:51:90:06 brd ff:ff:ff:ff:ff:ff

def getMac(ifName):
    try:
        iwOut = subprocess.check_output(['ip', 'link'], stderr=subprocess.STDOUT)
    except:
        return None
    m = re.search('^[0-9]+: ' + ifName + ': .*\n +link/[a-z]+ ([0-9a-f:]+) brd', iwOut, re.M)
    if m:
        return m.group(1)
    return None


# Set the 02:00:00:00:00:00 bit in a MAC
# The purpose of this is to set the "locally administered" bit in a MAC
# (see http://en.wikipedia.org/wiki/MAC_address). The purpose of that is to
# generate a second MAC that we can use for simultaneous AP/STATION support
# for SoloLink. We handle the case where that bit is already set; it is not
# expected to be set, but if it is, we would rather clear it than fail.

def macSetLocal(mac):
    if len(mac) < 2:
        return None
    oldNibble = mac[1]
    # 0->2, 1->3, 4->6, etc.
    if   oldNibble == '0': newNibble = '2'
    elif oldNibble == '1': newNibble = '3'
    elif oldNibble == '2': newNibble = '0'
    elif oldNibble == '3': newNibble = '1'
    elif oldNibble == '4': newNibble = '6'
    elif oldNibble == '5': newNibble = '7'
    elif oldNibble == '6': newNibble = '4'
    elif oldNibble == '7': newNibble = '5'
    elif oldNibble == '8': newNibble = 'a'
    elif oldNibble == '9': newNibble = 'b'
    elif oldNibble == 'a': newNibble = '8'
    elif oldNibble == 'b': newNibble = '9'
    elif oldNibble == 'c': newNibble = 'e'
    elif oldNibble == 'd': newNibble = 'f'
    elif oldNibble == 'e': newNibble = 'c'
    elif oldNibble == 'f': newNibble = 'd'
    else:
        return None
    return mac[0:1] + newNibble + mac[2:]


# Return last three bytes of MAC as a string
def mac3(ifname):
    mac = getMac(ifname)
    if len(mac) != 17:
        return ""
    return mac[9:11] + mac[12:14] + mac[15:17]


if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser('ip.py [options]')
    parser.add_option('-3', '--mac3', dest='mac3_ifname', type='string',
                      default=None,
                      help='return last three bytes of interface\'s MAC')
    (opts, args) = parser.parse_args()
    if opts.mac3_ifname is not None:
        print mac3(opts.mac3_ifname)
