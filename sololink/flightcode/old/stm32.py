#!/usr/bin/env python

# Receive and handle messages from the STM32: stm32.receiver waits for messages
# from the STM32. When one arrives, strip off the one-byte packet ID, and call
# a handler based on the packet ID.
#
#                                      |--> DSM -----------> stm32_rc
#                                      |
#                                      |--> SYSINFO -------> stm32_sysinfo
# STM32 --> slip --> stm32.receiver -->|
#                                      |--> MAVLINK -------> stm32_mavlink
#                                      |
#                                      |--> PAIR_CONFIRM --> stm32_pairCnf
#
# To send messages to the STM32, write them to a UDP port, where the port
# used determines the message ID used. The stm32.sender function is called
# after each incoming RC packet, and if there is anything in any of the UDP
# ports, it prepends the one-byte message ID and sends it to the STM32.
#
# mavlink --> udp -->|
#                    |
# sysinfo --> udp -->|
#                    |--> select --> stm32.sender --> slip --> STM32
# pairReq --> udp -->|
#                    |
# pairCnf --> udp -->|
#
# The slip object is given an interface that can send/receive data. Normally
# it is the serial port to the STM32, but for testing it can be a TCP socket
# to the STM32 "simulator" (see stm32_sim.py).

import ConfigParser
import datetime
import logd
import logging
import logging.config
import os
import re
import select
import serial
import simple_stats
import slip
import socket
import struct
import sys
import threading
import time

from stm32_defs import *


if True:
    configFileName = "/etc/sololink.conf"
    soloAddressFileName = "/var/run/solo.ip"
else:
    print "USING DEBUG FILE NAMES"
    configFileName = "./sololink.conf"
    soloAddressFileName = "./solo.ip"


logging.config.fileConfig(configFileName)
logger = logging.getLogger("stm32")

logger.info("starting (20141114_1132)")

config = ConfigParser.SafeConfigParser()
config.read(configFileName)


### These could be in a solo subclass of ConfigParser

def configGetString(optName):
    try:
        value = config.get("solo", optName)
        return value
    except ConfigParser.NoOptionError:
        logger.error("%s not found in %s", optName, configFileName)
        raise # pass it on up

def configGetInt(optName):
    try:
        value = config.getint("solo", optName)
        return value
    except ConfigParser.NoOptionError:
        logger.error("%s not found in %s", optName, configFileName)
        raise # pass it on up

###

### This should be in a subclass of ConfigParser
# Parse string into a list of IP address/port tuples, e.g.
# "" -> []
# "10.1.1.1:5000" -> [("10.1.1.1", 5000)]
# "10.1.1.1:5000;10.1.1.100:5001" -> [("10.1.1.1", 5000), ("10.1.1.100", 5001)]
def parseIps(stringIps):
    if len(stringIps) == 0:
        listIps = []
    else:
        listIps = re.split(";", stringIps)
        for i in range(len(listIps)):
            # ipPort should be e.g. "10.1.1.1:5001"
            tupleIp = re.split(":", listIps[i])
            tupleIp[1] = int(tupleIp[1])
            listIps[i] = tuple(tupleIp)
    return listIps
###

# Solo's IP address
soloIp = None

# Default port to which RC packets will be sent (at IP soloIp)
rcDestPort = configGetInt("rcDestPort")

pktIdToTypeName = [
    "NOP",
    "DSM",
    "CAL",
    "SYSINFO",
    "MAVLINK",
    "SET_RAW",
    "RAW_RPT",
    "PAIR_REQ",
    "PAIR_CNF",
    "PAIR_RES"
]

# i.MX6 -> STM32 message ports. A message arriving on one of these ports will
# be given the STM32 protocol packet ID and slipped to the STM32.
mavDestPort = configGetInt("mavDestPort")
sysDestPort = configGetInt("sysDestPort")
pairReqDestPort = configGetInt("pairReqDestPort")
pairResDestPort = configGetInt("pairResDestPort")

# STM32 serial port
stm32Dev = configGetString("stm32Dev")
stm32Baud = configGetInt("stm32Baud")

# Timeout for reading the next packet from the slip interface
portTimeout = 0.2



setSoloIpErrorLogged = False

def setSoloIp():
    """attempt to set solo's ip address

    Pairing module puts solo's address in soloAddressFileName when the
    connection is first established. It is expected to be on a non-
    persistent file system so it does not exist until solo is detected
    after each boot.
    """
    global soloIp

    try:
        f = open(soloAddressFileName)
    except IOError:
        # can't open file; no connection to solo yet
        return False
    fileData = f.read()
    f.close()

    # fileData should simply be an IP address
    soloIp = fileData.strip()
    logger.info("using solo IP address %s", soloIp)

    return True



# A UDP socket that has an associated packet ID. The idea is that each type
# of outgoing packet has an associated UDP port. To send a packet of a
# particular type, a message is sent to that type's port. The sender thread
# can then select on a set of UDP sockets, and when data arrives on one, it
# can get the packet ID associated with that socket.
class idSocket(socket.socket):
    def __init__(self, id):
        socket.socket.__init__(self, socket.AF_INET, socket.SOCK_DGRAM)
        self._id = id
    def id(self):
        return self._id



class stm32():


    def __init__(self, port, logPipe):
        self._slip = slip.slip(port)
        self._stats = simple_stats.SimpleStats()
        # The MAVLink uplink address is learned the first time we get a
        # MAVLink packet from Solo.
        self._mavUplinkAddress = None
        # The pairing socket address is learned the first time we get a
        # pair request packet from the pairing server module.
        self._pairingAddress = None
        # Message handlers.
        # Receiver thread uses these to process messages received from STM32.
        self.rc = stm32_rc(self)
        self.mavlink = stm32_mavlink(self)
        self.sysinfo = stm32_sysinfo(self)
        self.pairCnf = stm32_pairConfirm(self)
        # debug counts
        self._msgInCounts = {}
        self._msgOutCounts = {}
        self._junkCounts = {}
        # control how often we log progress and junk messages
        self._logProgressInterval = datetime.timedelta(seconds=30) # =None to never log
        self._logProgressLast = None
        self._logJunkInterval = datetime.timedelta(seconds=5) # =None to never log
        self._logJunkLast = None
        # Packet log
        self._logPipe = logPipe
        # Sender thread (sends messages to STM32)
        self._inSocks = [ ]
        # A packet arriving on one of these UDP ports is sent to the STM32
        # with the given packet ID
        self.addInput(mavDestPort, PKT_ID_MAVLINK)
        self.addInput(sysDestPort, PKT_ID_SYSINFO)
        self.addInput(pairReqDestPort, PKT_ID_PAIR_REQUEST)
        self.addInput(pairResDestPort, PKT_ID_PAIR_RESULT)
        # Receiver thread (receives messages from STM32)
        self._quit = False
        self._timeout = False
        self._receiver = threading.Thread(name = 'stm32.receiver',
                                          target = stm32.receiver,
                                          args = (self, ))
        self._receiver.daemon = True
        self._sender = threading.Thread(name = 'stm32.sender',
                                          target = stm32.sender,
                                          args = (self, ))
        self._sender.daemon = True
        # Start thread
        self._receiver.start()
        self._sender.start()


    def exit(self):
        self._quit = True
        self._receiver.join(1.0)
        if self._receiver.isAlive():
            logger.error("timeout waiting for receiver thread to exit")
        self._sender.join(1.0)
        if self._sender.isAlive():
            logger.error("timeout waiting for sender thread to exit")


    def logProgress(self, msgInType, msgOutType):
        # count incoming messages of each type
        if msgInType is not None:
            if msgInType not in self._msgInCounts:
                self._msgInCounts[msgInType] = 0
            self._msgInCounts[msgInType] += 1
        # count outgoing messages of each type
        if msgOutType is not None:
            if msgOutType not in self._msgOutCounts:
                self._msgOutCounts[msgOutType] = 0
            self._msgOutCounts[msgOutType] += 1
        # periodically print counts
        now = datetime.datetime.now()
        if (self._logProgressInterval is not None) and \
           ((self._logProgressLast is None) or \
            ((now - self._logProgressLast) >= self._logProgressInterval)):
            logger.info("messages in:  %s", str(self._msgInCounts))
            logger.info("messages out: %s", str(self._msgOutCounts))
            if self._stats.count() > 0:
                logger.info("dsm: n=%d avg=%0.0f min=%0.0f max=%0.0f stdev=%0.1f",
                            self._stats.count(), self._stats.average(),
                            self._stats.min(), self._stats.max(),
                            self._stats.stdev())
                self._stats.reset()
            self._logProgressLast = now


    def logJunk(self, junkType):
        now = datetime.datetime.now()
        if junkType not in self._junkCounts:
            self._junkCounts[junkType] = 0
        self._junkCounts[junkType] += 1
        if (self._logJunkInterval is not None) and \
           ((self._logJunkLast is None) or \
            ((now - self._logJunkLast) >= self._logJunkInterval)):
            logger.info("junk: stm32 %s, slip %s",
                        str(self._junkCounts), str(self._slip.counts))
            self._logJunkLast = now


    def logPacket(self, pktTime, pkt):
        # don't log unless Solo is connected
        if soloIp is None:
            return
        logd.logStm32Packet(pktTime, pkt)


    # Receiver thread waits for a packet to arrive from the STM32 over the
    # serial port, then based on the packet ID, gives it to one of the message
    # handlers. This thread is normally blocked on the serial port; the
    # message handlers should not block.
    #
    # If the recv function returns (None, None), then there was a timeout
    # waiting for data.
    def receiver(self):
        logger.info("stm32.receiver running")

        self.packetLogger = None
        #self.packetLogger = logd.Stm32Logger(self._logPipe)

        if self.packetLogger:
            now = datetime.datetime.now()
            self.packetLogger.log_packet(now, "\0start " + str(now))

        pktTimeDsmLast = None

        while True:

            pktTime, pkt = self._slip.recv()

            if self._quit:
                break

            if pktTime is None or pkt is None:
                self.logJunk("TIMEOUT")
                self._timeout = True
                continue
            self._timeout = False

            if len(pkt) < 1:
                self.logJunk("ZERO")
                continue

            if self.packetLogger:
                self.packetLogger.log_packet(pktTime, "".join(pkt))

            pktId = ord(pkt[0])

            try:
                typeName = pktIdToTypeName[pktId]
            except:
                logger.info("stm32.receiver: %s", [hex(ord(c)) for c in pkt])
                typeName = "UNKNOWN"

            if pktId == PKT_ID_NOP:
                self.logJunk(typeName)
            elif pktId == PKT_ID_DSM:
                self.rc.handle(pktTime, pkt[1:])
                # update stats
                if pktTimeDsmLast is not None:
                    delta_us = (pktTime - pktTimeDsmLast).total_seconds() * 1000000
                    self._stats.update(delta_us)
                pktTimeDsmLast = pktTime
                # handle outgoing messages
#                self.ender()
            elif pktId == PKT_ID_CAL:
                pass
            elif pktId == PKT_ID_SYSINFO:
                self.sysinfo.handle(pktTime, pkt[1:])
            elif pktId == PKT_ID_MAVLINK:
                # Upstream MAVLink (Artoo -> Solo)
                self.mavlink.handle(pktTime, pkt[1:])
            elif pktId == PKT_ID_PAIR_CONFIRM:
                self.pairCnf.handle(pktTime, pkt[1:])
            elif pktId == PKT_ID_SHUTDOWN_REQUEST:
                #Shutdown gracefully...
                logger.info("received shutdown request");
                os.system("shutdown -h now")
            else:
                # Don't desync here. We did just get an END, after all.
                self.logJunk(typeName)

            self.logProgress(typeName, None)

        # end while True

        if self.packetLogger:
            now = datetime.datetime.now()
            self.packetLogger.log_packet(now, "\0exit " + str(now))
            self.packetLogger.uninit()

        logger.info("stm32.receiver exiting")


    # Sender thread waits for packets to arrive on any of the UDP ports. When
    # a message arrives, it is prepended with the packet ID and sent to the
    # STM32. This is the only thread that is allowed to write to the serial
    # port. This thread is normally blocked in the select on the UDP ports.
    # If there is regular traffic on at least one of the UDP ports, then the
    # _quit request will be noticed and the thread will exit when requested.
    # Otherwise, it will be killed when the main module terminates, and could
    # cause an ugly but harmless exception on the way out. The select could
    # be done with a time to mitigate this, but that's TBD (the normal case is
    # that MAVLink is coming in often enough so the timeout is not needed).
    def sender(self):

        while True:

            if self._quit:
                break

            ready = select.select(self._inSocks, [], []) #Blocking

            for sock in ready[0]:

                pkt, srcAdrs = sock.recvfrom(4096)

                pktId = sock.id()

                try:
                    typeName = pktIdToTypeName[pktId]
                except:
                    typeName = "UNKNOWN"

                if self._mavUplinkAddress is None and pktId == PKT_ID_MAVLINK:
                    # Save source address; it is the destination address for
                    # the mavlink uplink.
                    # srcAdrs is a ("string", port) tuple.
                    self._mavUplinkAddress = srcAdrs
                    logger.info("mavlink destination address: %s",
                                str(self._mavUplinkAddress));

                if self._pairingAddress is None and pktId == PKT_ID_PAIR_REQUEST:
                    # Save source address; pairing confirm will go there
                    self._pairingAddress = srcAdrs
                    logger.info("pairing destination address: %s",
                                str(self._pairingAddress));

                self._slip.send(chr(pktId) + pkt)

                self.logProgress(None, typeName)

            ### end for sock in ready[0]
        ### End while True


    # Add a new UDP port to listen on. When a packet arrives, it will be
    # forwarded to the STM32 with the supplied packet ID. All addInput() calls
    # are expected to be done before the first call to sender().
    def addInput(self, portNum, pktId):
        sock = idSocket(pktId)
        sock.bind(('', portNum))
        self._inSocks.append(sock)



class stm32_sysinfo():

    def __init__(self, owner):
        self._owner = owner
        self._uniqueId = None
        self._hwVersion = None
        self._swVersion = None
        self.updateTime = datetime.datetime.now()


    def handle(self, pktTime, pkt):
        """Handle one "sysinfo" message from STM32.

        The packet ID has already been stripped from the front. The packet as
        received here looks like this (names are from artoo source):

        --DATA--------------  --LENGTH--------------------  --AS OF 9/25/14---
        Sys::UniqueId         Sys::UniqueIdLen              12 bytes
        Sys::HardwareVersion  sizeof(Sys::HardwareVersion)  2 bytes
        Version::str()        strlen(Version::str())        variable
        --------------------  ----------------------------  ------------------

        The UniqueId and HardwareVersion are (9/25/14) compiled-in, and the
        version string is generated at build time from `git describe --tags`.
        """
        pktLen = len(pkt)
        now = datetime.datetime.now()
        if pktLen > 0:

            if pktLen < 14:
                # malformed packet received - log it
                self._owner.logJunk("BAD_SYS")
                return

            newSysinfo = "".join(pkt)
            newUniqueId = newSysinfo[:12]
            # struct.unpack_from always returns a tuple
            newHwVersion = struct.unpack_from('<H', newSysinfo, 12)[0]
            # XXX verify this does not throw exc if length is 14
            newSwVersion = newSysinfo[14:]
            # log it the first time
            if self._uniqueId is None:
                ustr = "%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x" % \
                       tuple([ord(c) for c in newUniqueId])
                logger.info("unique ID=%s", ustr)
                logger.info("HW version=0x%04x", newHwVersion)
                logger.info("SW version=\"%s\"", newSwVersion)
            self._uniqueId = newUniqueId
            self._hwVersion = newHwVersion
            self._swVersion = newSwVersion
            self.updateTime = datetime.datetime.now()



class stm32_rc():

    PRINT_INTERVALS = 1
    PRINT_PACKETS = 2
    PRINT_GAPS = 4


    def __init__(self, owner):
        self._owner = owner
        self._sequence = 0
        # (datetime) epoch; everything references back to this
        self._epoch = datetime.datetime(1970, 1, 1)
        # (integer) time of most recent packet
        self._timePrev_us = 0
        self._ipAddress = None # tuple, ("ipAddress", portNum)
        self._sock = None
        self._dbg_printInterval_us = 0
        self._dbg_printLast_us = 0
        self._dbg_printDetails = 0


    def debug(self, printInterval_us = 0, printDetails = 0):
        """Set debug output level.

        printInterval_us:
            if zero, don't print any packets
            if nonzero, print at most every printInterval_us microseconds
        printDetails:
            OR of one or more of stm32_rc.PRINT_* constants
        """
        self._dbg_printInterval_us = printInterval_us
        self._dbg_printLast_us = 0 # print next one, then start doing interval
        self._dbg_printDetails = printDetails


    def setDestination(self, ipAddress=None):
        """Set destination IP address and port for RC packets."""
        # Close socket such that handle() can assume that if self._sock is
        # not None, it can be used for sending
        if self._sock is not None:
            tempSock = self._sock
            self._sock = None
            self._ipAddress = None
            tempSock.close()
        # Open socket such that if self._sock is not None, _ipAddress is valid
        # and the socket is ready to send
        if ipAddress is not None:
            self._ipAddress = ipAddress
            tempSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            tempSock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0xFF)
            self._sock = tempSock


    def handle(self, pktTime, pkt):
        """Handle one RC packet from STM32.

        The packet ID has already been stripped from the front. The packet as
        received has the channel data starting at pkt[0]. Channel data is
        little-endian.

        Start
        Byte    Size    Description
         0      2       Channel 0
         2      2       Channel 1
         4      2       Channel 2
         6      2       Channel 3
         8      2       Channel 4
        10      2       Channel 5
        12      2       Channel 6
        14      2       Channel 7
        16 (packet length)

        A packet as sent to a UDP port has the following format. All fields
        are little-endian.

        Start
        Byte    Size    Description
        0       8       Timestamp, usec since stm32 process started
        8       2       Sequence number
        10      2       Channel 0
        12      2       Channel 1
        14      2       Channel 2
        16      2       Channel 3
        18      2       Channel 4
        20      2       Channel 5
        22      2       Channel 6
        24      2       Channel 7
        26 (packet length)
        """

        # If the destination address for RC packets is not yet known, check to
        # see if it is known now.
        if self._sock is None:
            if setSoloIp():
                self.setDestination((soloIp, rcDestPort))
            # This packet is already delayed a bit due to the above; drop it.
            # The next one will go to the new address if setSoloIp worked.
            return

        # A packet is "good" if its length is even (whole number of channels).
        # Further checking may be done further downstream (e.g. range check
        # the number of channels).
        pktLen = len(pkt)
        if (pktLen & 1) != 0:
            self._owner.logJunk("BAD_RC")
            return

        # pktTime is datetime
        # packet times are since epoch
        pktTime = pktTime - self._epoch
        pktTime_s = (pktTime.days * 86400) + pktTime.seconds
        pktTime_us = pktTime.microseconds

        # Pack the timestamp and id little endian to match ADC data
        # (pktTime_us first, then pktTime_s)
        s = struct.pack('<IIH', pktTime_us, pktTime_s, self._sequence) \
          + "".join(pkt)

        if self._dbg_printInterval_us != 0 and \
           (self._dbg_printLast_us == 0 or \
            (pktTime_us - self._dbg_printLast_us) >= self._dbg_printInterval_us):
            interval_us = pktTime_us - self._timePrev_us
            msg = ""
            if self._dbg_printDetails & stm32_rc.PRINT_INTERVALS:
                msg += str(pktTime_us - self._timePrev_us)
            if self._dbg_printDetails & stm32_rc.PRINT_PACKETS:
                msg += str(struct.unpack("<QHHHHHHHHH", s))
            if self._dbg_printDetails & stm32_rc.PRINT_GAPS:
                if interval_us > 21000:
                    msg += "GAP = " + str(interval_us) + " us"
            if msg != "":
                logger.info(msg)
                #print msg
            self._dbg_printLast_us = pktTime_us

        self._sock.sendto(s, self._ipAddress)

        self._timePrev_us = pktTime_us
        self._sequence = (self._sequence + 1) % 0xffff



class stm32_mavlink():

    def __init__(self, owner):
        self._owner = owner
        self._destAddress = None
        self._destSock = None

    def handle(self, pktTime, pkt):
        """Handle one MAVLink packet from STM32.

        Forwarded to Solo (Pixhawk) if we know the UDP port number to send to.
        The UDP port number is captured and saved the first time we get a
        MAVLink packet from Solo. Until then, uplink MAVLink packets are
        dropped, with an error logged.
        """
        if self._destAddress is None:
            self._destAddress = self._owner._mavUplinkAddress

        # _destAddress is still None if _mavUplinkAddress is still None
        # (no MAVLink received from Solo yet)
        if self._destAddress is None:
            logger.error("MAVLink packet from STM32 dropped (no destination)")
            logger.error("%s", [hex(ord(c)) for c in pkt].__str__())
        else:
            # create socket on first use
            if self._destSock is None:
                self._destSock = socket.socket(socket.AF_INET,
                                               socket.SOCK_DGRAM)
            self._destSock.sendto("".join(pkt), self._destAddress)


class stm32_pairConfirm():

    def __init__(self, owner):
        self._owner = owner

    def handle(self, pktTime, pkt):
        """Handle pair confirm packet from the STM32."""
        logger.info("pair confirm for \"%s\"", "".join(pkt))
        if self._owner._pairingAddress is None:
            logger.error("pairing address not set! (dropping pair confirm)")
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            confirm = struct.pack("!BBB", 3, 1, 1)
            sock.sendto(confirm, self._owner._pairingAddress)



# Provide read() and write() methods identical to those of a serial port.
# Mainly, read() defaults to one byte. This is for testing when we are using
# the simulated STM32 via TCP.
class sock1():
    def __init__(self, sock):
        self._sock = sock
    def read(self):
        # socket raises exception when it times out; serial port just
        # returns no data
        try:
            b = self._sock.recv(1)
        except socket.timeout:
            b = ""
        return b
    def write(self, c):
        self._sock.sendall(c)



def createTcpPort(address):
    logger.info("connecting to %s", str(address))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(address)
    sock.settimeout(portTimeout)
    return sock1(sock)



def createSerialPort(device, baud):
    try:
        logger.info("opening %s at %d", device, baud)
        # Opening the port may raise serial.SerialException; let that pass on
        # up. The timeout is intended to be several times the minimum packet
        # interval, i.e. for RC packets arriving every 20 msec, a timeout of
        # 200 msec (x10) should work to detect when data stops coming in.
        return serial.Serial(port=device, baudrate=baud, timeout=portTimeout)
    except serial.SerialException as excOpen:
        logger.error(excOpen.__str__())
        sys.exit(1)
    except:
        logger.error(sys.exc_info()[0])
        sys.exit(1)



def main(port, logPipe):

    # 'port' is anything with .read() and .write() methods, where .read returns
    # one byte, and .write writes however many bytes are supplied.
    s = stm32(port, logPipe)

    # Ping the STM32 periodically to make sure everything is okay, including
    # the send thread, the receive thread, and the STM32 itself. If any pieces
    # are stuck, this script exits, killing both threads, and init restarts
    # it all.

    # We use the sysinfo message as a "ping". Something like a real ping (with
    # less data returned) might be better.

    pingSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    pingInterval = datetime.timedelta(seconds=1)

    # can't do timedelta * float
    pingTimeout = 3 * pingInterval + pingInterval / 2

    while True:
        pingSock.sendto('', ('127.0.0.1', sysDestPort))
        time.sleep(pingInterval.total_seconds())
        age = datetime.datetime.now() - s.sysinfo.updateTime
        # Can miss 2, but missing 3 means something is wrong
        # If none have been missed, "age" will be approximately 1; could be just
        # less than 1 or just more than 1. Similar for one missed; age will be
        # about 2, or two missed; age will be about 3. That is why 3.5
        # (calculated above) is the threshold to detect three missed.
        if age > pingTimeout:
            # Exiting this thread causes the stm32 threads to be terminated;
            # the init process should restart everything
            break

    # Tell the receiver thread to quit gracefully, then wait for it do do so
    s.exit()

    logger.error("stm32 not responding; exiting")



if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser("stm32.py [options]")
    parser.add_option("--tcp", dest="tcpAdrs", type="string", default=None,
                      help="STM32 at TCP address:port")
    parser.add_option("--rc", dest="rcAdrs", type="string", default=None,
                      help="destination address:port for RC packets")
    parser.add_option("--log", dest="logPipe", type="string", default=None,
                      help="packet log pipe file name")
    (opts, args) = parser.parse_args()

    if opts.tcpAdrs:
        # opts.tcpAdrs should be of the form "127.0.0.1:55055"
        address = parseIps(opts.tcpAdrs)
        # address is a list of tuples, each ("ipAdrs", portNum) - use 1st one
        port = createTcpPort(address[0])
    else:
        port = createSerialPort(stm32Dev, stm32Baud)

    if opts.rcAdrs:
        # opts.rcAdrs should be of the form "10.0.0.1:5005"
        address = parseIps(opts.rcAdrs)
        # address is a list of tuples, each ("ipAdrs", portNum) - use 1st one
        soloIp = address[0][0]

    if opts.logPipe:
        logPipe = opts.logPipe
    else:
        logPipe = "/var/run/logd"

    main(port, logPipe)

# Testing at the python prompt:
#
# >>> import stm32
# >>> port = stm32.createTcpPort(('127.0.0.1', 55055))
# >>> stm32.main(port)
