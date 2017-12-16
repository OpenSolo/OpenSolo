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
from flyController import FlyController
import shots

# on host systems these files are located here
sys.path.append(os.path.realpath('../../flightcode/stm32'))
from sololink import btn_msg

logger = shotLogger.logger

# state management
RISING = 0
TRAVELING = 1
LANDING = 2

RTL_ALT = 2500 # store in cm
RTL_CONE_SLOPE = 1.5
RTL_MIN_RISE = 1
RTL_CLIMB_MIN = 10
RTL_LAND_SPEED_SLOW = .75
RTL_LAND_SPEED_FAST = 2.5
RTL_LAND_REPOSITION_SPEED = 2

MIN_HOME_DISTANCE = 1

# Accel/decel constants
ALT_ACCEL = .1
ALT_ACCEL_PER_TICK = ALT_ACCEL * UPDATE_TIME

# cam control
YAW_SPEED = 60.0
PITCH_SPEED = 60.0

class returnHomeShot():

    def __init__(self, vehicle, shotmgr):

        # assign the vehicle object
        self.vehicle = vehicle

        # assign the shotManager object
        self.shotmgr = shotmgr

        # Exit the shot and use RTL Mode
        self.vehicle.mode = VehicleMode("RTL")
        self.shotmgr.rcMgr.enableRemapping( false )
        return
        
        ##########################################################

        # grab a copy of home
        self.homeLocation = self.shotmgr.getHomeLocation()

        # enable stick remappings
        self.shotmgr.rcMgr.enableRemapping( True )

        # enter GUIDED mode
        logger.log("[RTL] Try Guided")
        self.setButtonMappings()
        self.vehicle.mode = VehicleMode("GUIDED")
    
        # sets desired climb altitude
        self.rtlAltParam = shotmgr.getParam( "RTL_ALT", RTL_ALT ) / 100.0
        self.returnAlt = max((self.vehicle.location.global_relative_frame.alt + RTL_CLIMB_MIN), self.rtlAltParam)
        self.returnAlt = self.coneOfAwesomeness(self.returnAlt)

        # open loop alt target
        self.targetAlt = self.vehicle.location.global_relative_frame.alt

        # manages acceleration of alt target
        self.desiredClimbRate = 0
        self.currentClimbRate = 0

        # init state machine
        self.state = RISING

        # Camera control
        self.camYaw = camera.getYaw(self.vehicle)
        self.camPitch = camera.getPitch(self.vehicle)
        self.camDir = 1
        self.manualGimbalTargeting()


    def handleRCs(self, channels):
        # Freelook during all phases of RTL
        self.manualPitch(channels)
        self.manualYaw(channels)
        self.handleFreeLookPointing()

        # if we don't have a home, just land;
        # should never happen, but...
        if self.homeLocation == None:
            self.setupLanding()

        if self.state is RISING:
            # rise to minimum altitude
            self.rise()
            if self.vehicle.location.global_relative_frame.alt > self.returnAlt:
                logger.log("[RTL] Completed Rise, Travel Home")
                self.state = TRAVELING
                self.comeHome()

        elif self.state is TRAVELING:
            if self.isNearHome():
                if self.shotmgr.rewindManager.hover == True:
                    #exit to fly
                    logger.log("[RTL] Landing disabled")
                    self.shotmgr.enterShot(shots.APP_SHOT_NONE)
                else:
                    logger.log("[RTL] Landing at home")
                    self.setupLanding()

        elif self.state is LANDING:
            # XXX hack until JC fixes Landing in Pos/Vel
            #self.land(channels)
            return


    def setupLanding(self):
        self.state = LANDING
        # re-init alt to deal with loss of alt during transit
        self.targetAlt = self.vehicle.location.global_relative_frame.alt
        # Initialize the feed-forward Fly controller
        temp = LocationGlobalRelative(self.homeLocation.lat, self.homeLocation.lon, self.targetAlt)
        self.pathController = FlyController(temp, 0, 0, 0, self.camYaw)
        self.pathController.setOptions(RTL_LAND_SPEED_FAST, 400)
        self.pathController.maxSpeed = RTL_LAND_REPOSITION_SPEED
        
        # XXX hack until JC fixes landing
        self.vehicle.mode = VehicleMode("LAND")


    def coneOfAwesomeness(self, _rtlAlt):
        ''' creates a cone above home that prevents massive altitude changes during RTL '''
        homeDistance = location_helpers.getDistanceFromPoints(self.vehicle.location.global_relative_frame, self.homeLocation)
        coneLimit = max(homeDistance * RTL_CONE_SLOPE, self.vehicle.location.global_relative_frame.alt + RTL_MIN_RISE)
        return min(coneLimit, _rtlAlt)


    def comeHome(self):
        # travel to home
        aboveHome = LocationGlobalRelative(self.homeLocation.lat, self.homeLocation.lon, self.returnAlt)
        self.vehicle.simple_goto(aboveHome)

        # should replace with a dronekit command when it gets in there
        msg = self.vehicle.message_factory.command_long_encode(
             0, 1,    # target system, target component
             mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
             0,       # confirmation
             1, RTL_SPEED, -1, # params 1-3
             0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)

        # send command to vehicle
        self.vehicle.send_mavlink(msg)


    def rise(self):
        self.desiredClimbRate = RTL_LAND_SPEED_FAST * UPDATE_TIME
        self.accelerateZ()
        self.targetAlt += self.currentClimbRate

        # formulate mavlink message for pos-vel controller
        posVelMsg = self.vehicle.message_factory.set_position_target_global_int_encode(
            0,       # time_boot_ms (not used)
            0, 1,    # target system, target component
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,  # frame
            0b0000110111000000,  # type_mask - enable pos/vel
            int(self.vehicle.location.global_relative_frame.lat * 10000000),  # latitude (degrees*1.0e7)
            int(self.vehicle.location.global_relative_frame.lon * 10000000),  # longitude (degrees*1.0e7)
            self.targetAlt,  # altitude (meters)
            0, 0, -self.currentClimbRate,  # North, East, Down velocity (m/s)
            0, 0, 0,  # x, y, z acceleration (not used)
            0, 0)    # yaw, yaw_rate (not used)

        # send pos-vel command to vehicle
        self.vehicle.send_mavlink(posVelMsg)


    def land(self, channels):
        pos, vel = self.pathController.move(channels, newHeading = self.camYaw)

        # if we are high, come down faster
        if self.vehicle.location.global_relative_frame.alt > 10:
            self.desiredClimbRate = -RTL_LAND_SPEED_FAST * UPDATE_TIME
        else:
            self.desiredClimbRate = -RTL_LAND_SPEED_SLOW * UPDATE_TIME

        self.accelerateZ()
        self.targetAlt += self.currentClimbRate

        # formulate mavlink message for pos-vel controller
        posVelMsg = self.vehicle.message_factory.set_position_target_global_int_encode(
            0,       # time_boot_ms (not used)
            0, 1,    # target system, target component
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,  # frame
            0b0000110111000000,  # type_mask - enable pos/vel
            int(pos.lat * 10000000),  # latitude (degrees*1.0e7)
            int(pos.lon * 10000000),  # longitude (degrees*1.0e7)
            self.targetAlt,  # altitude (meters)
            vel.x, vel.y, -self.currentClimbRate,  # North, East, Down velocity (m/s)
            0, 0, 0,  # x, y, z acceleration (not used)
            0, 0)    # yaw, yaw_rate (not used)

        # send pos-vel command to vehicle
        self.vehicle.send_mavlink(posVelMsg)


    def accelerateZ(self):
        # Synthetic acceleration
        if self.desiredClimbRate > self.currentClimbRate:
            self.currentClimbRate += ALT_ACCEL_PER_TICK
            self.currentClimbRate = min(self.currentClimbRate, self.desiredClimbRate)
        elif self.desiredClimbRate < self.currentClimbRate:
            self.currentClimbRate -= ALT_ACCEL_PER_TICK
            self.currentClimbRate = max(self.currentClimbRate, self.desiredClimbRate)
        else:
            self.currentClimbRate = self.desiredClimbRate


    def isNearHome(self):
        mydist = location_helpers.getDistanceFromPoints(self.vehicle.location.global_relative_frame, self.homeLocation)
        return (mydist < MIN_HOME_DISTANCE)


    def handleButton(self, button, event):

        # any Pause button press or release should get out of RTL
        if button == btn_msg.ButtonLoiter and event == btn_msg.ClickRelease:
            #exit to fly
            self.shotmgr.enterShot(shots.APP_SHOT_NONE)

        if button == btn_msg.ButtonRTL and event == btn_msg.LongHold and self.state is RISING:
            self.state = TRAVELING
            self.returnAlt = self.vehicle.location.global_relative_frame.alt
            self.comeHome()


    def handlePacket(self, packetType, packetLength, packetValue):
        return False


    def setButtonMappings(self):
        buttonMgr = self.shotmgr.buttonManager
        buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_REWIND, 0, "\0")
        buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_REWIND, 0, "\0")


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

        # init the open loop gimbal pointing vars
        self.camYaw = camera.getYaw(self.vehicle)
        self.camPitch = camera.getPitch(self.vehicle)


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

