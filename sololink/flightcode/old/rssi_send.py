#!/usr/bin/env python

import os
import socket
import sys
import time
import logging
import logging.config
import iw
from pymavlink import mavutil
sys.path.append("/usr/bin")
import clock

if_name = "wlan0"
src_system = 10
src_component = 0
conf_filename = "/etc/sololink.conf"


# 'mav' is a mavutil.mavlink.MAVLink, needed for
#   srcSystem, srcComponent, and sequence
# 'dbm' is the signal dbm as read from the wifi card
# return is a mavlink message as a string (binary)
def create_rssi_msg(mav, dbm):
    # dbm is a small negative number. We would like the rssi byte in the
    # mavlink message to be interpretable as a signed byte, but the mavlink
    # stuff packs it as an unsigned byte. Get the right bits into the
    # message by munging before packing:
    #  dbm    byte_to_pack
    # -128 -> 0x80 -> 128
    #   -1 -> 0xff -> 255
    #    0 -> 0x00 ->   0
    #    1 -> 0x01 ->   1
    # +127 -> 0x7f -> 127
    # ...so negative values of dbm are replaced with (256 + dbm)
    # This is all just to get the pymavlink struct packer to generate the
    # message we want.

    if dbm is None or dbm < -128:
        dbm = -128
    if dbm > 127:
        dbm = 127

    if dbm >= 0:
        rssi = dbm
    else:
        rssi = 256 + dbm

    # on Solo, we are "remrssi"
    msg = mavutil.mavlink.MAVLink_radio_status_message(
        rssi=0, remrssi=rssi, txbuf=0, noise=0, remnoise=0, rxerrors=0, fixed=0
    )
    return msg.pack(mav)


# take a mavlink message and print the remrssi
def show_remrssi(m):
    rssi = ord(m[11])
    if rssi >= 128:
        rssi -= 256
    print rssi


logging.config.fileConfig(conf_filename)
logger = logging.getLogger("wifi")

logger.info("rssi_send starting")

mav = mavutil.mavlink.MAVLink(None, src_system, src_component)

# socket to inject into downlink telemetry from
sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
sock.bind("/tmp/rssi_send." + str(os.getpid()))

skip_list = [ "mac", "ssid", "freq" ]

abbrev_list = {
    "rxBytes" : "rxb", "rxPackets" : "rxp",
    "txBytes" : "txb", "txPackets" : "txp",
    "txBitrate" : "txr", "signal" : "sig"
}

#RC lockout
rclockout = True
#if there is an unlock file or no lock file, we're unlocked
if os.path.isfile("/tmp/.rc_unlock"):
    rclockout = False
elif (not os.path.isfile("/etc/.rc_lock")) and (not os.path.isfile("/mnt/rootfs.ro/etc/.rc_lock")):
    rclockout = False

# how often to send a message
interval_us = 1000000

next_us = clock.gettime_us(clock.CLOCK_MONOTONIC) + interval_us

while True:

    now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    if next_us > now_us:
        time.sleep((next_us - now_us) / 1000000.0)
    next_us += interval_us

    info = iw.link(if_name)
    s = ""
    for key in info:
        if key in skip_list:
            continue
        if key in abbrev_list:
            lbl = abbrev_list[key]
        else:
            lbl = key
        s = s + str(lbl) + "=" + str(info[key]) + " "
    logger.info(s)
    dbm = info["signal"]

    #Check the lockout status again
    if rclockout is True:
        if os.path.isfile("/tmp/.rc_unlock"):
            rclockout = False

    if rclockout is False:
        try:
            m = create_rssi_msg(mav, dbm)
            sock.sendto(m, "/run/telem_downlink")
            mav.seq += 1
            if mav.seq >= 256:
                mav.seq = 0
        except:
            pass
