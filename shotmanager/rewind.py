#
#  rewind.py
#  shotmanager
#
#  The Rewind RTL shot controller.
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
import time
from vector3 import Vector3

sys.path.append(os.path.realpath(''))
import app_packet
import camera
import location_helpers
import shotLogger
from shotManagerConstants import *
import shots

# spline
import cableController
from cableController import CableController
import monotonic

# on host systems these files are located here
sys.path.append(os.path.realpath('../../flightcode/stm32'))
from sololink import btn_msg

# for manual control of the camera during rewind
YAW_SPEED = 60.0
PITCH_SPEED = 60.0

# spline speed control
REWIND_SPEED = 3.5
REWIND_MIN_SPEED = 0.5

# distance to exit rewind if we are near home
REWIND_MIN_HOME_DISTANCE = 6.0

logger = shotLogger.logger

# spline
ACCEL_LIMIT = 2.5 #m/s^2
NORM_ACCEL_LIMIT = 2.25 #m/s^2
TANGENT_ACCEL_LIMIT = math.sqrt(ACCEL_LIMIT**2-NORM_ACCEL_LIMIT**2) #m/s^2


class RewindShot():

    def __init__(self, vehicle, shotmgr):

        # assign the vehicle object
        self.vehicle = vehicle

        # assign the shotManager object
        self.shotmgr = shotmgr

        # Exit the shot and use RTL Mode
        self.vehicle.mode = VehicleMode("RTL")
        self.shotmgr.rcMgr.enableRemapping( false )
        return

        ############################################################

        # data manager for breadcrumbs
        self.rewindManager = shotmgr.rewindManager

        # defines how we exit
        self.exitToRTL = True
        
        # enable stick remappings
        self.shotmgr.rcMgr.enableRemapping( True )

        # enter GUIDED mode
        logger.log("[Rewind] Try Guided")
        self.setButtonMappings()
        self.vehicle.mode = VehicleMode("GUIDED")

        # grab a copy of home
        self.homeLocation = self.shotmgr.getHomeLocation()        

        ''' spline '''        
        # default targetP
        self.targetP = 0.0

        # initialize cable to None
        self.cable = None
        
        # last time that the controller was advanced
        self.lastTime = None
        
        self.splineOrigin = None
        
        if not self.generateSplines():
            logger.log("[Rewind]: Spline generation failed.")

        if self.cable is not None:
            # go to 1.0
            self.cable.setTargetP(1.0)

            # give cable controller our desired speed
            self.cable.trackSpeed(REWIND_SPEED)
        
            # Camera control
            self.camYaw = camera.getYaw(self.vehicle)
            self.camPitch = camera.getPitch(self.vehicle)
            self.camDir = 1
            self.manualGimbalTargeting()
        

    def handleRCs(self, channels):
        if self.cable is None:
            if self.exitToRTL:
                self.exitRewind()
            else:
                self.shotmgr.enterShot(shots.APP_SHOT_NONE)
            return
        
        self.travel()

        # Freelook
        self.manualPitch(channels)
        self.manualYaw(channels)
        self.handleFreeLookPointing()            
        
        if self.cable.reachedTarget():
            self.cable.trackSpeed(0)
            if self.exitToRTL:
                logger.log("[Rewind] exiting at end of Spline")
                self.exitRewind()

        if self.isNearHome():
            if self.exitToRTL:
                logger.log("[Rewind] Exiting Near Home")
                self.exitRewind()


    def exitRewind(self):
        self.rewindManager.resetSpline()
        self.vehicle.mode = VehicleMode("RTL")

        
    def travel(self):
        # advance cable controller by dt (time elapsed)
        now = monotonic.monotonic()
        if self.lastTime is None:
            dt = UPDATE_TIME
        else:
            dt = now - self.lastTime
        self.lastTime = now

        self.cable.update(dt)

        # add NED position vector to spline origin (addVectorToLocation needs NEU)
        self.commandPos = location_helpers.addVectorToLocation(self.splineOrigin, Vector3(self.cable.position.x, self.cable.position.y, -self.cable.position.z))

        # assign velocity from controller
        self.commandVel = self.cable.velocity

        # formulate mavlink message for pos-vel controller
        posVelMsg = self.vehicle.message_factory.set_position_target_global_int_encode(
            0,       # time_boot_ms (not used)
            0, 1,    # target system, target component
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,  # frame
            0b0000110111000000,  # type_mask - enable pos/vel
            int(self.commandPos.lat * 10000000),  # latitude (degrees*1.0e7)
            int(self.commandPos.lon * 10000000),  # longitude (degrees*1.0e7)
            self.commandPos.alt,  # altitude (meters)
            self.commandVel.x, self.commandVel.y, self.commandVel.z,  # North, East, Down velocity (m/s)
            0, 0, 0,  # x, y, z acceleration (not used)
            0, 0)    # yaw, yaw_rate (not used)

        # send pos-vel command to vehicle
        self.vehicle.send_mavlink(posVelMsg)


    def isNearHome(self):
        if self.homeLocation is None:
            return True

        mydist = location_helpers.getDistanceFromPoints(self.vehicle.location.global_relative_frame, self.homeLocation)
        return (mydist < REWIND_MIN_HOME_DISTANCE)


    def handleButton(self, button, event):
        # any Pause button press or release should get out of Rewind
        if button == btn_msg.ButtonLoiter and (event == btn_msg.Release or event == btn_msg.ClickRelease):
            #exit to fly
            self.shotmgr.enterShot(shots.APP_SHOT_NONE)
        return


    def handlePacket(self, packetType, packetLength, packetValue):
        return False


    def setButtonMappings(self):
        buttonMgr = self.shotmgr.buttonManager
        buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_REWIND, 0, "\0")
        buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_REWIND, 0, "\0")


    def updateAppOptions(self):
        return

    def addLocation(self, loc):
        return

    def generateSplines(self):
        '''Generate the multi-point spline'''

        logger.log("[Rewind] generateSplines")
        # store the Lat,lon,alt locations
        ctrlPtsLLA = []
        # store vectors for relative offsets
        ctrlPtsCart = []
        # set initial control point as origin
        ctrlPtsCart.append(Vector3(0, 0, 0))

        # try and load a point
        loc = self.rewindManager.queueNextloc()
        if loc is None:
            return False

        logger.log("[Rewind] read loc: %f %f %f" % (loc.lat, loc.lon, loc.alt))

        ctrlPtsLLA.append(loc)
        # store as spline origin
        self.splineOrigin = ctrlPtsLLA[0]
        
        # read all available locations
        while (loc is not None):
            loc = self.rewindManager.queueNextloc()
            if loc is not None:
                logger.log("[Rewind] read loc: %f %f %f" % (loc.lat, loc.lon, loc.alt))
                ctrlPtsLLA.append(loc)
            else:
                print "loc: None"

        # try and have a 3 point spline or longer:
        if len(ctrlPtsLLA) < 2:
            return False

        # Save offsets from home for spline
        for n in range(1, len(ctrlPtsLLA)):
            ctrlPtsCart.append(location_helpers.getVectorFromPoints(self.splineOrigin, ctrlPtsLLA[n]))
            ctrlPtsCart[-1].z *= -1. #NED

        # Construct spline object
        try:
            self.cable = cableController.CableController(points = ctrlPtsCart, maxSpeed = REWIND_SPEED, minSpeed = REWIND_MIN_SPEED, tanAccelLim = TANGENT_ACCEL_LIMIT, normAccelLim = NORM_ACCEL_LIMIT, smoothStopP = 0.7, maxAlt = 400)
        except ValueError, e:
            logger.log("%s", e)
            return False

        #set the location to the start point
        self.cable.setCurrentP(0)
        return True


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


    def manualPitch(self, channels):
        if abs(channels[RAW_PADDLE]) > abs(channels[THROTTLE]):
            value = channels[RAW_PADDLE]
        else:
            value = channels[THROTTLE]

        self.camPitch += PITCH_SPEED * UPDATE_TIME * value

        if self.camPitch > 0.0:
            self.camPitch = 0.0
        elif self.camPitch < -90:
            self.camPitch = -90


    def manualYaw(self, channels):
        if channels[YAW] == 0:
            return

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
                0, 1,    # target system, target component
                # pitch is in centidegrees
                self.camPitch * 100.0,
                0.0,  # roll
                # yaw is in centidegrees
                self.camYaw * 100.0,
                0  # save position
            )
        else:
            # if we don't have a gimbal, just set CONDITION_YAW
            msg = self.vehicle.message_factory.command_long_encode(
                0, 0,    # target system, target component
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,  # command
                0,  # confirmation
                self.camYaw,  # param 1 - target angle
                YAW_SPEED,  # param 2 - yaw speed
                self.camDir,  # param 3 - direction XXX
                0.0,  # relative offset
                0, 0, 0  # params 5-7 (unused)
            )
        self.vehicle.send_mavlink(msg)
