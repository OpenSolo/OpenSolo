#
#  Handles RC (radio control) connection state and IO.
#  Created by Will Silva on 3/5/2016.
#  Updated by Jason Short 4/6/2016.
#  Copyright (c) 2016 3D Robotics.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import socket
import sys
import shotLogger
from sololink import rc_pkt

sys.path.append(os.path.realpath(''))
from shotManagerConstants import *
from sololink import rc_ipc
from sololink import rc_pkt
import shots
import rcManager

logger = shotLogger.logger

DEFAULT_RC_MIN = 1000
DEFAULT_RC_MAX = 2000
DEFAULT_RC_MID = ( DEFAULT_RC_MAX - DEFAULT_RC_MIN ) / 2.0 + DEFAULT_RC_MIN

# These channels have different ranges
CHANNEL6_MIN = 1000
CHANNEL6_MAX = 1520
CHANNEL6_MID = ( CHANNEL6_MAX - CHANNEL6_MIN ) / 2.0 + CHANNEL6_MIN

CHANNEL8_MIN = 0
CHANNEL8_MAX = 1000
CHANNEL8_MID = ( CHANNEL8_MAX - CHANNEL8_MIN ) / 2.0 + CHANNEL8_MIN

THROTTLE_FAILSAFE = 950
DEAD_ZONE = 0.009

TICKS_UNTIL_RC_STALE = 20 # ticks
RC_TCP_BUFSIZE = 1024


class rcManager():
    def __init__(self, shotmgr):
        self.shotmgr = shotmgr
        self.connected = False
        self.bindServer()

        # Manage flow of RC data
        self.numTicksSinceRCUpdate = 0
        self.timestamp = 0
        self.sequence = 0
        self.channels = None

        # True if we have RC link
        self.failsafe = False

        if os.path.exists( "/run/rc_uplink_cmd" ):
            self.server.sendto("attach", "/run/rc_uplink_cmd")

        # only log this once
        self.loggedRC_ipc = False

        # We are sending the RC data to PixRC and disabling CH Yaw
        # Force off on startup
        self.remappingSticks = True
        self.enableRemapping(False)


    def bindServer(self):
		# set up a socket to receive rc inputs from pixrc
        if os.path.exists( "/tmp/shotManager_RCInputs_socket" ):
            os.remove( "/tmp/shotManager_RCInputs_socket" )

        self.server = socket.socket( socket.AF_UNIX, socket.SOCK_DGRAM )
        self.server.bind("/tmp/shotManager_RCInputs_socket")
        self.server.setblocking(0)

    # This is called whenever we have data on the rc socket, which should be
    # at 50 hz, barring any drops
    # We remap/normalize the RC and then store it away for use in Tick()
    def parse(self):
        datagram = self.server.recv(RC_TCP_BUFSIZE)

        if datagram == None or len(datagram) != rc_pkt.LENGTH:
            self.channels = None
            return

        self.timestamp, self.sequence, self.channels = rc_pkt.unpack(datagram)

        if self.channels[THROTTLE] > THROTTLE_FAILSAFE:
            self.numTicksSinceRCUpdate = 0
        else:
            # we are in failsafe so don't cache data - we'll send defaults
            self.channels = None


    def rcCheck(self):
        self.numTicksSinceRCUpdate += 1

        if self.numTicksSinceRCUpdate > TICKS_UNTIL_RC_STALE:
            if self.failsafe == False:
                logger.log( "[RC] Enter failsafe")
                self.triggerFailsafe(True)
        else:
            if self.failsafe == True:
                logger.log( "[RC] Exit failsafe")
                self.triggerFailsafe(False)


    def isRcConnected(self):
    	return self.numTicksSinceRCUpdate < TICKS_UNTIL_RC_STALE

    """
    This remaps all of our RC input into (-1.0, 1.0) ranges.
    The RC channels come in as PWM values of (1000, 2000)
    Filtered camera paddle is in channel 6 (index 5), and has range (1000, 1520) for some odd reason.
    Raw camera paddle is channel 8 (index 7) and is of range (0, 1000)
    This function is responsible for sending RC data back to PixRC for remapping purposes.
    However, it will only do this if the sendToPixRC param is set to True and self.remappingSticks is set
    """
    def remap(self):
        if self.failsafe or self.channels == None:
            # send default values to the Pixhawk
            self.channels = [DEFAULT_RC_MID, DEFAULT_RC_MID, DEFAULT_RC_MID, DEFAULT_RC_MID, DEFAULT_RC_MIN, CHANNEL6_MAX, DEFAULT_RC_MIN, CHANNEL8_MID ]

        normChannels = [0]*8

        # channels 1-4
        for i in range(4):
            normChannels[i] = self.normalizeRC( self.channels[i], DEFAULT_RC_MIN, DEFAULT_RC_MAX )

        #logger.log("FP %d, RP %d" % (self.channels[FILTERED_PADDLE], self.channels[RAW_PADDLE]))
        
        # channel 6 (index 5) is the filtered gimbal paddle value
        # its values go from CHANNEL6_MIN - CHANNEL6_MAX
        # this value is used directly to point the gimbal 
        # 1520 = level, 1000 = straight down
        normChannels[FILTERED_PADDLE] = self.normalizeRC( self.channels[FILTERED_PADDLE], CHANNEL6_MIN, CHANNEL6_MAX )

        # channel 8 (index 7) is the raw gimbal paddle and is a special case
        # its values go from CHANNEL8_MIN - CHANNEL8_MAX
        # this value is used to understand user input
        # >500 = tilt up, 500 = no tilt, < 500 tilt down
        normChannels[RAW_PADDLE] = self.normalizeRC( self.channels[RAW_PADDLE], CHANNEL8_MIN, CHANNEL8_MAX)

        if self.remappingSticks:
            # never allow Yaw to rotate in guided shots to prevent shot confusion
            self.channels[YAW] = 1500
            if not rc_ipc.put((self.timestamp, self.sequence, self.channels)):
                if not self.loggedRC_ipc:
                    logger.log( "ERROR returned from rc_ipc.put" )
                    self.loggedRC_ipc = True

        return normChannels


    # convert from RC input values to (-1.0, 1.0) floating point value
    # min/max is customizable to handle inputs of different ranges
    def normalizeRC(self, value, min, max):

        # failsafe is out of these bounds
        if value < min or value > max:
            return 0.0

        halfrange = (max - min) / 2.0
        midpt = halfrange + min

        # this is our range
        effectiveRange = halfrange

        # scale the input to (-1.0, 1.0),
        result = float( value - midpt ) / effectiveRange
    
        if abs(result) < DEAD_ZONE:
            return 0.0
        else:
            return result


    def triggerFailsafe(self, doFailsafe):
        self.failsafe = doFailsafe
        if self.failsafe:
            self.shotmgr.enterFailsafe()


    # enable/Disable remapping of sticks
    def enableRemapping(self, doEnable):
        # only act on change
        if self.remappingSticks != doEnable:
            self.remappingSticks = doEnable

            if os.path.exists( "/run/rc_uplink_cmd" ):
                if doEnable:
                    logger.log("[RC] Enabling stick remapping")
                    rc_ipc.attach()
                    self.server.sendto("detach uplink", "/run/rc_uplink_cmd")
                else:
                    logger.log("[RC] Disabling stick remapping")
                    self.server.sendto("attach uplink", "/run/rc_uplink_cmd")
                    rc_ipc.detach()

    def detach(self):
        logger.log( "[RC] detach from rc_ipc.put" )
        if os.path.exists( "/run/rc_uplink_cmd" ):
            self.server.sendto("detach", "/run/rc_uplink_cmd")
        self.enableRemapping(False)

