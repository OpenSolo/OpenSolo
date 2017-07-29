#!/usr/bin/env python

import os
import cPickle
import datetime
import socket
import struct
import sys

from stm32_defs import *

# Log record types.
TYPE_STM32_PACKET = 1
TYPE_PIXIN_PACKET = 2
TYPE_PIXOUT_PACKET = 3

PIPE_NAME_DEFAULT = "/var/run/logd"

# log to LOG_DIR_0_DEFAULT if it exists, else LOG_DIR_1_DEFAULT
LOG_DIR_0_DEFAULT = "/log"
LOG_DIR_1_DEFAULT = "/var/local"

debug = False


class Stm32Logger(object):

    def __init__(self, pipe_name=PIPE_NAME_DEFAULT):
        self.log_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.local_name = "/tmp/logd-stm32"
        self.pipe_name = pipe_name
        # delete it if there's an old one still there
        try:
            os.remove(self.local_name)
        except:
            pass # wasn't there, okay
        self.log_sock.bind(self.local_name)

    def uninit(self):
        os.remove(self.local_name)

    def log_packet(self, pktTime, pkt):
        data = (TYPE_STM32_PACKET, datetime.datetime.now(), pktTime, pkt)
        pick = cPickle.dumps(data)
        try:
            self.log_sock.sendto(pick, self.pipe_name)
        except:
            pass # logger is dead


class PixInLogger(object):

    def __init__(self, pipe_name=PIPE_NAME_DEFAULT):
        self.log_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.local_name = "/tmp/logd-pixin"
        self.pipe_name = pipe_name
        # delete it if there's an old one still there
        try:
            os.remove(self.local_name)
        except:
            pass # wasn't there, okay
        self.log_sock.bind(self.local_name)

    def uninit(self):
        os.remove(self.local_name)

    def log_packet(self, pkt):
        data = (TYPE_PIXIN_PACKET, datetime.datetime.now(), pkt)
        pick = cPickle.dumps(data)
        try:
            self.log_sock.sendto(pick, self.pipe_name)
        except:
            pass # logger is dead


class PixOutLogger(object):

    def __init__(self, pipe_name=PIPE_NAME_DEFAULT):
        self.log_sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.local_name = "/tmp/logd-pixout"
        self.pipe_name = pipe_name
        # delete it if there's an old one still there
        try:
            os.remove(self.local_name)
        except:
            pass # wasn't there, okay
        self.log_sock.bind(self.local_name)

    def uninit(self):
        os.remove(self.local_name)

    def log_packet(self, pkt):
        data = (TYPE_PIXOUT_PACKET, datetime.datetime.now(), pkt)
        pick = cPickle.dumps(data)
        try:
            self.log_sock.sendto(pick, self.pipe_name)
        except:
            pass # logger is dead


class Logger(object):

    # XXX get from config file

    # If we roll the log and have more than MAX_FILES, old files are deleted
    # to get down to MAX_FILES.
    MAX_FILES = 50

    # If a log file gets to MAX_FILE_BYTES, the log is rolled.
    MAX_FILE_BYTES = 10000000

    # If the total number of bytes logged gets to MAX_BYTES, old files are
    # deleted to get down to MAX_BYTES.
    MAX_BYTES = 75000000 # 90% of a 100 MB partition (~85 MB usable)

    def __init__(self, pipe_name, file_root, file_ext):
        self.total_bytes = 0
        self.epoch = datetime.datetime(1970, 1, 1)
        self.pipe_name = pipe_name
        self.file_root = file_root
        self.file_ext = file_ext
        # delete named socket if left over from a previous run
        try:
            os.remove(self.pipe_name)
        except:
            pass # did not exist, okay
        # create named socket to receive data on
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            self.sock.bind(self.pipe_name)
        except:
            print "ERROR creating pipe %s" % (self.pipe_name,)
            raise
        # always start with a new log file
        self.roll()

    def file_name(self, n):
        return "%s.%03d.%s" % (self.file_root, n, self.file_ext)

    # RC packets as received from STM32 serial port on Artoo
    def format_stm32(self, data_tuple):
        # data_tuple is:
        #   integer  typeId
        #   datetime logTime
        #   datetime pktTime
        #   string   packet

        typeId = data_tuple[0]
        logTime = data_tuple[1]
        pktTime = data_tuple[2]
        pkt = data_tuple[3]

        logTime = logTime - self.epoch # timedelta
        pktTime = pktTime - self.epoch # timedelta
        pktLen = len(pkt)

        if pktLen > 0:
            pktId = ord(pkt[0])
        else:
            pktId = -1

        s1 = "%d,%d,%d,%d,%d,%d,%d" % (typeId,
                                       logTime.days * 86400 + logTime.seconds,
                                       logTime.microseconds,
                                       pktTime.days * 86400 + pktTime.seconds,
                                       pktTime.microseconds,
                                       pktLen,
                                       pktId)

        if pktId == 0:
            s2 = ",%s\n" % (pkt[1:],)
        elif pktId == PKT_ID_DSM:
            if pktLen == 17:
                s2 = ",%d,%d,%d,%d,%d,%d,%d,%d\n" % (ord(pkt[2]) * 256 + ord(pkt[1]),
                                                     ord(pkt[4]) * 256 + ord(pkt[3]),
                                                     ord(pkt[6]) * 256 + ord(pkt[5]),
                                                     ord(pkt[8]) * 256 + ord(pkt[7]),
                                                     ord(pkt[10]) * 256 + ord(pkt[9]),
                                                     ord(pkt[12]) * 256 + ord(pkt[11]),
                                                     ord(pkt[14]) * 256 + ord(pkt[13]),
                                                     ord(pkt[16]) * 256 + ord(pkt[15]))
            else:
                s2 = "\n"
        elif pktId == PKT_ID_SYSINFO:
            # 12 bytes unique_id
            # 2 bytes hw_version
            # string sw_version
            if pktLen >= 13:
                # unique_id
                s2 = ",%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x:%02x" % \
                    (ord(pkt[1]), ord(pkt[2]), ord(pkt[3]), ord(pkt[4]),
                     ord(pkt[5]), ord(pkt[6]), ord(pkt[7]), ord(pkt[8]),
                     ord(pkt[9]), ord(pkt[10]), ord(pkt[11]), ord(pkt[12]))
                if pktLen >= 15:
                    # hw_version
                    s2 += ",%02x:%02x" % (ord(pkt[13]), ord(pkt[14]))
                    if pktLen >= 16:
                        # sw_version
                        s2 += ",%s" % ("".join(pkt[15:]),)
                s2 += "\n"
            else:
                s2 = "\n"
        else:
            s2 = "\n"

        return s1 + s2

    # RC packets as received from UDP port on Solo
    def format_pixin(self, data_tuple):
        # data_tuple is:
        #   integer  typeId
        #   datetime logTime
        #   string   packet

        typeId = data_tuple[0]
        logTime = data_tuple[1]
        pkt = data_tuple[2]

        logTime = logTime - self.epoch # timedelta
        pktLen = len(pkt)

        if pktLen != 26:
            s = "%d,%d,%d\n" % (typeId,
                                logTime.days * 86400 + logTime.seconds,
                                logTime.microseconds)
            return s

        # packet is:
        #   pktTime.usec    32 bits
        #   pktTime.sec     32 bits
        #   sequence        16 bits
        #   channel 1       16 bits
        #   :
        #   channel 8       16 bits
        (usec, sec, seq, ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8) = \
            struct.unpack("<IIHHHHHHHHH", pkt)

        s = "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n" % \
            (typeId,
             logTime.days * 86400 + logTime.seconds, logTime.microseconds,
             sec, usec, seq, ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8)

        return s

    # RC packets as sent over serial port to Pixhawk
    def format_pixout(self, data_tuple):
        # data_tuple is:
        #   integer  typeId
        #   datetime logTime
        #   string   packet

        typeId = data_tuple[0]
        logTime = data_tuple[1]
        pkt = data_tuple[2]

        logTime = logTime - self.epoch # timedelta
        pktLen = len(pkt)

        s = "%d,%d,%d" % (typeId,
                          logTime.days * 86400 + logTime.seconds,
                          logTime.microseconds)

        # packet is BIG endian:
        #   magic           16 bits
        #   channel 1       16 bits
        #   :
        #   channel 7       16 bits
        # and if 32 bytes:
        #   magic           16 bits
        #   channel 8       16 bits
        #   :
        #   channel 14      16 bits
        # and each channel is (one-based channel numbers):
        #   (chNum-1 << 11) | (chDat & 0x07ff)

        if pktLen != 16 and pktLen != 32:
            return s + "\n"

        pktIdx = 0
        while pktIdx < pktLen:
            # magic
            s += ",%d" % struct.unpack(">H", pkt[pktIdx:pktIdx+2])
            pktIdx += 2
            # channels
            for chIdx in range(1, 8):
                (chRaw,) = struct.unpack(">H", pkt[pktIdx:pktIdx+2])
                pktIdx += 2
                chNum = (chRaw >> 11) & 0xf
                chVal = chRaw & 0x7ff
                s += ",%d,%d" % (chNum, chVal)

        return s + "\n"

    def roll(self):
        # If there is not a log file, do nothing.
        # Otherwise, rename it to
        #     file_root.001.file_ext
        # bumping all old ones up. We keep up to MAX_FILES.
        #
        # The end result is:
        #     file_root.000.file_ext   current
        #     file_root.001.file_ext      |
        #     file_root.002.file_ext      v
        #     file_root.003.file_ext    oldest
        # where ".003" goes up to MAX_FILES-1.

        self.total_bytes = 0

        try:
            stat_info = os.stat(self.file_name(0))
        except:
            return # "current" file not there, nothing to do

        # Rename files, starting from high numbers and working down. This takes
        # care of the MAX_FILES limit (the highest-numbered file is just
        # overwritten).
        for file_num in range(self.MAX_FILES-1, 0, -1):
            src = self.file_name(file_num-1)
            try:
                stat_info = os.stat(src)
            except:
                # file does not exist
                continue
            # file exists
            self.total_bytes += stat_info.st_size
            dst = self.file_name(file_num)
            try:
                os.rename(src, dst)
                if debug:
                    print "rename %s to %s" % (src, dst)
            except:
                pass # error renaming file?
        ### end for file_num

    def check_size(self):
        """check total size of logs and delete log files as necessary"""

        # if current log file is over 10% of the total, do a roll
        try:
            stat_info = os.stat(self.file_name(0))
        except:
            return # "current" file not there, nothing to do

        if stat_info.st_size >= self.MAX_FILE_BYTES:
            self.roll()

        # delete files until the total number of bytes is less that the max
        for file_num in range(self.MAX_FILES-1, 0, -1):
            if self.total_bytes <= self.MAX_BYTES:
                break
            src = self.file_name(file_num)
            try:
                stat_info = os.stat(src)
                if debug:
                    print "delete %s" % (src,)
                os.remove(src)
                self.total_bytes -= stat_info.st_size
            except:
                pass # does not exist

    def run(self):
        while True:
            data = self.sock.recv(1024)
            # data is pickled python, consisting of an integer type indicator
            # followed by type-specific data.
            try:
                data_tuple = cPickle.loads(data)
            except:
                pickle_error += 1
                continue
            typeId = data_tuple[0]
            if typeId == TYPE_STM32_PACKET:
                s = self.format_stm32(data_tuple)
            elif typeId == TYPE_PIXIN_PACKET:
                s = self.format_pixin(data_tuple)
            elif typeId == TYPE_PIXOUT_PACKET:
                s = self.format_pixout(data_tuple)
            else:
                s = "%d" % (typeId,)
            try:
                logfile = open(self.file_name(0), "a")
            except:
                print "ERROR opening log file %s for writing" % (self.file_name(0),)
                raise
            logfile.write(s)
            logfile.close()
            self.total_bytes += len(s)
            self.check_size()


def is_dir(path):
    try:
        s = os.stat(path)
    except:
        return False
    if s.st_mode & os.O_DIRECTORY:
        return True
    else:
        return False


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser("logd.py [options]")

    parser.add_option("--pipe", dest="pipe_name", type="string", default=None,
                      help="logging pipe name")

    parser.add_option("--file", dest="file_root", type="string", default=None,
                      help="log file name root")

    (opts, args) = parser.parse_args()

    pipe_name = PIPE_NAME_DEFAULT
    if opts.pipe_name is not None:
        pipe_name = opts.pipe_name

    # set default path

    if is_dir(LOG_DIR_0_DEFAULT):
        log_dir = LOG_DIR_0_DEFAULT # preferred
    else:
        log_dir = LOG_DIR_1_DEFAULT # must exist
    file_root = log_dir + "/3dr-logd"

    if opts.file_root is not None:
        file_root = opts.file_root

    file_ext = "csv"

    logger = Logger(pipe_name, file_root, file_ext)

    os.nice(19)

    logger.run()
