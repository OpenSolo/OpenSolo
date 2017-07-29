#
#  zipline.py
#  shotmanager
#
#  The zipline smart shot controller.
#  Runs as a DroneKit-Python script.
#
#  Created by Jason Short
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
import vectorPathHandler
import shotLogger
import shots
from shotManagerConstants import *
# on host systems these files are located here
sys.path.append(os.path.realpath('../../flightcode/stm32'))
from sololink import btn_msg

SHALLOW_ANGLE_THRESHOLD = -5
ROI_ALT_MAX_DELTA = 50

# States
ZIPLINE_SETUP = 0
ZIPLINE_RUN = 1

# Camera modes
FREE_LOOK = 0
SPOT_LOCK = 1

YAW_SPEED = 60.0
PITCH_SPEED = 60.0
YAW_NUDGE_SPEED = 35.0
FOLLOW_ALT_NUDGE_SPEED = 6

MIN_PADDLE_THRESHOLD = 0.02
ROI_ALT_MARGIN = 5

logger = shotLogger.logger

class ZiplineShot():

    def __init__(self, vehicle, shotmgr):
        self.vehicle = vehicle
        self.shotmgr = shotmgr

        # Limit ziplines to a plane parallel with Earth surface
        self.is3D = False

        # default pathHandler to none
        self.pathHandler = None
        
        # track cruise speed between pathHandler instances
        self.cruiseSpeed = 0
        
        # tracks the camera control mode
        self.camPointing = FREE_LOOK

        # ROI will update when this is True
        self.needsUpdate = True

        # Camera control
        self.camYaw = camera.getYaw(self.vehicle)
        self.camPitch = camera.getPitch(self.vehicle)
        self.camDir = 1

        # initialize roi object to none
        # roi used to store spot lock location object
        self.roi = None

        self.state = ZIPLINE_SETUP



    # channels are expected to be floating point values in the (-1.0, 1.0) range
    def handleRCs(self, channels):
        if self.state == ZIPLINE_SETUP:
            return

        # handle camera per camera mode
        if self.camPointing == SPOT_LOCK:
            self.handleSpotLock(channels)
        else:
            # Freelook
            self.manualPitch(channels)
            self.manualYaw(channels)
            self.handleFreeLookPointing()
        
        # Vechicle control on the zipline
        if self.pathHandler is not None:
            self.pathHandler.move(channels)


    def setupZipline(self):
        if self.state == ZIPLINE_SETUP:
            # enter GUIDED mode
            self.vehicle.mode = VehicleMode("GUIDED")

            # Take over RC
            self.shotmgr.rcMgr.enableRemapping( True )
            
            # default camera mode to FREE LOOK
            self.camPointing = -1
            self.initCam(FREE_LOOK)

            self.state = ZIPLINE_RUN
        

        # re-init Yaw
        self.camYaw = camera.getYaw(self.vehicle)

        # null pitch if we only want 2D ziplines
        if self.is3D == 0:
            self.camPitch = 0

        # create a new pathHandler obejct with our new points
        self.pathHandler = vectorPathHandler.VectorPathHandler(self.vehicle, self.shotmgr, self.camYaw, self.camPitch)
        self.pathHandler.setCruiseSpeed(self.cruiseSpeed)
        
        # re-init Pitch
        self.camPitch = camera.getPitch(self.vehicle)

        # update the app
        self.updateAppOptions()
        self.updateAppStart()


    def setButtonMappings(self):
        buttonMgr = self.shotmgr.buttonManager
        buttonMgr.setArtooButton(
            btn_msg.ButtonA, shots.APP_SHOT_ZIPLINE, btn_msg.ARTOO_BITMASK_ENABLED, "New Zipline\0")

        if self.camPointing == SPOT_LOCK:
            buttonMgr.setArtooButton(
                btn_msg.ButtonB, shots.APP_SHOT_ZIPLINE, btn_msg.ARTOO_BITMASK_ENABLED, "Free Look\0")
        else:
            buttonMgr.setArtooButton(
                btn_msg.ButtonB, shots.APP_SHOT_ZIPLINE, btn_msg.ARTOO_BITMASK_ENABLED, "Spot Lock\0")


    def handleButton(self, button, event):
        if button == btn_msg.ButtonA and event == btn_msg.Press:
            self.setupZipline()

        if button == btn_msg.ButtonB and event == btn_msg.Press:
            # Toggle between free look and spot lock
            if self.camPointing is FREE_LOOK:
                self.initCam(SPOT_LOCK)
            else:
                self.initCam(FREE_LOOK)

        if button == btn_msg.ButtonLoiter and event == btn_msg.Press:
            if self.pathHandler:
                self.pathHandler.togglePause()
                self.cruiseSpeed = self.pathHandler.cruiseSpeed
                self.updateAppOptions()


    def initCam(self, _camPointing):
        if _camPointing == self.camPointing:
            return
        
        if _camPointing is SPOT_LOCK:
            self.spotLock()
            self.camPointing = _camPointing
        else:
            self.manualGimbalTargeting()
            self.camPointing = _camPointing
        
        self.setButtonMappings()
        self.updateAppOptions()
        
        
    def updateAppOptions(self):
        '''send our current set of options to the app'''
        # B = uint_8 
        if self.pathHandler is None:
            return
            
        packet = struct.pack('<IIfBB', app_packet.SOLO_ZIPLINE_OPTIONS, 6, self.pathHandler.cruiseSpeed, self.is3D, self.camPointing)
        self.shotmgr.appMgr.sendPacket(packet)


    def updateAppStart(self):
        '''Let app know we've started'''
        if self.pathHandler is None:
            return
        logger.log("[ZIPLINE]: send App Start")
        packet = struct.pack('<II', app_packet.SOLO_ZIPLINE_LOCK, 0)
        self.shotmgr.appMgr.sendPacket(packet)


    def handlePacket(self, packetType, packetLength, packetValue):
        '''handle incoming data from the client app'''
        try:
            if packetType == app_packet.SOLO_MESSAGE_LOCATION:
                (lat, lon, alt) = struct.unpack('<ddf', packetValue)
                logger.log("[ZIPLINE]: Location received from app: %f, %f, %f." %( lat, lon, alt ) )
                # dont read alt from App - it has no way to set it from UI
                self.addLocation(LocationGlobalRelative(lat, lon, self.roi.alt))
            
            elif packetType == app_packet.SOLO_ZIPLINE_OPTIONS:
                (self.cruiseSpeed, self.is3D, _camPointing) = struct.unpack('<fBB', packetValue)
                logger.log( "[ZIPLINE]: Set cruise speed to %f"% (self.cruiseSpeed,))
                logger.log( "[ZIPLINE]: Set 3D path %d"% (self.is3D,))
                logger.log( "[ZIPLINE]: Cam pointing %d"% (_camPointing,))
                self.setButtonMappings()
                self.initCam(_camPointing)
                if self.pathHandler:
                    self.pathHandler.setCruiseSpeed(self.cruiseSpeed)

            elif packetType == app_packet.SOLO_ZIPLINE_LOCK:
                self.setupZipline()
                
            else:
                return False
        except Exception as e:
            logger.log('[ZIPLINE]: Error handling packet. (%s)' % e)
            return False
        else:
            return True


    def addLocation(self, loc):
        '''called by shot manager to set new ROI from App'''
        # replaces our ROI
        self.roi = loc

        # send this ROI to the app
        packet = struct.pack('<IIddf', app_packet.SOLO_MESSAGE_LOCATION, 20, loc.lat, loc.lon, loc.alt)
        self.shotmgr.appMgr.sendPacket(packet)


    def spotLock(self):
        '''take the angle of the copter and lock onto a ground level target'''
        if self.camPointing == SPOT_LOCK:
            return

        self.needsUpdate = True

        # don't use a shallow angle resulting in massively distant ROIs
        pitch = min(camera.getPitch(self.vehicle), SHALLOW_ANGLE_THRESHOLD)

        # Get ROI for the vehicle to look at
        spotLock = location_helpers.getSpotLock(self.vehicle.location.global_relative_frame, pitch, camera.getYaw(self.vehicle))
        self.addLocation(spotLock)

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


    def handleSpotLock(self, channels):
        '''handle spot lock'''
        # we rotate this value for re-pointing
        dist = location_helpers.getDistanceFromPoints(self.vehicle.location.global_relative_frame, self.roi)

        # rotate the ROI point
        if abs(channels[YAW]) > 0:
            self.needsUpdate = True
            tmp = self.roi.alt
            az = location_helpers.calcAzimuthFromPoints(self.vehicle.location.global_relative_frame, self.roi)
            az += (channels[YAW] * YAW_NUDGE_SPEED * UPDATE_TIME)
            newRoi = location_helpers.newLocationFromAzimuthAndDistance(self.vehicle.location.global_relative_frame, az, dist)
            newRoi.alt = tmp
            self.addLocation(newRoi)

        self.updateROIAlt(channels[RAW_PADDLE])

        # nothing to do if no user interaction
        if not self.needsUpdate:
            return

        # clear update flag
        self.needsUpdate = False

        # Tell Gimbal ROI Location
        msg = self.vehicle.message_factory.command_int_encode(
                    0, 1,    # target system, target component
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, #frame
                    mavutil.mavlink.MAV_CMD_DO_SET_ROI, #command
                    0, #current
                    0, #autocontinue
                    0, 0, 0, 0, #params 1-4
                    self.roi.lat*1.E7,
                    self.roi.lon*1.E7,
                    self.roi.alt)

        self.vehicle.send_mavlink(msg)

    # moves an offset of the ROI altitude up or down
    def updateROIAlt(self, rawPaddleValue):
        # no gimbal, no reason to change ROI
        if self.vehicle.mount_status[0] == None:
            return

        if abs(rawPaddleValue) > MIN_PADDLE_THRESHOLD:
            self.roi.alt += (rawPaddleValue * FOLLOW_ALT_NUDGE_SPEED * UPDATE_TIME)
            self.roi.alt = min(self.vehicle.location.global_relative_frame.alt + ROI_ALT_MARGIN, self.roi.alt)
            self.roi.alt = max(self.vehicle.location.global_relative_frame.alt - ROI_ALT_MAX_DELTA, self.roi.alt)

