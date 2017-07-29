#!/usr/bin/env python

import datetime
import slip
import socket
import struct
import threading
import time
from optparse import OptionParser
from pymavlink import mavutil


DEFAULT_PORT = 55055

RC_PKT_INTERVAL = datetime.timedelta(seconds=0, milliseconds=20)

rcChannels = [1500, 1500, 1500, 1500, 0, 1500, 0, 0]

# Packet IDs. These must match "enum MsgID" in artoo/src/hostprotocol.h.
PKT_ID_NOP = 0
PKT_ID_DSM = 1
PKT_ID_CAL = 2
PKT_ID_SYSINFO = 3
PKT_ID_MAVLINK = 4
PKT_ID_SET_RAW_IO = 5
PKT_ID_RAW_IO_REPORT = 6
PKT_ID_PAIR_REQUEST = 7
PKT_ID_PAIR_CONFIRM = 8
PKT_ID_PAIR_RESULT = 9


# Protection for multiple threads calling slip.send().
# slip.send() does not need to be thread safe in the "real" version, so we
# don't burden it with the lock.
slipSendLock = threading.Lock()


# RC packet thread
# Read global control settings and emit packets at RC packet rate
def rcThreadRun(slipIf):
    nextPacketTime = datetime.datetime.now() + RC_PKT_INTERVAL
    while True:
        now = datetime.datetime.now()
        while nextPacketTime > now:
            sleepTime = (nextPacketTime - now).total_seconds()
            time.sleep(sleepTime)
            now = datetime.datetime.now()
        nextPacketTime += RC_PKT_INTERVAL
        packet = chr(PKT_ID_DSM)
        for channel in range(8):
            data = rcChannels[channel]
            packet += chr(data % 256)
            packet += chr(data / 256)
        try:
            slipSendLock.acquire()
            slipIf.send(packet)
            slipSendLock.release()
        except:
            break
    try:
        slipSendLock.release()
    except:
        pass


# Message thread
# Wait for and respond to incoming messages
def msgThreadRun(slipIf):
    while True:
        pktOut = None
        try:
            pktTime, pkt = slipIf.recv()
        except:
            break
        if not pkt:
            break
        pktId = ord(pkt[0])
        if pktId == PKT_ID_NOP:
            pass # print "PKT_ID_NOP"
        elif pktId == PKT_ID_DSM:
            pass # print "PKT_ID_DSM"
        elif pktId == PKT_ID_CAL:
            pass # print "PKT_ID_CAL"
        elif pktId == PKT_ID_SYSINFO:
            pass # print "PKT_ID_SYSINFO"
            pktOut = chr(PKT_ID_SYSINFO) + "012345678901" + \
                     struct.pack('<H', 0xabcd) + "stm32_sim"
        elif pktId == PKT_ID_MAVLINK:
            pass # print "PKT_ID_MAVLINK"
        elif pktId == PKT_ID_SET_RAW_IO:
            pass # print "PKT_ID_SET_RAW_IO"
        elif pktId == PKT_ID_RAW_IO_REPORT:
            pass # print "PKT_ID_RAW_IO_REPORT"
        elif pktId == PKT_ID_PAIR_REQUEST:
            pass # print "PKT_ID_PAIR_REQUEST"
            pktOut = chr(PKT_ID_PAIR_CONFIRM) + "".join(pkt[1:])
        elif pktId == PKT_ID_PAIR_CONFIRM:
            # should never get this
            pass # print "PKT_ID_PAIR_CONFIRM"
        elif pktId == PKT_ID_PAIR_RESULT:
            pass # print "PKT_ID_PAIR_RESULT"
        else:
            pass # print "PKT_ID UNKNOWN"
        if pktOut is not None:
            try:
                slipSendLock.acquire()
                slipIf.send(pktOut)
                slipSendLock.release()
            except:
                break
    try:
        slipSendLock.release()
    except:
        pass


class sock1():
    def __init__(self, sock):
        self._sock = sock
    def read(self):
        return self._sock.recv(1)
    def write(self, c):
        self._sock.sendall(c)


parser = OptionParser("stm32_sim.py [options]")
parser.add_option("-p", dest="port", type="int",
                  help="TCP port to listen on",
                  default = DEFAULT_PORT)
(opts, args) = parser.parse_args()


listenSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listenSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listenSock.bind(("", opts.port))
listenSock.listen(1)

while True:
    print "waiting for connection on port", opts.port
    try:
        dataSock, remoteAddress = listenSock.accept()
    except:
        # typically ctrl-C
        break
    print "connection from", remoteAddress

    slipIf = slip.slip(sock1(dataSock))

    # start threads
    rcThread = threading.Thread(name="rcThread", target=rcThreadRun, args=(slipIf,))
    rcThread.daemon = True
    rcThread.start()

    msgThread = threading.Thread(name="msgThread", target=msgThreadRun, args=(slipIf,))
    msgThread.daemon = True
    msgThread.start()

    rcThread.join()
    msgThread.join()

    dataSock.close()
