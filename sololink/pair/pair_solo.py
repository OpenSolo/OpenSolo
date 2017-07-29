#!/usr/bin/env python

import errno
import ConfigParser
import logging
import logging.config
import os
import pair
import re
import select
import shutil
import socket
import struct
import sys
import time
sys.path.append("/usr/bin")
import clock
import ifconfig
import iw
import runlevel
import udhcpc
import wpa_control
import wpa_supplicant
import rc_lock

sololink_conf = "/etc/sololink.conf"
wpa_supplicant_conf = "/etc/wpa_supplicant.conf"
wpa_supplicant_back = "/etc/wpa_supplicant.back"
sololink_version_file = "/VERSION"
firmware_version_file = "/PIX_VERSION"
controller_sololink_version_file = "/tmp/PEER_SL_VERSION"
controller_firmware_version_file = "/tmp/PEER_FW_VERSION"

# defaults for items normally read from config file
controller_link_port = 5501
wifi_connect_timeout = 5.0
connect_request_interval = 1.0
connect_ack_timeout = 0.5
button_filename = "/dev/input/event0"
solo_ip = "10.1.1.10"
check_versions = True

# It is not critical that the PIN be secret. The reason for using WPS PIN is
# not the PIN's security (it is not), but that we can cause hostapd to ask us
# for the PIN, at which time get confirmation from the user.
secret_pin = 74015887

button_error = False
button_file = None

runlevel_ready = False

# Log a version mismatch once per minute
version_mismatch_log_time_us = 0
version_mismatch_log_interval_us = 60 * 1000000

controller_sololink_version = None
controller_firmware_version = None

ifname = "wlan0"

wpa = wpa_control.WpaControl(ifname)


# conditions:
#   paired/not_paired: whether network exists in wpa_supplicant.conf


def pair_button():
    """get status of pairing button

    Returns True if pairing button has been pushed since the last call to this
    function, or False otherwise.
    """
    global button_error, button_file
    if not button_error and button_file is None:
        # open on first call
        try:
            button_file = open(button_filename)
        except:
            button_error = True
            logger.error("can't open %s for reading", button_filename)
    pushed = False
    if not button_error:
        # read all events, looking for pushes and ignoring others
        while True:
            r, w, x = select.select([button_file], [], [], 0)
            if len(r) == 0:
                # no more events
                break
            # button event
            event = r[0].read(16)
            if len(event) != 16:
                logger.error("event not 16 bytes: len=%d, event=%s",
                             len(event),
                             str([hex(ord(x)) for x in event]))
            # event is:
            #   struct input_event {
            #       struct timeval time;
            #       unsigned short type;
            #       unsigned short code;
            #       unsigned int value;
            #   };
            # time:  8 bytes, not used here
            # type:  EV_SYN=0x0000, EV_KEY=0x0001
            # code:  KEY_WPS_BUTTON=0x0211
            # value: 1 on push, 0 on release
            # Fields are little endian.
            #
            # button push:
            # xx xx xx xx xx xx xx xx 01 00 11 02 01 00 00 00
            #     type=0x0001 code=0x0211 value=0x00000001
            # xx xx xx xx xx xx xx xx 00 00 00 00 00 00 00 00
            #     type=0x0000 code=0x0000 value=0x00000000
            #
            # button release:
            # xx xx xx xx xx xx xx xx 01 00 11 02 00 00 00 00
            #     type=0x0001 code=0x0211 value=0x00000000
            # xx xx xx xx xx xx xx xx 00 00 00 00 00 00 00 00
            #     type=0x0000 code=0x0000 value=0x00000000
            try:
                s, t, c, v = struct.unpack("@QHHi", event)
                if t == 0x0001 and c == 0x0211 and v == 1:
                    pushed = True
                    # keep reading events to flush out others
            except:
                logger.error("error unpacking input event: %s",
                             str([hex(ord(x)) for x in event]))
        ### end while True
    ### end if not button_error
    return pushed


# Returns:
#   First network name if there is at least one
#   None if there are no networks
def wpa_supplicant_network_get():
    """get network from wpa_supplicant.conf

    Retrieve and return ssid from network={} section in wpa_supplicant.conf.
    The first network found is returned.
    """

    try:
        d = wpa_supplicant.read(wpa_supplicant_conf)
    except:
        logger.error("can't open %s for reading", wpa_supplicant_conf)
        return None

    if "network" in d:
        for net in d["network"]:
            # net is a dictionary of net parameters
            if "ssid" in net:
                name = net["ssid"][0]
                # strip leading and trailing quotes
                if name[0] == "\"" and name[-1] == "\"":
                    name = name[1:-1]
                return name

    # no network in wpa_supplicant.conf
    return None


# Returns:
#   True - Solo is paired
#   False - Solo is not paired
def is_paired():
    # Solo is "paired" if there is a network in wpa_supplicant.conf
    ssid = wpa_supplicant_network_get()
    return (ssid is not None)


# Returns True or False
def pin_pair():
    logger.info("pin pair...")
    wpa.pin_pair(secret_pin)
    state = None
    last_state = None
    start_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    while True:
        time.sleep(0.1)
        stat = wpa.get_status()
        now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
        if "wpa_state" in stat:
            state = stat["wpa_state"]
        else:
            state = None
        if state != last_state:
            if "ssid" in stat:
                ssid = stat["ssid"]
            else:
                ssid = ""
            if "bssid" in stat:
                bssid = stat["bssid"]
            else:
                bssid = ""
            logger.debug("%0.3f %s %s %s", (now_us - start_us) / 1000000.0,
                         state, ssid, bssid)
            last_state = state
        if state == "COMPLETED":
            break
        if state == "INACTIVE":
            break
    # end while
    if state == "COMPLETED":
        wpa.set("update_config", "1")
        wpa.save()
        wpa.set("update_config", "0")
        os.system("md5sum %s > %s.md5" % \
                  (wpa_supplicant_conf, wpa_supplicant_conf))
        os.system("sync")
        logger.info("pin pair successful")
    else:
        logger.info("pin pair failed")
    return (state == "COMPLETED")


# Returns:
#   True    associated
#   False   not associated, timeout
def associate(timeout):
    logger.debug("associate")
    wpa.reconfigure()
    return wpa.network_connect(timeout)


def disassociate():
    logger.debug("disassociate")
    wpa.network_disconnect()


# Returns:
#   True    got IP
#   False   error getting IP
def get_ip():
    logger.debug("get_ip")
    udhcpc.start(ifname, hostname="solo")
    ip_mask = ifconfig.ip_mask(ifname)
    if ip_mask is None:
        logger.info("pairing failed: error getting IP address")
        udhcpc.stop()
        return False
    elif ip_mask[0] != solo_ip:
        # This happens if this Solo and another Solo both know the wifi
        # password, and:
        # 1. The controller is paired to and already connected to the other
        #    Solo. This Solo will not get the correct IP unless the controller
        #    restarts.
        # 2. The controller is paired to this Solo, but the other Solo got on
        #    the wifi network first and got the Solo IP. In that case, the
        #    other Solo will get booted off, and this Solo will get the
        #    correct IP when it retries.
        logger.info("pairing failed: not at the fixed solo IP address")
        udhcpc.stop()
        return False
    else:
        logger.info("ip address %s netmask %s", ip_mask[0], ip_mask[1])
        return True


def release_ip():
    logger.debug("release_ip")
    udhcpc.stop()


# Check network link status. If it is good (associated, have Solo IP address),
# return True. Otherwise, make sure everything is down (disassociated, udhcpc
# stopped, no IP) and return False.
#
# Returns:
#   True    associated, udhcpc running, at solo IP
#   False   not associated, udhcpc not running, no IP
def check_link():
    stat = wpa.get_status()
    if ("wpa_state" in stat) and (stat["wpa_state"] == "COMPLETED"):
        # wifi is associated
        ip_mask = ifconfig.ip_mask(ifname)
        if ip_mask and (ip_mask[0] == solo_ip):
            return True
    # something is not right; tear everything down
    network_down()
    return False


# Returns:
#   True    network is up
#   False   button was pushed (network is not up)
def network_up():
    logger.info("bringing up network...")
    if check_link():
        logger.info("network already up")
        return True
    # check_link either confirms the network is up, or makes sure it is
    # completely down
    while True:
        if associate(wifi_connect_timeout):
            if get_ip():
                logger.info("network is up")
                return True
            disassociate()
        # don't do network_remove_all here
        if wait_button(2):
            logger.info("network is down (button detected)")
            return False


def network_down():
    release_ip()
    disassociate()
    wpa.network_remove_all()


# connected to controller, advance runlevel
def go_ready():
    global runlevel_ready
    if not runlevel_ready:
        logger.info("switching to runlevel.READY")
        runlevel.set(runlevel.READY)
        runlevel_ready = True


def set_controller_versions(pkt):
    global controller_sololink_version
    global controller_firmware_version
    sololink = pkt[4:36].strip('\r\n\t\0 ')
    firmware = pkt[36:68].strip('\r\n\t\0 ')
    if controller_sololink_version == sololink and \
       controller_firmware_version == firmware:
        return;
    controller_sololink_version = sololink
    controller_firmware_version = firmware
    try:
        f = open(controller_sololink_version_file, 'w')
        f.write("%s\n" % (controller_sololink_version, ))
        f.close()
    except:
        logger.error("error writing controller sololink version to %s",
                     controller_sololink_version_file)
    try:
        f = open(controller_firmware_version_file, 'w')
        f.write("%s\n" % (controller_firmware_version, ))
        f.close()
    except:
        logger.error("error writing controller firmware version to %s",
                     controller_firmware_version_file)
    logger.info("controller version \"%s\"; firmware \"%s\"",
                controller_sololink_version, controller_firmware_version)


# Returns
#   Only if button pushed before any response from controller
def run_connected():
    global version_mismatch_log_time_us
    ack_received = None
    logger.info("establishing connection...")
    controller_adrs = (controller_ip, controller_link_port)
    confirmed = False
    pending = False
    pair_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pair_sock.bind(("", 0)) # any port
    pair_sock.settimeout(connect_ack_timeout)
    send_error_logged = False
    recv_error_logged = False
    while True:
        need_sleep = False

        if rc_lock.locked():
            locked = 1
        else:
            locked = 0
        logger.debug("locked=%d", locked)

        conn_req = struct.pack("<BBBB32s32s",
                               pair.CMD_CONN_REQ, pair.SYS_SOLO, 0, locked,
                               solo_sololink_version, solo_firmware_version)

        try:
            pair_sock.sendto(conn_req, controller_adrs)
        except Exception as e:
            if not send_error_logged:
                logger.info("error returned from sendto (%s)" % (e))
                send_error_logged = True
            need_sleep = True
            pkt = None
        else:
            # sendto success; reset so we log the next error
            send_error_logged = False

        # If we got an error on send, we'll likely get an error from this
        # recvfrom, leading to the correct processing (same as if we skipped
        # this recvfrom).
        try:
            pkt, adrs = pair_sock.recvfrom(256)
        except socket.timeout:
            need_sleep = False
            pkt = None
        except Exception as e:
            if not recv_error_logged:
                logger.info("error returned from recvfrom (%s)" % (e))
                recv_error_logged = True
            need_sleep = True
            pkt = None
        else:
            # recvfrom success; reset so we log the next error
            recv_error_logged = False

        now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)

        if pkt is None:
            if ack_received is not None and ack_received:
                # first non-reply after ack received
                logger.info("timeout waiting for ack")
                ack_received = False
            if not confirmed and wait_button(0):
                logger.info("pairing button detected")
                network_down()
                return
            if need_sleep:
                # Could be here because of timeout waiting for packet, or
                # socket error (e.g. out of range). If not a timeout, sleep
                # a bit so as not to soak the CPU sending requests.
                time.sleep(connect_request_interval)
            # back to top to send next request
            continue

        # got a reply
        if len(pkt) == pair.CONN_MSG_LEN and \
           ord(pkt[0]) == pair.CMD_CONN_ACK and \
           ord(pkt[1]) == pair.SYS_CONTROLLER:
            if ord(pkt[2]) == pair.YES:
                set_controller_versions(pkt)
                if not confirmed:
                    confirmed = True
                elif ack_received is not None and not ack_received:
                    # previous one timed out
                    logger.info("ack received after timeout")
                ack_received = True
                # Do this even if connection was already confirmed. It is
                # possible that the other side started out on the wrong
                # version, the connection was confirmed, the other side was
                # updated, and now the versions match so we should unlock.
                if (not check_versions) or (solo_sololink_version == controller_sololink_version):
                    rc_lock.unlock_version()
                else:
                    rc_lock.lock_version()
                    # logging is rate-limited here
                    if now_us > version_mismatch_log_time_us:
                        logger.info("version mismatch: solo=\"%s\", controller=\"%s\"",
                                    solo_sololink_version, controller_sololink_version)
                        version_mismatch_log_time_us = now_us + version_mismatch_log_interval_us
                # Change runlevel even if locked or versions incompatible.
                # Apps look better if there is telemetry flowing and shotmgr
                # is running
                go_ready()
            elif ord(pkt[2]) == pair.PEND:
                if not pending:
                    logger.info("connection pending")
                pending = True
            else: # pair.NO
                if not confirmed:
                    # Controller says no. This Solo knows the wifi password
                    # from a previous pairing, but the controller has since
                    # been re-paired to a different Solo.
                    logger.info("connection rejected")
                    network_down()
                    return
                else:
                    # Controller said yes to a previous connect request, but
                    # is now saying no. We are already in runlevel 4;
                    # something is really messed up. Ignore the nack.
                    logger.error("connection was up, now rejected")
        else:
            # mystery packet!
            logger.error("mystery response received: %s",
                         str([ord(c) for c in pkt]))
        time.sleep(connect_request_interval)


# Wait for pairing button
#
# Timeout = None means wait forever, else timeout in seconds
#
# Returns:
#   True    button pushed within timeout
#   False   timeout
def wait_button(timeout=None):
    if timeout is None:
        end_us = None
    else:
        end_us = clock.gettime_us(clock.CLOCK_MONOTONIC) + \
                 int(timeout * 1000000)
    while True:
        if pair_button():
            return True
        if end_us is not None and \
           clock.gettime_us(clock.CLOCK_MONOTONIC) >= end_us:
            return False
        time.sleep(0.1)


def pair_solo():
    logger.info("pairing using %s", ifname)
    # XXX update_config=0 should be default in wpa_supplicant.conf
    wpa.set("update_config", "0")
    while True:
        if is_paired():
            if network_up():
                run_connected()
        else:
            network_down()
            logger.info("waiting for pairing button")
            wait_button()
        pin_pair()


if __name__ == "__main__":

    logging.config.fileConfig(sololink_conf)
    logger = logging.getLogger("pair")

    logger.info("pair_solo.py starting")

    config = ConfigParser.SafeConfigParser()

    # if the config file is not found, an empty list is returned and the "get"
    # operations below fail
    config.read(sololink_conf)

    # read configuration items
    try:
        controller_link_port = config.getint("pairing", "controller_link_port")
        wifi_connect_timeout = \
                config.getfloat("pairing", "wifi_connect_timeout")
        connect_request_interval = \
                config.getfloat("pairing", "connect_request_interval")
        connect_ack_timeout = config.getfloat("pairing", "connect_ack_timeout")
        button_filename = config.get("pairing", "button_filename")
        solo_ip = config.get("solo", "soloIp")
        controller_ip = config.get("solo", "artooIp")
    except:
        logger.error("error reading config from %s", sololink_conf)
        sys.exit(1)

    try:
        check_versions = sololink_config.getboolean("solo", "pairCheckVersions")
    except:
        check_versions = True # default
        logger.info("using default check_versions=%s", str(check_versions))

    # read sololink version
    try:
        f = open(sololink_version_file, 'r')
        solo_sololink_version = f.readline() # still has \n
        solo_sololink_version = solo_sololink_version.strip('\r\n\t\0 ')
    except:
        logger.error("error reading version from %s", sololink_version_file)
        sys.exit(1)

    logger.info("sololink version \"%s\"", solo_sololink_version)

    # read firmware version
    try:
        f = open(firmware_version_file, 'r')
        solo_firmware_version = f.readline() # still has \n
        solo_firmware_version = solo_firmware_version.strip('\r\n\t\0 ')
    except:
        logger.error("error reading version from %s", firmware_version_file)
        solo_firmware_version = "unknown"

    logger.info("firmware version \"%s\"", solo_firmware_version)

    # If /etc/.rc_lock exists, delete it (SOLO-709)
    if os.path.isfile("/etc/.rc_lock"):
        logger.info("deleting /etc/.rc_lock")
        os.unlink("/etc/.rc_lock")

    pair_solo()
    # pair_solo never returns
