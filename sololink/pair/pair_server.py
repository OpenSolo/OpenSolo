#!/usr/bin/env python

# standard python
import ConfigParser
import logging
import logging.config
import re
import select
import socket
import struct
import sys
import time

# sololink, in /usr/bin
import clock
import hostapd_ctrl
import ip_util
import lockout_msg
import pair
import runlevel

# as printed to console and logs
prog_name = "pair_server"

sololink_conf = "/etc/sololink.conf"
pairing_conf = "/log/3dr-pairing.conf"
sololink_version_file = "/VERSION"
firmware_version_file = "/STM_VERSION"
solo_sololink_version_file = "/tmp/PEER_SL_VERSION"
solo_firmware_version_file = "/tmp/PEER_FW_VERSION"

logging.config.fileConfig(sololink_conf)
logger = logging.getLogger("pair")

logger.info("%s starting", prog_name)

sololink_config = ConfigParser.SafeConfigParser()
pairing_config = ConfigParser.SafeConfigParser()

sololink_config.read(sololink_conf)
pairing_config.read(pairing_conf)

# read configuration items
try:
    # controller_link_port = 5501
    controller_link_port = \
            sololink_config.getint("pairing", "controller_link_port")
    # solo_address_file = "/var/run/solo.ip"
    solo_address_file = sololink_config.get("pairing", "solo_address_file")
    # user_confirmation_timeout = 30.0
    user_confirmation_timeout = \
            sololink_config.getfloat("pairing", "user_confirmation_timeout")
    # pair_req_port = 5013
    pair_req_port = sololink_config.getint("solo", "pairReqDestPort")
    # pair_res_port = 5014
    pair_res_port = sololink_config.getint("solo", "pairResDestPort")
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
    controller_sololink_version = f.readline() # still has \n
    controller_sololink_version = controller_sololink_version.strip('\r\n\t\0 ')
except:
    logger.error("error reading version from %s", sololink_version_file)
    sys.exit(1)

logger.info("sololink version \"%s\"", controller_sololink_version)

# read firmware version

try:
    f = open(firmware_version_file, 'r')
    controller_firmware_version = f.readline() # still has \n
    controller_firmware_version = controller_firmware_version.strip('\r\n\t\0 ')
except:
    logger.error("error reading version from %s", firmware_version_file)
    controller_firmware_version = "unknown"

logger.info("firmware version \"%s\"", controller_firmware_version)

user_wait_timeout_us = int(user_confirmation_timeout * 1000000)
user_wait_start_us = None

# It is not critical that the PIN be secret. The reason for using WPS PIN is
# not the PIN's security (it is not), but that we can cause hostapd to ask us
# for the PIN, at which time get confirmation from the user.
secret_pin = 74015887


# States the controller side can be in
#   STATE_IDLE: have not heard from a Solo yet
#   STATE_USER_WAIT: have asked for user approval for a Solo
#   STATE_CONNECTED: have connected to a Solo
#
# Events causing state transitions
#   hostapd: pin request
#   solo: connect request
#   stm32: pair confirm
#   timeout (waiting for user)
#
# Conditions affecting state transitions
#   is message from the paired solo
#   is message from the connected solo
#
# Actions to take on state transitions
#   send pair request to stm32
#   send pair result to stm32
#   send pin response to hostapd
#   send connect/yes to solo
#   send connect/no to solo
#   send connect/pend to solo
#   set paired solo
#   set connected solo
#
# A "paired solo" is a static thing, stored in a file. It is the Solo that we
# will accept a connection from without prompting the user.
#
# A "connected solo" is one that we have gotten a connect request from and
# sent a connect yes to.
#
# A solo becomes the "paired solo" by sending a pin request and having the
# user approve it. The "paired solo" is remembered in a file.
#
# A solo then becomes the "connected solo" by sending a connect request to
# which we respond with a connect yes. The "connected solo" is established
# some time after startup, and once established, cannot change until the
# controller is power cycled.
#
# At power on, there might be a paired solo, but there will not be a connected
# Solo.


STATE_IDLE = 0
STATE_USER_WAIT = 1
STATE_CONNECTED = 2

state_names = [ "IDLE", "USER_WAIT", "CONNECTED" ]

def set_state(new_state):
    global state
    logger.info("%s -> %s", state_names[state], state_names[new_state])
    state = new_state


# information about the Solo we are currently talking to
class Solo:
    # uuid: arrives from Solo with the PIN request, and is given back to
    # hostapd with the PIN reply. Keeping it makes it so hostapd will give the
    # password only to the Solo that the user approved by name (in case there
    # happens to be more than one trying to pair at the same time).
    #
    # mac: used to identify a paired solo, i.e. once a user approves pairing
    # with a particular MAC, future requests from the same MAC do not need
    # approval.
    #
    # name: comes from wpa_supplicant.conf on Solo, and is what is presented
    # to the user for approval.
    def __init__(self):
        self.reset()
    def reset(self):
        self.name = None
        self.mac = None
        self.uuid = None
        self.need_pin = None
        self.confirmed = None
        self.locked = None
        self.sololink_version = None
        self.firmware_version = None
        self.last_msg_us = None
    def set(self, name, mac):
        self.name = name
        self.mac = mac
        self.uuid = None
        self.confirmed = None
        self.locked = None
        self.sololink_version = None
        self.firmware_version = None
        self.last_msg_us = None
    def set_versions(self, sololink, firmware):
        if self.sololink_version == sololink and self.firmware_version == firmware:
            return
        self.sololink_version = sololink
        self.firmware_version = firmware
        try:
            f = open(solo_sololink_version_file, 'w')
            f.write("%s\n" % (sololink, ))
            f.close()
        except:
            logger.error("error writing solo sololink version to %s", solo_sololink_version_file)
        try:
            f = open(solo_firmware_version_file, 'w')
            f.write("%s\n" % (firmware, ))
            f.close()
        except:
            logger.error("error writing solo firmware version to %s", solo_firmware_version_file)
        logger.info("solo version \"%s\"; firmware \"%s\"",
                    solo.sololink_version, solo.firmware_version)


solo = Solo()


# Set Solo's IP in /var/run/solo.ip, then change runlevels
def set_solo(solo_adrs):
    logger.info("connected with %s", str(solo_adrs))
    # write solo address file
    f = open(solo_address_file, "w")
    f.write(solo_adrs[0] + "\n")
    f.close()


# Timeouts all use CLOCK_MONOTONIC so as to not be disturbed by jumps
# in system time. Internal times all have either _s (seconds) or _us
# (microseconds) appended to the name to keep the units straight. Times
# from external sources (i.e. config settings) are all floating-point
# seconds.


# The stm32 module listens on different UDP ports, waiting for messages
# to send down to the STM32.
# pair request messages
stm32_req_sockaddr_remote = ("127.0.0.1", pair_req_port)
# pair result messages
stm32_res_sockaddr_remote = ("127.0.0.1", pair_res_port)

# this server listens on this port; solo contacts this port to pair
pair_sockaddr_local = ("", controller_link_port)


# These come over in the pin-needed message, and so must match the settings in
# Solo's wpa_supplicant.conf file. Requiring these to match just lessens the
# liklihood that we get spurious pin-needed events from whoever happens to be
# out there.
manuf_name = "3D Robotics"
model_name = "Solo"


# Whether we have changed to runlevel.READY yet or not
runlevel_ready = False


# Log a version mismatch once per minute
version_mismatch_log_time_us = 0
version_mismatch_log_interval_us = 60 * 1000000


# If we are connected to a locked solo, but don't hear from it in this long,
# we take down the preflight update screen
solo_locked_msg_timeout_us = 3000000 # 3 sec


# Solo's that have been rejected since power on. Once a user rejects pairing
# for a Solo, that Solo should not cause a prompt again. The blacklist only
# lasts until the next reboot. It can't be persistent, in case a user
# accidently rejects his own Solo.
blacklist = []


# Messages we might send to solo (part of the pairing protocol)
conn_ack_no = struct.pack("<BBBB32s32s", pair.CMD_CONN_ACK,
                          pair.SYS_CONTROLLER, pair.NO, 0,
                          "", "")
conn_ack_yes = struct.pack("<BBBB32s32s", pair.CMD_CONN_ACK,
                           pair.SYS_CONTROLLER, pair.YES, 0,
                           controller_sololink_version,
                           controller_firmware_version)
conn_ack_pend = struct.pack("<BBBB32s32s", pair.CMD_CONN_ACK,
                            pair.SYS_CONTROLLER, pair.PEND, 0,
                            "", "")


# Messages we might send to stm32
# VehicleConnector::MAX_ID_LEN is 32; to be nice, we make sure the names we
# send are always EOS-terminated - max 31 characters + EOS.

def send_pair_request(name):
    if len(name) > 31:
        name = name[:31]
    name = name + "\0"
    logger.debug("sending pair request to stm32 (%s)", name)
    stm32_sock.sendto(name, stm32_req_sockaddr_remote)

def send_pair_result(name):
    if len(name) > 31:
        name = name[:31]
    name = name + "\0"
    logger.debug("sending pair result to stm32 (%s)", name)
    stm32_sock.sendto(name, stm32_res_sockaddr_remote)


def pin_req_valid(pin_req):
    global solo
    # msg is a 9-tuple
    if len(pin_req) != 9:
        solo.reset()
        logger.info("pin request invalid")
        logger.info(pin_req)
        return False
    uuid = pin_req[1]
    mac = pin_req[2]
    name = pin_req[3]
    manufacturer = pin_req[4]
    model_name = pin_req[5]
    model_number = pin_req[6]
    serial_number = pin_req[7]
    device_type = pin_req[8]
    # must be a 3DR Solo (allow model names like "Solo 1" or "Solo 2")
    if manufacturer != "3D Robotics" or model_name.find("Solo") == -1:
        solo.reset()
        logger.info("pin request not from a 3DR Solo")
        logger.info(msg)
        return False
    # must have a UUID in the request, since that's used to send back the PIN
    if uuid is None:
        solo.reset()
        logger.info("pin request has no uuid")
        logger.info(msg)
        return False
    # must have a MAC in the request, since that's used to differentiate Solos
    if mac is None:
        solo.reset()
        logger.info("pin request has no mac")
        logger.info(msg)
        return False
    # pin request is valid
    logger.info("pin request: name=\"%s\", mac=%s, uuid=%s",
                name, mac, uuid)
    if name is None or name == "":
        name = mac
    solo.uuid = uuid
    solo.mac = mac
    solo.name = name
    return True


def check_user_wait_timeout(now_us):
    user_wait_us = now_us - user_wait_start_us;
    if user_wait_us > user_wait_timeout_us:
        # timeout!
        logger.info("timeout waiting for user (%0.3f sec)",
                    user_wait_us / 1000000.0)
        send_pair_result("")
        solo.reset()
        set_state(STATE_IDLE)


# Handle PIN request message from hostapd
#
# Only called when we are in STATE_IDLE and we got a WPS-PIN-NEEDED message
# from hostapd.
#
# Return next state:
#   STATE_IDLE (pin request ignored)
#   STATE_USER_WAIT (asked used to confirm)
#   STATE_CONNECTED (known solo)
def handle_pin_request(now_us, msg):
    global solo
    global user_wait_start_us
    logger.debug("handle_pin_request: %s", msg)
    if not pin_req_valid(msg):
        return STATE_IDLE
    # pin_req_valid sets solo.uuid, solo.mac, and solo.name
    # Has user rejected this solo since power on?
    if solo.mac in blacklist:
        logger.info("pin request from rejected solo; ignoring")
        return STATE_IDLE
    # Is this the paired Solo? (hmm, if so, it forgot its pairing)
    if pairing_config.has_section(solo.mac):
        logger.info("pin request from known solo")
        # send pin reply to hostapd
        hostapd.send_pin(solo.uuid, secret_pin)
        logger.debug("sending pin for uuid %s", solo.uuid)
        solo.confirmed = False
        return STATE_CONNECTED
    else:
        logger.info("pin request from unknown solo; need user confirmation")
        # send pair request to the STM32
        solo.need_pin = True
        send_pair_request(solo.name)
        user_wait_start_us = now_us
        return STATE_USER_WAIT


# True if user accepted pairing
# False if user did not accepted pairing
def pair_confirm_answer(stm32_pkt):
    return (ord(stm32_pkt[0]) != 0)


# validate connect request from solo
# True if packet valid
# False if packet not valid
def connect_request_valid(solo_pkt):
    return (len(solo_pkt) == pair.CONN_MSG_LEN and \
            ord(solo_pkt[0]) == pair.CMD_CONN_REQ and \
            ord(solo_pkt[1]) == pair.SYS_SOLO and \
            ord(solo_pkt[2]) == 0)
            # not checking solo_pkt[3] (locked flag)
            # not checking solo_pkt[4:] (version)


def set_paired_solo(solo):
    logger.info("setting %s as paired solo", solo.mac)
    sections = pairing_config.sections()
    for s in sections:
        pairing_config.remove_section(s)
    pairing_config.add_section(solo.mac)
    pairing_config.set(solo.mac, "name", solo.name)
    f = open(pairing_conf, "w")
    pairing_config.write(f)
    f.close()


def go_ready():
    global runlevel_ready
    if not runlevel_ready:
        logger.info("switching to runlevel.READY")
        runlevel.set(runlevel.READY)
        runlevel_ready = True


# stm32 interface socket. Send the pair request to the stm32 module using this
# socket, then get a pair confirm from the stm32 module. stm32_sock is not
# bound (gets INADDR_ANY and a random port).
stm32_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

pair_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
pair_sock.bind(pair_sockaddr_local)


# hostapd control interface
hostapd = hostapd_ctrl.HostapdCtrl("wlan0-ap")

if not hostapd.attach(2.0):
    logger.error("can't attach to hostapd")
    sys.exit(1)


#
# State transition loop
#

state = STATE_IDLE

while True:

    source_adrs = None
    timeout = False

    # Could get message from:
    #   hostapd (pin request)
    #   solo (connect request)
    #   stm32 (pair confirm)
    # ...or timeout waiting for a message
    ready = select.select([hostapd.sock, stm32_sock, pair_sock], [], [], 1)

    # This is the only place the clock is read. If it is needed below (e.g.
    # for user_wait_start_us), this value is used. Reading it again can lead
    # to the condition where user_wait_start_us is temporarily later than
    # now_us (it should always be earlier).
    now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)

    if hostapd.sock in ready[0]:
        # Can get several messages from hostapd, but we only respond to
        # pin request
        pkt = hostapd.sock.recv(256)
        #logger.debug("%s: %s", prog_name, pkt)
        msg = hostapd.parse(pkt)
        # Ignore it we are not in STATE_IDLE or if it is not a pin request.
        if state != STATE_IDLE:
            logger.debug("ignoring message %s (not STATE_IDLE)", str(msg[0]))
        elif msg[0] != "WPS-PIN-NEEDED":
            logger.debug("ignoring message %s", str(msg[0]))
        else:
            set_state(handle_pin_request(now_us, msg))

    elif stm32_sock in ready[0]:
        # The only message from the STM32 we respond to is a pair_confirm,
        # and we only respond to that if we are in STATE_USER_WAIT.
        pkt = stm32_sock.recv(256)
        logger.debug("message from stm32: %s", str([ord(c) for c in pkt]))
        if state != STATE_USER_WAIT:
            logger.debug("not STATE_USER_WAIT; ignoring message")
        elif pair_confirm_answer(pkt):
            logger.debug("user accepted pairing")
            set_paired_solo(solo)
            if solo.need_pin:
                logger.debug("sending pin %d for uuid %s",
                             secret_pin, solo.uuid)
                hostapd.send_pin(solo.uuid, secret_pin)
            solo.confirmed = False
            set_state(STATE_CONNECTED)
        else:
            logger.info("user rejected pairing")
            send_pair_result("")
            blacklist.append(solo.mac)
            logger.info("blacklist: %s", str(blacklist))
            solo.reset()
            set_state(STATE_IDLE)

    elif pair_sock in ready[0]:
        # message from solo
        pkt, source_adrs = pair_sock.recvfrom(256)
        # the only valid message is a connect request
        if not connect_request_valid(pkt):
            logger.info("unknown message from %s", str(source_adrs))
            # ignore it
        else:
            source_mac = ip_util.get_ip_mac(source_adrs[0])
            solo_locked = ((ord(pkt[3]) & pair.DATA_LOCKED) != 0)
            # source_mac might be None
            if source_mac is not None:
                logger.debug("connect request from %s", str(source_mac))
                if state == STATE_CONNECTED:
                    if source_mac == solo.mac:
                        logger.debug("send CONN_ACK (yes)")
                        pair_sock.sendto(conn_ack_yes, source_adrs)
                        solo.set_versions(pkt[4:36].strip('\r\n\t\0 '),
                                          pkt[36:68].strip('\r\n\t\0 '))
                        if not solo.confirmed:
                            send_pair_result(solo.name)
                            set_solo(source_adrs)
                            solo.confirmed = True
                        # look for changes in solo's lock state
                        if solo.locked is None:
                            # This happens when the user first confirms
                            # pairing; lock is not handled until after the
                            # pairing process (here).
                            if solo_locked:
                                # paired with a locked solo
                                logger.info("connected to locked solo")
                                lockout_msg.send_lock()
                            else:
                                logger.info("connected to unlocked solo")
                                # don't need to send an unlock message
                        elif not solo.locked:
                            # This is the usual case while flying; solo is not
                            # locked, and we'll find solo_locked (from the
                            # message) to be false
                            if solo_locked:
                                # solo was unlocked, but is now locked
                                # uncommon!
                                logger.info("solo is now locked")
                                lockout_msg.send_lock()
                        else: # solo.locked
                            if not solo_locked:
                                # solo was locked, and is now unlocked
                                # common when factory testing
                                logger.info("solo is now unlocked")
                                lockout_msg.send_unlock()
                        solo.locked = solo_locked
                        # check for version mismatch
                        if check_versions and (solo.sololink_version != controller_sololink_version):
                            # version mismatch - update required
                            # this really only needs to be sent once
                            lockout_msg.send_lock()
                            if now_us > version_mismatch_log_time_us:
                                logger.info("version mismatch: solo=\"%s\", controller=\"%s\"",
                                            solo.sololink_version, controller_sololink_version)
                                version_mismatch_log_time_us = now_us + version_mismatch_log_interval_us
                            # XXX updating solo to matching version without
                            # restarting controller is probably not handled
                            # correctly
                        # change runlevel even if locked or versions incompatible
                        # apps look better if there is telemetry flowing and shotmgr is running
                        go_ready()
                        # remember the last time we heard from the connected solo
                        solo.last_msg_us = now_us
                    else:
                        # we have a connected solo, but the message is from a different solo
                        logger.info("send CONN_ACK (no)")
                        pair_sock.sendto(conn_ack_no, source_adrs)
                elif state == STATE_IDLE:
                    # is this the paired Solo?
                    if pairing_config.has_section(source_mac):
                        logger.info("connection request from known solo: " + \
                                    "send CONN_ACK (yes)")
                        pair_sock.sendto(conn_ack_yes, source_adrs)
                        name = pairing_config.get(source_mac, "name")
                        solo.set(name, source_mac)
                        solo.confirmed = True
                        solo.locked = solo_locked
                        # strip whitespace and \0
                        solo.set_versions(pkt[4:36].strip('\r\n\t\0 '),
                                          pkt[36:68].strip('\r\n\t\0 '))
                        set_state(STATE_CONNECTED)
                        set_solo(source_adrs)
                        if solo.locked:
                            # solo is locked - update required
                            lockout_msg.send_lock()
                            logger.info("connected to locked solo: solo=\"%s\", controller=\"%s\"",
                                        solo.sololink_version, controller_sololink_version)
                        elif check_versions and (solo.sololink_version != controller_sololink_version):
                            # version mismatch - update required
                            lockout_msg.send_lock()
                            logger.info("version mismatch: solo=\"%s\", controller=\"%s\"",
                                        solo.sololink_version, controller_sololink_version)
                            version_mismatch_log_time_us = now_us + version_mismatch_log_interval_us
                        # change runlevel even if locked or versions incompatible
                        # apps look better if there is telemetry flowing and shotmgr is running
                        go_ready()
                        # remember the last time we heard from the connected solo
                        solo.last_msg_us = now_us
                        # There is an edge case here, probably only stimulated
                        # by forcing it while testing: Artoo is entering its
                        # CONNECTED state. If one unpairs the Solo and reboots
                        # it, then Solo will come up and when the pair button is
                        # pressed, send a PIN request. This Artoo will not respond
                        # to it because it went straight from IDLE to CONNECTED.
                        # We cannot pre-load the PIN into hostapd at this point
                        # because we do not know the Solo's UUID. Artoo must be
                        # restarted to handle that case.
                    elif source_mac in blacklist:
                        # User has rejected this Solo since power on
                        logger.info("connection request from rejected solo: " + \
                                    "send CONN_ACK (no)")
                        pair_sock.sendto(conn_ack_no, source_adrs)
                        # stay in IDLE
                    else:
                        logger.info("connection request from unknown solo: " + \
                                    "send CONN_ACK (pending)")
                        pair_sock.sendto(conn_ack_pend, source_adrs)
                        # get from connect request message
                        # XXX generate it for now
                        name = "Solo " + source_mac[9:11] + \
                            source_mac[12:14] + source_mac[15:17]
                        solo.set(name, source_mac)
                        solo.need_pin = False
                        send_pair_request(solo.name)
                        user_wait_start_us = now_us
                        # Don't check lockout and don't set solo.locked; need
                        # to allow pairing screens. Lockout is checked after
                        # pairing is confirmed.
                        set_state(STATE_USER_WAIT)
                else: # STATE_USER_WAIT
                    if solo.mac == source_mac:
                        pair_sock.sendto(conn_ack_pend, source_adrs)
                    else:
                        pair_sock.sendto(conn_ack_no, source_adrs)
            ### if source_mac is not None

    # all cases: check for timeout in STATE_USER_WAIT
    if state == STATE_USER_WAIT:
        check_user_wait_timeout(now_us)

    # All cases: check for timeout since we last heard from connected solo
    # The purpose of this check is for the locked build case: If solo is
    # turned off, we want to switch from "preflight update" to "waiting for
    # solo".
    if state == STATE_CONNECTED and \
        solo.locked and \
        (now_us - solo.last_msg_us) > solo_locked_msg_timeout_us:
        # this causes the desired screen switch, but we stat connected
        solo.locked = None
        lockout_msg.send_unlock()

# end while
