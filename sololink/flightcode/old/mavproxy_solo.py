#!/usr/bin/env python
"""solo status insertion"""

from pymavlink import mavutil
from MAVProxy.modules.lib import mp_module
import iw
import logging
import logging.config

class SoloModule(mp_module.MPModule):


    # times per second to trigger in idle task
    POLL_FREQ = 1


    def __init__(self, mpstate):
        super(SoloModule, self).__init__(mpstate, "solo",
                                         "solo status insertion",
                                         public = True)
        logging.config.fileConfig("/etc/sololink.conf")
        self._logger = logging.getLogger("wifi")
        self._period = mavutil.periodic_event(SoloModule.POLL_FREQ)
        # Pixhawk is sending messages with srcSystem=1, srcComponent=1
        # Use the same srcSystem but a different srcComponent so the sequence
        # numbers make sense.
        # XXX How do we determine when we are running on Artoo, and should use
        #     a different srcSystem?
        # The --source-system command line argment does not change the source
        # system for downstream messages. Maybe it does for upstream messages.
        self._srcSystem = 1
        self._srcComponent = 2
        self._logger.info("MAVProxy solo module running")


    def link_rssi(self, info):
        # map link info to rssi value (0..255)
        # Using signal strength...
        if False:
            # Signal is dBm, rougly ~ -100..-30
            # Arbitrary mapping:
            # <= -100 -> 0
            # >=  -50 -> 255
            val = info["signal"]
            valMin = -100.0
            valMax = -50.0
            rssiMin = 0.0
            rssiMax = 255.0
        # Using txBitrate...
        if True:
            # Rate is Mbit/sec, 1..54
            # Arbitrary mapping:
            # <1 -> 0
            #  1 -> 10    valMin -> rssiMin
            # 54 -> 255   valMax -> rssiMax
            val = info["txBitrate"]
            valMin = 1.0
            valMax = 54.0
            rssiMin = 10.0
            rssiMax = 255.0
        if val is None:
            rssi = 0
        elif val < valMin:
            rssi = 0
        elif val >= valMax:
            rssi = int(rssiMax)
        else:
            rssi = int(((val - valMin) / (valMax - valMin)) * (rssiMax - rssiMin) + rssiMin)
        # rssi should already be in range
        if rssi < 0:
            rssi = 0
        elif rssi > 255:
            rssi = 255
        return rssi


    def idle_task(self):
        # idle_task is called 100 times/second
        if self._period.trigger():
            # trigger rate is POLL_FREQ times/second

            info = iw.iwLink("wlan0")

            # info contains: txBytes rxBytes ssid txBitrate rxPackets freq signal txPackets
            # log some at "info" level and some at "debug" level
            self._logger.info("ssid=%s freq=%s signal=%s txBitrate=%s",
                              info["ssid"], info["freq"],
                              info["signal"], info["txBitrate"])
            self._logger.debug("txPackets=%s rxPackets=%s txBytes=%s rxBytes=%s",
                              info["txPackets"], info["rxPackets"],
                              info["txBytes"], info["rxBytes"])

            rssi = self.link_rssi(info)

            # Send status to master. If sending to Pixhawk, this does not get
            # echoed back out in the outgoing telemetry stream.
            for master in self.mpstate.mav_master:
                master.mav.srcSystem = self._srcSystem
                master.mav.srcComponent = self._srcComponent
                try:
                    msg = master.mav.radio_status_encode(rssi=rssi, remrssi=0,
                                                         txbuf=0, noise=0,
                                                         remnoise=0, rxerrors=0,
                                                         fixed=0)
                except Exception as excEncode:
                    print "solo: master encode exception", excEncode
                else:
                    try:
                        master.mav.send(msg)
                    except Exception as excSend:
                        print "solo: master send exception:", excSend

            # Send status to all slaves.
            for slave in self.mpstate.mav_outputs:
                # srcSystem/srcComponent are properties of the 'mav' object.
                # Messages from upstream that are simply routed through are not
                # affected by this change. This is done here instead of in the
                # constructor since the outputs may change at runtime.
                slave.mav.srcSystem = self._srcSystem
                slave.mav.srcComponent = self._srcComponent
                try:
                    msg = slave.mav.radio_status_encode(rssi=rssi, remrssi=0,
                                                        txbuf=0, noise=0,
                                                        remnoise=0, rxerrors=0,
                                                        fixed=0)
                except Exception as excEncode:
                    print "solo: slave encode exception", excEncode
                else:
                    try:
                        slave.mav.send(msg)
                    except Exception as excSend:
                        print "solo: slave send exception:", excSend


def init(mpstate):
    """initialize module"""
    return SoloModule(mpstate)
