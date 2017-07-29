#!/usr/bin/env python

import sys, os, struct, datetime
import serial, slip

from msg_id import MsgID
from event_id import EventID
import artoo

ARTOO_BAUD = 115200
EVENT_MSG = 'TestEvent'
FORMAT_ID = '<B'
FORMAT_EVENT = 'B'

import IPython

def get_msg_id(msg_name):
    msg_id = MsgID.index(msg_name)
    return msg_id

def get_event_id(event_name):
    event_id = EventID.index(event_name) 
    alert_id = EventID.index('AlertBegin')
    ALERT_OFFSET = 100
    FIRST_ELEM_OFFSET = -1

    # offset event id if it is an alert
    if event_id >= alert_id:
        event_id = (event_id - alert_id) + ALERT_OFFSET + FIRST_ELEM_OFFSET

    # print "[get_event_id]"
    # IPython.embed()
    # print "\[get_event_id]"

    return event_id

def pack_msg(msg_name,event_name):
    msg_id = get_msg_id(msg_name)
    event_id = get_event_id(event_name)

    return struct.pack("".join([FORMAT_ID,FORMAT_EVENT]), msg_id, event_id)

def send_event(dev, event_name):
    return dev.write(pack_msg(EVENT_MSG, event_name))

def show_all_alerts(dev):
    show_all_from(dev, 'AlertBegin')

def show_all_from(dev, first_alert):
    alert_id = EventID.index('AlertBegin')
    first_id = EventID.index(first_alert)
    for event_name in EventID:
        event_id = EventID.index(event_name) 
        if (event_id >= first_id and event_id >= alert_id):
            raw_input('Press enter to continue to {}: '.format(event_name))
            send_event(dev, event_name)
            raw_input('Press enter to dismiss {}: '.format(event_name))
            send_event(dev, 'AlertRecovery')

def mainloop(serialpath):

    serialport = serial.Serial(serialpath, ARTOO_BAUD)
    slipdev = slip.SlipDevice(serialport)
    
    s = pack_msg(EVENT_MSG, 'AltitudeCalRequired')

    print "[mainloop]"
    IPython.embed()
    # slipdev.write("".join([str(get_msg_id("SetShotInfo")), "COORDINATED TURNS", '\0']))
    # slipdev.write("".join([chr(0x11), "COORDINATED TURNS", '\0']))
    slipdev.write("".join([artoo.MSGID_SOLO_APP_CONNECTION, chr(1), '\0']))
    print "\[mainloop]"

    # usage
    send_event(slipdev, 'SoloConnectionPoor')

    print "[sweep-cfg] Serial write returned: ", slipdev.write(s)

#
# main
#

if len(sys.argv) < 2:
    print "usage: test_event.py /dev/ttyMyDev"
    sys.exit(1)

mainloop(sys.argv[1])
