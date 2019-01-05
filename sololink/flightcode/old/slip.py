#!/usr/bin/env python

import datetime
import logging
import logging.config
import serial

configFileName = "/etc/sololink.conf"

logging.config.fileConfig(configFileName)
logger = logging.getLogger("slip")



class slip():


    END     = chr(0xc0) # indicates end of packet
    ESC     = chr(0xdb) # indicates byte stuffing
    ESC_END = chr(0xdc) # ESC ESC_END means END data byte
    ESC_ESC = chr(0xdd) # ESC ESC_ESC means ESC data byte


    # This is really for detecting garbage input, and not passing huge junk to the
    # stm32 message handlers. Intended to be much bigger than any real packet. If
    # we get more than this much data without finding an END, we drop the packet
    # and go back to looking for sync.
    maxPktLen = 1024


    def __init__(self, stream):
        # I/O interface, provides s=read() and write(s)
        self._stream = stream
        self._inSync = False
        # count of each reason we lost sync
        self.desyncCounts = {}
        self._desyncLogInterval = datetime.timedelta(seconds=1) # =None to never log
        self._desyncLogLast = None
        # receive counters
        self.counts = { 'BYTE': 0, 'SYNC': 0, 'DROP': 0, 'ESC': 0 }
        self._syncLogInterval = datetime.timedelta(seconds=1) # =None to never log
        self._syncLogLast = None


    # Lost sync. Functionally, we just want to set inSync False, but for analysis
    # and debugging, we use a function so we can count things and log and such.
    def desync(self, reason):
        now = datetime.datetime.now()
        self._inSync = False
        # count various reasons for losing sync (debug)
        if reason not in self.desyncCounts:
            self.desyncCounts[reason] = 0
        self.desyncCounts[reason] += 1
        # periodically log (debug)
        if (self._desyncLogInterval is not None) and \
           ((self._desyncLogLast is None) or \
            ((now - self._desyncLogLast) >= self._desyncLogInterval)):
            logger.info("lost sync (desyncs = %s)", str(self.desyncCounts))
            self._desyncLogLast = now


    # Receive one SLIP-encoded packet. If there is a timeout
    # waiting for the next character, any data received so far is dropped and
    # (None, None) is returned. The timout is set when the port is opened.
    def recv(self):

        pktTime = None
        pkt = []

        if not self._inSync:
            now = datetime.datetime.now()
            self.counts['SYNC'] += 1
            # periodically log
            if (self._syncLogInterval is not None) and \
               ((self._syncLogLast is None) or \
                ((now - self._syncLogLast) >= self._syncLogInterval)):
                logger.info("syncing, counts = %s", str(self.counts))
                self._syncLogLast = now
            # find the next END
            while True:
                b = self._stream.read()
                if len(b) == 0:
                    return None, None # timeout
                self.counts['BYTE'] += 1
                if b == slip.END:
                    break
                self.counts['DROP'] += 1

        # already synced, or just got an END
        self._inSync = True

        # read packet
        while True:
            b = self._stream.read()
            if len(b) == 0:
                return None, None # timeout
            self.counts['BYTE'] += 1
            if len(pkt) == 0:
                if b == slip.END:
                    # packet data has not started
                    continue
                else:
                    # first byte in packet
                    # timestamp is that of the first byte in the packet
                    pktTime = datetime.datetime.now()

            # If b is END at this point, it is the packet end. pkt[] must have
            # at least one byte, and pktTime must have been set to get past the
            # continue a few lines up
            if b == slip.END:
                return pktTime, pkt

            if b == slip.ESC:
                b = self._stream.read()
                if len(b) == 0:
                    return None, None # timeout
                self.counts['BYTE'] += 1
                if b == slip.ESC_END:
                    pkt.append(slip.END)
                elif b == slip.ESC_ESC:
                    pkt.append(slip.ESC)
                else:
                    pkt.append(b)
                self.counts['ESC'] += 1
            else:
                pkt.append(b)

            # Sanity check
            if len(pkt) > slip.maxPktLen:
                # Something is wrong
                slip.desync('TOO_LONG')


    # Send one SLIP-encoded packet.
    # 'pkt' is anything we can iterate over a byte at a time
    # (e.g. string, list of single-char strings)
    def send(self, pkt):

        self._stream.write(slip.END) # may be optional

        for c in pkt:
            if c == slip.END:
                self._stream.write(slip.ESC)
                self._stream.write(slip.ESC_END)
            elif c == slip.ESC:
                self._stream.write(slip.ESC)
                self._stream.write(slip.ESC_ESC)
            else:
                self._stream.write(c)

        self._stream.write(slip.END)



# END class slip



if __name__ == "__main__":
    # test

    class dataSource():
        def __init__(self, data):
            self._data = data
            self._index = 0
        def read(self):
            b = self._data[self._index]
            self._index += 1
            return b

    # These tests just check the END processing.
    # ESC processing has been running for a while; add tests if needed.

    testData = ""
    # junk discarded before first END, and the first END
    testData += "abc" + slip.END
    # first packet
    testData += "1:123" + slip.END
    # second packet, only the one END between first and second
    testData += "2:45" + slip.END
    # leading ENDs are okay
    testData += slip.END + "3:6" + slip.END
    # lots of ENDs are okay
    testData += slip.END + slip.END + slip.END + "4:789" + slip.END

    testSer = dataSource(testData)

    while True:
        try:
            print recv(testSer)
        except:
            break
