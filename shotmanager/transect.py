#
#  transect.py
#  shotmanager
#
#  The transect smart shot controller.
#  Runs as a DroneKit-Python script under MAVProxy.
#
#  Created by Jason Short
#  Copyright (c) 2015 3D Robotics.
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

from dronekit import Vehicle, LocationGlobalRelative, VehicleMode

from pymavlink import mavutil
import os
from os import sys, path
import math
import struct

sys.path.append(os.path.realpath(''))
import app_packet
import camera
import location_helpers
import pathHandler
import shotLogger
import shots
from shotManagerConstants import *
import GoProManager
from GoProConstants import *
from sololink import btn_msg

# length of the transect line (meters)
MAX_TRANSECT_LENGTH = 500
MIN_TRANSECT_LENGTH = 50
#speed of vehicle m/s
TRANSECT_SPEED = 1.5

# we can take a photo every 2 seconds
MIN_TRIGGER_DIST = TRANSECT_SPEED * 2

OVERLAP = .8

STARTUP_DELAY = UPDATE_RATE * 2

RETURN_TO_START = 4
FINISH = 3
RUN = 2
TILT = 1
SETUP = 0

YAW_SPEED = 60.0

logger = shotLogger.logger

class TransectShot():

    def __init__(self, vehicle, shotmgr):
        # assign the vehicle object
        self.vehicle = vehicle

        # assign the shotManager object
        self.shotmgr = shotmgr

        # default pathHandler to none
        self.pathHandler = None

        # default gimbal into mavlink targeting mode
        self.setupTargeting()

        # initialize roi object to none
        self.roi = None

        # default camYaw to current pointing
        self.camYaw = camera.getYaw(self.vehicle)
        
        # enter GUIDED mode
        self.vehicle.mode = VehicleMode("GUIDED")

        #disable stick deadzones for throttle and yaw
        self.shotmgr.rcMgr.enableRemapping( True )

        #state machine
        self.state = SETUP
        
        #state machine
        self.lastShot = -1
        
        # distance traveled
        self.dist = 0
        
        # distance between photos in M
        self.triggerDist = 10
        
        # length of cable
        self.transectLength = MIN_TRANSECT_LENGTH

        self.start_loc = None
        
        # used for timing
        self.ticks = 0
        
        # set Camera to Photo
        self.enterPhotoMode()

        

    # channels are expected to be floating point values in the (-1.0, 1.0) range
    def handleRCs(self, channels):
        if self.state == SETUP:
            # point stright ahead
            self.camPitch = 0
            # allow user to point Solo
            self.manualYaw(channels)
            self.ticks = 0
                        
        elif self.state == TILT:
            # point straight down
            self.camPitch = -90
            self.ticks += 1
            if self.ticks > STARTUP_DELAY:
                # take first shot
                self.shotmgr.goproManager.handleRecordCommand(self.shotmgr.goproManager.captureMode, RECORD_COMMAND_TOGGLE)
                self.pathHandler.setCruiseSpeed(TRANSECT_SPEED) #temp
                self.state = RUN
        
        elif self.state == RUN:
            self.ticks = 0
            self.calcPhoto()
            self.pathHandler.MoveTowardsEndpt(channels)

            # pause at the end of "infinity"!
            if self.pathHandler.isNearTarget():
                self.pathHandler.pause()
                #take 1 more photo
                self.shotmgr.goproManager.handleRecordCommand(self.shotmgr.goproManager.captureMode, RECORD_COMMAND_TOGGLE)
                self.state = FINISH
                
        elif self.state == FINISH:
            self.ticks += 1            
            if self.ticks > STARTUP_DELAY:
                logger.log("[Transect] Finished")
                self.state = RETURN_TO_START
                self.pathHandler.setCruiseSpeed(-6)

        elif self.state == RETURN_TO_START:
            self.pathHandler.MoveTowardsEndpt(channels)
            if self.pathHandler.isNearTarget():
                self.pathHandler.currentSpeed = 0.0
                self.pathHandler.pause()
                self.shotmgr.enterShot(shots.APP_SHOT_NONE)        
            

                
        self.handlePitchYaw()


    def calcPhoto(self):
        '''determins when to shoot photo based on distance'''
        # calc distance from home
        self.dist = location_helpers.getDistanceFromPoints(self.pathHandler.pt1, self.vehicle.location.global_relative_frame)

        # find a slot
        index =  math.floor(self.dist / self.triggerDist)

        if self.lastShot != index:
            self.lastShot = index
            self.shotmgr.goproManager.handleRecordCommand(self.shotmgr.goproManager.captureMode, RECORD_COMMAND_TOGGLE)


    def setupWaypoints(self):
        '''setup our two waypoints'''
        # we want two points that are far apart
        # both in the direction we're looking and the opposite direction

        # get vehicle state
        self.start_loc = self.vehicle.location.global_relative_frame

        self.triggerDist = self.start_loc.alt * OVERLAP
        self.triggerDist = max(self.triggerDist, MIN_TRIGGER_DIST)
        
        # calculate the foward point
        forwardPt = location_helpers.newLocationFromAzimuthAndDistance(self.start_loc, self.camYaw, self.transectLength)
        
        # create a new pathHandler obejct with our new points
        # this will automatically reset resumeSpeed, cruiseSpeed etc...
        self.pathHandler = pathHandler.TwoPointPathHandler(self.start_loc, forwardPt, self.vehicle, self.shotmgr)
        #self.addLocation(forwardPt)
        
        
    def handleButton(self, button, event):
        if self.state == SETUP and button == btn_msg.ButtonA and event == btn_msg.Press:
            self.state = TILT
            self.setupWaypoints()
            self.setButtonMappings()

        if self.state == SETUP and button == btn_msg.ButtonB and event == btn_msg.Press:
            self.transectLength += 25
            if self.transectLength > MAX_TRANSECT_LENGTH:
                self.transectLength = MIN_TRANSECT_LENGTH
            # redo path
            self.setButtonMappings()

        if button == btn_msg.ButtonLoiter and event == btn_msg.Press:
            if self.pathHandler:
                self.pathHandler.togglePause()
                self.updateAppOptions()


    def setButtonMappings(self):
        buttonMgr = self.shotmgr.buttonManager
        if self.state == SETUP:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_TRANSECT, btn_msg.ARTOO_BITMASK_ENABLED, "Begin\0")
            buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_TRANSECT, btn_msg.ARTOO_BITMASK_ENABLED, str(self.transectLength)+"m\0")
        else:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_TRANSECT, 0, "\0")
            buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_TRANSECT, btn_msg.ARTOO_BITMASK_ENABLED, "("+str(self.transectLength)+"m)\0")


    def updateAppOptions(self):
        '''send our current set of options to the app'''
        return

    def addLocation(self, loc):
        '''called by shot manager to set new ROI from App'''
        return


    def manualYaw(self, channels):
        if channels[YAW] == 0:
            return

        self.camYaw += channels[YAW] * YAW_SPEED * UPDATE_TIME
        
        if self.camYaw > 360:
            self.camYaw -= 360
        if self.camYaw < 0:
            self.camYaw += 360


    def setupTargeting(self):
        '''set gimbal targeting mode'''
        msg = self.vehicle.message_factory.mount_configure_encode(
            0, 1,    # target system, target component
            mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,  # mount_mode
            1,  # stabilize roll
            1,  # stabilize pitch
            1,  # stabilize yaw
        )

        logger.log("setting gimbal to mavlink mode")
        self.vehicle.send_mavlink(msg)


    def handlePitchYaw(self):
        '''Handle free look'''
        # if we do have a gimbal, use mount_control to set pitch and yaw
        if self.vehicle.mount_status[0] is not None:
            msg = self.vehicle.message_factory.mount_control_encode(
                0, 1,    # target system, target component
                # pitch is in centidegrees
                self.camPitch * 100,
                0.0,  # roll
                # yaw is in centidegrees
                self.camYaw * 100,
                0  # save position
            )
        self.vehicle.send_mavlink(msg)


    def enterPhotoMode(self):
        # switch into photo mode if we aren't already in it
        if self.shotmgr.goproManager.captureMode != CAPTURE_MODE_PHOTO:
            self.shotmgr.goproManager.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_CAPTURE_MODE, (CAPTURE_MODE_PHOTO, 0 ,0 , 0))


    def handlePacket(self, packetType, packetLength, packetValue):
        try:
            return False
        except Exception as e:
            logger.log('[selfie]: Error handling packet. (%s)' % e)
            return False
        else:
            return True
