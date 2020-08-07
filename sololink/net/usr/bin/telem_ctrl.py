#!/usr/bin/env python

# Forward telemetry to everyone attached to the AP.

# NOTE: this has been superseded by telem_ctrl.cpp!  This doesn't
# handle mavlink2!

import ConfigParser
import datetime
import logging
import logging.config
import os
import re
import select
import socket
import sys
import time
import struct
import clock
from pymavlink import mavutil

logging.config.fileConfig("/etc/sololink.conf")
logger = logging.getLogger("tlm")

logger.info("starting")

solo_conf = "/etc/sololink.conf"

config = ConfigParser.SafeConfigParser()
config.read(solo_conf)

hostapd_ctrl_sock_name = "/var/run/hostapd/wlan0-ap"

# pairing module writes solo's IP address here when it is found
solo_address_file = "/var/run/solo.ip"


# read configuration items
try:
    mav_dest_port = config.getint("solo", "mavDestPort")
    telem_dest_port = config.getint("solo", "telemDestPort")
    use_gps_time = config.getboolean("solo", "useGpsTime")
except:
    logger.error("error reading config from %s", solo_conf)
    sys.exit(1)



def get_arp_table():
    """return ARP table as a list of tuples

    Only the MAC and IP are returned for each entry, since that is all that is
    currently needed. Each entry is ("IP", "MAC").

    IP address  HW type  Flags  HW address         Mask  Device
    10.1.1.123  0x1      0x2    00:e0:4c:15:0a:df  *     wlan0-ap
    10.1.1.103  0x1      0x2    00:e0:4c:15:0a:df  *     wlan0-ap
    10.1.1.160  0x1      0x2    00:1f:09:04:00:24  *     wlan0-ap
    """
    arp_table = []

    arp_table_file = "/proc/net/arp"
    try:
        f = open(arp_table_file)
    except:
        logger.error("can't open %s", arp_table_file)
        return arp_table

    for line in f:
        m = re.match("([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+).*?(\
[0-9a-fA-F][0-9a-fA-F]:[0-9a-fA-F][0-9a-fA-F]:[0-9a-fA-F][0-9a-fA-F]:\
[0-9a-fA-F][0-9a-fA-F]:[0-9a-fA-F][0-9a-fA-F]:[0-9a-fA-F][0-9a-fA-F])", line)
        if m:
            arp_table.append((m.group(1), m.group(2).lower()))
    f.close()

    logger.debug("get_arp_table: %s", str(arp_table))

    return arp_table



def get_mac_ips(mac, arp_table=None):
    """get MAC's IPs

    Given a MAC address, find it in the ARP table and return all IP addresses
    for it. NOTE that one MAC can have multiple IPs.
    """
    ips = []
    mac = mac.lower()
    if arp_table is None:
        arp_table = get_arp_table()
    for entry in arp_table:
        if entry[1] == mac:
            ips.append(entry[0])
    return ips



def get_stations(sock):
    """get list of attached stations

    The return value is a list of tuples, where each tuple is ("mac", "ip").
    The MAC address will always be there, but the IP will only be there if
    there is currently an entry in the ARP table.
    """
    stations = []

    arp_table = get_arp_table()

    # query hostapd for all attached stations
    sock.sendto("STA-FIRST", hostapd_ctrl_sock_name)
    p = sock.recv(1024)
    while p:
        lines = p.splitlines()
        mac = lines[0]
        ips = get_mac_ips(mac, arp_table)
        for ip in ips:
            stations.append((mac, ip))
        sock.sendto("STA-NEXT %s" % mac, hostapd_ctrl_sock_name)
        p = sock.recv(1024)

    logger.debug("get_stations: %s", str(arp_table))

    return stations


# wait for solo to attach, and get its IP address
while True:
    try:
        f = open(solo_address_file)
    except IOError:
        # no solo yet
        time.sleep(1.0)
        continue
    data = f.read()
    f.close()
    solo_ip = data.strip()
    break
### end while True


# hostapd control socket
hostapd_ctrl_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

# socket has to have a name even if we don't want to receive anything
hostapd_ctrl_local_name = "/tmp/telem_ctrl-%d" % os.getpid()
hostapd_ctrl_sock.bind(hostapd_ctrl_local_name)

# port in solo to send telemetry to; this is set when we get the first
# downlink telemetry packet
solo_port = None

# solo-side socket
# receives from solo, sends to solo
solo_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
solo_sock.bind(("", telem_dest_port))

# gcs-side socket
# receives from GCSes, sends to GCSes
gcs_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
gcs_sock.bind(("", 0))

read_socks = [solo_sock, gcs_sock]

# index by tuple (src_system, src_component)
# corrupt packets in (-1, -1)
packets_down = { }
packets_down_drops = { }

packets_down_total = 0
packets_up_total = 0

# list of tuples ("mac", "ip")
current_stations = []

now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)

# how often to update list of stations to send telemetry to
station_update_interval_us = long(5 * 1000000)
station_update_time_us = now_us

# how often to log packet counts
report_interval_us = long(10 * 1000000)
report_time_us = now_us + report_interval_us

got_gps_time = False

# last_down_sequence is indexed by a tuple (src_system, src_component)
# Each component has an independently running sequence, so we must keep track
# of each.
last_down_sequence = { }

# Time when we can log another drop. Each time we log, we increment this by
# drop_log_min_us so we don't log more than that often. drop_log_count is the
# number of drops we did not log; it is printed to the log if it is not zero.
drop_log_us = 0
drop_log_min_us = 1000000 # 1 second
drop_log_count = 0

# Time when we can log another corrupt packet.
drop_corrupt_us = 0
drop_corrupt_min_us = 1000000 # 1 second
drop_corrupt_count = 0

while True:

    # check for packets to forward
    ready = select.select(read_socks, [], [], 1.0)

    now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)

    if solo_sock in ready[0]:
        # packet from solo
        pkt, src_adrs = solo_sock.recvfrom(4096)
        packets_down_total += 1

        # check for "corrupt", where "corrupt" means we shouldn't even look
        # at this packet
        pkt_corrupt = False
        pkt_len = len(pkt)
        if pkt_len < 8:
            pkt_corrupt = True
        else:
            # manual decode of mavlink header
            magic = ord(pkt[0])
            if magic != 254:
                pkt_corrupt = True
            length = ord(pkt[1])
            if length != (pkt_len - 8):
                pkt_corrupt = True
            sequence = ord(pkt[2])
            src_sys = ord(pkt[3])
            src_comp = ord(pkt[4])
            msg_id = ord(pkt[5])

        if pkt_corrupt:

            src = (-1, -1)
            # Log corrupt packets, but don't flood the log
            if src not in packets_down:
                packets_down[src] = 1      # first one
            else:
                packets_down[src] += 1     # not first one

            if now_us >= drop_corrupt_us:
                # loggit!
                if drop_corrupt_count > 0:
                    logger.info("downlink: (skipped %d corrupt packets)",
                                drop_corrupt_count)
                    drop_corrupt_count = 0
                # pkt[:6] works even if pkt is less than 6 chars, e.g.
                # '1234'[:6] = '1234'
                logger.info("downlink: corrupt packet: %s",
                            str([ord(c) for c in pkt[:6]]))
                drop_corrupt_us = now_us + drop_corrupt_min_us
            else:
                # don't log it
                drop_corrupt_count += 1

        else: # packet not corrupt

            src = (src_sys, src_comp)

            # initialize last_down_sequence[(system, component)] if necessary
            # (happens for first message from a component)
            if src not in last_down_sequence:
                if sequence == 0:
                    last_down_sequence[src] = 255
                else:
                    last_down_sequence[src] = sequence - 1

            expected_sequence = last_down_sequence[src] + 1
            if expected_sequence == 256:
                expected_sequence = 0

            # Log dropped packets, but don't flood the log.
            # Ignore sequence numbers in gimbal messages (they are not right).
            if (src_sys != 1 or src_comp != 154) and sequence != expected_sequence:
                if src not in packets_down_drops:
                    packets_down_drops[src] = 0
                packets_down_drops[src] += 1
                if now_us >= drop_log_us:
                    # loggit!
                    logger.info("downlink: %d sequence errors: sys=%d comp=%d seq=%d",
                                1 + drop_log_count, src_sys, src_comp, sequence)
                    drop_log_count = 0
                    drop_log_us = now_us + drop_log_min_us
                else:
                    # don't log it
                    drop_log_count += 1

            last_down_sequence[src] = sequence

            # count packets from each source
            if src not in packets_down:
                packets_down[src] = 1   # first one
            else:
                packets_down[src] += 1  # not first one

            # The port on solo we send to varies; we save it from the first packet
            # received. If we don't know the port yet and the packet is from solo,
            # save the port number.
            if src_adrs[0] == solo_ip:
                if solo_port is None:
                    # first time we've see solo
                    logger.info("downlink: solo is at %s:%d", solo_ip, src_adrs[1])
                elif solo_port != src_adrs[1]:
                    # not first time we've see solo, but it's at a new port
                    logger.info("downlink: solo is now at %s:%d", solo_ip, src_adrs[1])
                solo_port = src_adrs[1]

            if not got_gps_time:
                if msg_id == mavutil.mavlink.MAVLINK_MSG_ID_SYSTEM_TIME:
                    if len(pkt) == 20: # 6 + 12 + CRC
                        unix_usec, boot_msec = struct.unpack("<QI", pkt[6:18])
                        if unix_usec != 0:
                            got_gps_time = True
                            dt = datetime.datetime.fromtimestamp(unix_usec / 1000000.0)
                            logger.info("downlink: GPS time %s", str(dt))
                            if use_gps_time:
                                # set system clock
                                clock.settime_us(clock.CLOCK_REALTIME, unix_usec)
                                logger.info("downlink: system time set from GPS time")

            # forward packet to all GCSes
            for station in current_stations:
                # station is ("mac", "ip"). Forward using gcs_sock, since the
                # receiver may use the source of telemetry packets as the
                # uplink destination.
                gcs_sock.sendto(pkt, (station[1], telem_dest_port))
            # stm32 is on local machine, on a different port
            gcs_sock.sendto(pkt, ("127.0.0.1", mav_dest_port))
            # tlog is on local machine, on a different port
            gcs_sock.sendto(pkt, ("127.0.0.1", 14583))

        ### end if packet corrupt

    ### end if solo_sock...

    if gcs_sock in ready[0]:
        # packet from GCS
        pkt = gcs_sock.recv(4096)
        packets_up_total += 1
        # forward to solo
        if solo_port is not None:
            solo_sock.sendto(pkt, (solo_ip, solo_port))
    ### end if gcs_sock...

    # check for new machines to send telemetry to
    if now_us > station_update_time_us:

        all_stations = get_stations(hostapd_ctrl_sock)

        # all_stations is list of tuples ("mac", "ip"). The MAC is always
        # present, but the IP might be None if the ARP entry has timed out.
        # A station is only added to current_stations if the IP is not None.
        # A station is only removed from current_stations if the MAC is no
        # longer there. (This code would be simpler if we knew that ARP
        # entries never timed out.)

        # any new ones to add?
        for new_station in all_stations:
            if new_station[1] is None:
                continue # no IP, can't add it even if new
            if new_station[1] == solo_ip:
                continue # don't send telemtry back to solo!
            found = False
            for old_station in current_stations:
                if new_station[0] == old_station[0] and \
                   new_station[1] == old_station[1]: # compare MACs and IPs
                    found = True
                    break
            if not found:
                logger.info("adding %s", str(new_station))
                current_stations.append(new_station)

        # any not there any more?
        for old_station in current_stations:
            found = False
            for new_station in all_stations:
                if old_station[0] == new_station[0]:
                    found = True
                    break
            if not found:
                logger.info("removing %s", str(old_station))
                current_stations.remove(old_station)

        station_update_time_us += station_update_interval_us

    ### end if now_us > station_update_time_us

    # time to report status?
    if now_us > report_time_us:
        msg = "downlink:"
        for src in packets_down:
            msg += " (%d,%d):%d" % (src[0], src[1], packets_down[src])
        packets_down = { }
        if len(packets_down_drops) > 0:
            msg += " -"
            for src in packets_down_drops:
                msg += " (%d,%d):%d" % (src[0], src[1], packets_down_drops[src])
            packets_down_drops = { }
        msg += " uplink: %d" % packets_up_total
        packets_up_total = 0
        logger.info(msg)
        report_time_us += report_interval_us

### end while True
