#!/usr/bin/python

# This uses the above '#!' instead of '#!/usr/bin/env python' so that the
# busybox 'pidof' can find this process by name.

import ConfigParser
import clock
import logging
import logging.config
import socket
import sys

solo_conf = "/etc/sololink.conf"

logging.config.fileConfig(solo_conf)
logger = logging.getLogger("vid")

logger.info("starting")

# Read packets from 127.0.0.1:5600, and forward them to another IP, same port.
# 127.0.0.1:5600 is where the SN decoder streams video.
# Other IP address is expected to be the App.

def get_app_ip():
    try:
        f = open(app_address_file)
        ip = f.read()
        ip = ip.strip()
        f.close()
        return ip
    except IOError:
        return None

src_ip = ""
src_port = 5600

dst_ip = None
dst_port = 5600

app_address_file = ""

config = ConfigParser.SafeConfigParser()

# if the config file is not found, and empty list is returned and the
# "get" operations later fail
config.read(solo_conf)

# read configuration items
try:
    app_address_file = config.get("solo", "appAddressFile")
except:
    logger.error("error reading config from %s", solo_conf)
    sys.exit(1)

packet_count = 0
byte_count = 0

now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)

log_interval_s = 10
log_interval_us = long(log_interval_s * 1000000)
log_time_us = now_us + log_interval_us

app_time_us = now_us
app_interval_us = 1000000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 191) #Highest level VI
sock.bind((src_ip, src_port))

while True:
    # forward a packet
    pkt = sock.recv(4096)

    now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)

    # To reduce jitter, send it first, then check for changes. This means
    # when the destination IP changes, we'll probably not send the first
    # packet, and send one too many at the end.

    if dst_ip is not None:
        sock.sendto(pkt, (dst_ip, dst_port))
        packet_count += 1
        byte_count += len(pkt)
        if now_us > log_time_us:
            bytes_sec = byte_count / log_interval_s
            logger.info("%0.1f pkts/s, %d bytes/s, %d bits/s)",
                        float(packet_count) / float(log_interval_s),
                        bytes_sec, bytes_sec * 8)
            packet_count = 0
            byte_count = 0
            log_time_us += log_interval_us
    else:
        # avoid a barrage of catchup messages when the app goes away then comes back
        log_time_us = clock.gettime_us(clock.CLOCK_MONOTONIC) + log_interval_us

    if now_us > app_time_us:
        # Check for change in dst_ip. It might change from None to some IP
        # address, from an IP address to None, or from one IP address to another.
        app_ip = get_app_ip()
        if dst_ip != app_ip:
            dst_ip = app_ip
        app_time_us = now_us + app_interval_us
