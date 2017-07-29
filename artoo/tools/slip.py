#!/usr/bin/env python

class SlipDevice:

    END     = chr(0300) # indicates end of packet
    ESC     = chr(0333) # indicates byte stuffing
    ESC_END = chr(0334) # ESC ESC_END means END data byte
    ESC_ESC = chr(0335) # ESC ESC_ESC means ESC data byte

    def __init__(self, serial_dev, trace_tx=False):
        self.ser = serial_dev
        self.trace_tx = trace_tx
        self.insync = False

        self.ser.flushInput()
        self.ser.flushOutput()

    def sync(self):
        while self.ser.read() != self.END:
            pass
        self.insync = True

    def read(self):
        """
        read a SLIP packet from artoo.
        """

        if not self.insync:
            self.sync()

        pkt = []

        while True:
            b = self.ser.read()
            if b == self.END:
                if len(pkt) > 0:
                    return pkt
            elif b == self.ESC:
                b = self.ser.read()
                if b == self.ESC_END:
                    pkt.append(self.END)
                elif b == self.ESC_ESC:
                    pkt.append(self.ESC)
                else:
                    pkt.append(b)
            else:
                pkt.append(b)

    def write(self, pkt):
        """
        write a SLIP message to artoo
        """

        slip_bytes = [self.END]
        for b in pkt:

            if not isinstance(b, str):
                b = chr(b)

            if b == self.END:
                slip_bytes.append(self.ESC)
                slip_bytes.append(self.ESC_END)
            elif b == self.ESC:
                slip_bytes.append(self.ESC)
                slip_bytes.append(self.ESC_ESC)
            else:
                slip_bytes.append(b)

        slip_bytes.append(self.END)
        if self.trace_tx:
            print "r2 tx:", [hex(ord(b)) for b in slip_bytes]
        return self.ser.write("".join(slip_bytes))
