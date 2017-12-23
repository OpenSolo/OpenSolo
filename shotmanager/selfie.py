#  selfie.py
#  shotmanager
#
#  The selfie smart shot.
#  Press Fly Out in the app and the drone flies up and out, keeping the camera pointed at the ROI
#  Runs as a DroneKit-Python script.
#
#  Created by Will Silva and Eric Liao in 2015
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


from dronekit import VehicleMode, LocationGlobalRelative
from pymavlink import mavutil
import os
from os import sys, path
import struct
import math

sys.path.append(os.path.realpath(''))
import app_packet
import location_helpers
import pathHandler
import shotLogger
import shots
from shotManagerConstants import *
# on host systems these files are located here
sys.path.append(os.path.realpath('../../flightcode/stm32'))
from sololink import btn_msg

YAW_SPEED = 60.0
PITCH_SPEED = 60.0

logger = shotLogger.logger

class SelfieShot():
    def __init__(self, vehicle, shotmgr):
        self.vehicle = vehicle
        self.shotmgr = shotmgr
        self.waypoints = []
        self.roi = None
        self.pathHandler = None

        # Camera control
        self.camPitch = 0
        self.camYaw = 0
        self.camDir = 1
        self.canResetCam = False

        self.setButtonMappings()

        # get current altitude limit
        self.altLimit = self.shotmgr.getParam( "FENCE_ALT_MAX", DEFAULT_FENCE_ALT_MAX ) # in meters

        # check APM params to see if Altitude Limit should apply
        if self.shotmgr.getParam( "FENCE_ENABLE", DEFAULT_FENCE_ENABLE ) == 0:
            self.altLimit = None
            logger.log("[Selfie]: Altitude Limit is disabled.")

    # channels are expected to be floating point values in the (-1.0, 1.0) range
    def handleRCs( self, channels ):
        #selfie needs 2 waypoints and an ROI to be ready
        if len(self.waypoints) != 2 or not self.roi:
            return

        self.pathHandler.MoveTowardsEndpt(channels)
        self.manualPitch(channels)
        self.manualYaw(channels)
        self.handleFreeLookPointing()

        if self.pathHandler.isNearTarget():
            # if we reached the end, flip
            if self.pathHandler.cruiseSpeed > 0.0:
                self.pathHandler.cruiseSpeed = -self.pathHandler.cruiseSpeed
                logger.log("[Selfie]: reached end of selfie path, flipping")
            elif self.pathHandler.cruiseSpeed < 0.0:
                logger.log("[Selfie]: reached end of selfie path, pausing")
                self.pathHandler.pause()

            self.updateAppOptions()


    def setButtonMappings(self):
        buttonMgr = self.shotmgr.buttonManager

        if self.canResetCam:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_SELFIE, btn_msg.ARTOO_BITMASK_ENABLED, "Look At Me\0")
        else:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_SELFIE, 0, "\0")

        buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_SELFIE, 0, "\0")


    # if we can handle the button we do
    def handleButton(self, button, event):
        if button == btn_msg.ButtonA and event == btn_msg.ClickRelease:
            self.pointAtROI()


        if button == btn_msg.ButtonLoiter and event == btn_msg.ClickRelease:
            if self.pathHandler:
                self.shotmgr.notifyPause(True)
                self.pathHandler.togglePause()
                self.updateAppOptions()
            else:
                # notify autopilot of pause press (technically not in shot)
                self.shotmgr.notifyPause(False)


    # send our current set of options to the app
    def updateAppOptions(self):
        speed = 0.0

        if self.pathHandler:
            speed = self.pathHandler.cruiseSpeed

        packet = struct.pack('<IIf', app_packet.SOLO_SHOT_OPTIONS, 4, speed)
        self.shotmgr.appMgr.sendPacket(packet)


    def handlePacket(self, packetType, packetLength, packetValue):
        try:
            if packetType == app_packet.SOLO_MESSAGE_LOCATION:
                (lat, lon, alt) = struct.unpack('<ddf', packetValue)
                logger.log("[selfie]: Location received from app: %f, %f, %f." %( lat, lon, alt ) )
                self.addLocation(LocationGlobalRelative(lat, lon, alt))

            elif packetType == app_packet.SOLO_SHOT_OPTIONS:
                (cruiseSpeed,) = struct.unpack('<f', packetValue)

                if self.pathHandler:
                    self.pathHandler.setCruiseSpeed(cruiseSpeed)
                    logger.log("[selfie]: Cruise speed set to %.2f." % (cruiseSpeed,))
            else:
                return False
        except Exception as e:
            logger.log('[selfie]: Error handling packet. (%s)' % e)
            return False
        else:
            return True


    def addLocation(self, loc):
        # we're ready once we have 2 waypoints and an ROI
        if len(self.waypoints) < 2:

            # check altitude limit on 2nd point
            if self.altLimit is not None and len(self.waypoints) > 0:
                if loc.alt > self.altLimit:
                    logger.log("[Selfie]: 2nd selfie point breaches user-set altitude limit (%.1f meters)." % (self.altLimit))

                    # find vector to 2nd point
                    selfieVector = location_helpers.getVectorFromPoints(self.waypoints[0],loc)

                    # normalize it
                    selfieVector.normalize()

                    # calculate distance between two points
                    d = location_helpers.getDistanceFromPoints3d(self.waypoints[0],loc)

                    # calculate hypotenuse
                    hyp = (self.altLimit-self.waypoints[0].alt)/((loc.alt-self.waypoints[0].alt)/d)

                    # scale selfie vector by hypotenuse
                    selfieVector *= hyp

                    # add selfieVector to original selfie point to create a new 2nd point
                    loc = location_helpers.addVectorToLocation(self.waypoints[0],selfieVector)

            self.waypoints.append(loc)
            logger.log("[Selfie]: Added a selfie point: %f, %f, %f." % ( loc.lat, loc.lon,loc.alt))

        elif not self.roi:
            self.roi = loc

            logger.log("[Selfie]: Added a selfie ROI: %f, %f, %f." %
                    ( loc.lat, loc.lon,
                        loc.alt))

            self.pathHandler = pathHandler.TwoPointPathHandler( self.waypoints[0], self.waypoints[1], self.vehicle, self.shotmgr )
            # ready!  set up everything
            self.shotmgr.rcMgr.enableRemapping( True )
            # Now change the vehicle into guided mode
            self.vehicle.mode = VehicleMode("GUIDED")
            self.manualGimbalTargeting()
            self.setButtonMappings()


    def manualGimbalTargeting(self):
        '''set gimbal targeting mode to manual'''
        msg = self.vehicle.message_factory.mount_configure_encode(
            0, 1,    # target system, target component
            mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,  # mount_mode
            1,  # stabilize roll
            1,  # stabilize pitch
            1,  # stabilize yaw
        )
        self.vehicle.send_mavlink(msg)
        self.pointAtROI()


    def pointAtROI(self):
        logger.log("[Selfie]: Point at ROI")
        # calcs the yaw and pitch to point the gimbal
        self.camYaw, self.camPitch = location_helpers.calcYawPitchFromLocations(self.vehicle.location.global_relative_frame, self.roi)

        if self.canResetCam:
            self.canResetCam = False
            self.setButtonMappings()


    def updateCanResetCam(self, resetCam):
        # only send button label updates on change
        if resetCam != self.canResetCam:
            logger.log("[Selfie]: can reset to ROI")
            self.canResetCam = resetCam
            self.setButtonMappings()


    def manualPitch(self, channels):
        if abs(channels[RAW_PADDLE]) > abs(channels[THROTTLE]):
            value = channels[RAW_PADDLE]
        else:
            value = channels[THROTTLE]

        if value == 0:
            return

        self.updateCanResetCam(True)
        self.camPitch += value * PITCH_SPEED * UPDATE_TIME

        if self.camPitch > 0.0:
            self.camPitch = 0.0
        elif self.camPitch < -90:
            self.camPitch = -90


    def manualYaw(self, channels):
        if channels[YAW] == 0:
            return

        self.updateCanResetCam(True)
        self.camYaw += channels[YAW] * YAW_SPEED * UPDATE_TIME
        if self.camYaw > 360:
            self.camYaw -= 360
        if self.camYaw < 0:
            self.camYaw += 360

        # required for gimbals w/o Yaw
        if channels[YAW] > 0:
            self.camDir = 1
        else:
            self.camDir = -1


    def handleFreeLookPointing(self):
        '''Handle free look'''
        # if we do have a gimbal, use mount_control to set pitch and yaw
        if self.vehicle.mount_status[0] is not None:
            msg = self.vehicle.message_factory.mount_control_encode(
                0, 1,                   # Target system, target component
                self.camPitch * 100,    # Pitch in centidegrees
                0.0,                    # Roll not used
                self.camYaw * 100,      # Yaw in centidegrees
                0                       # save position
            )
            self.vehicle.send_mavlink(msg)

        else:
            # if we don't have a gimbal, just set CONDITION_YAW
            msg = self.vehicle.message_factory.command_long_encode(
                0, 1,           # target system, target component
                mavutil.mavlink.MAV_CMD_CONDITION_YAW, #command
                0,              # confirmation
                self.camYaw,    # param 1 - target angle
                YAW_SPEED,      # param 2 - yaw speed
                self.camDir,    # param 3 - direction
                0.0,            # relative offset
                0, 0, 0         # params 5-7 (unused)
            )
            self.vehicle.send_mavlink(msg)
