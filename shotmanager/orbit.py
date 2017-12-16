#  orbit.py
#  shotmanager
#
#  The orbit smart shot.
#  Runs as a DroneKit-Python script.
#
#  Created by Will Silva and Eric Liao on 1/19/2015.
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
import pathHandler
import shotLogger
from shotManagerConstants import *
import shots
import socket
import orbitController
from orbitController import OrbitController
from vector3 import Vector3
from sololink import btn_msg

SHALLOW_ANGLE_THRESHOLD = -5

# if we didn't aim at the ground or we don't have a gimbal
MAX_ALT_DIFF = 9999.0

TICKS_TO_IGNORE_PADDLE = 2.0 * UPDATE_RATE

# in degrees per second
YAW_SPEED = 25.0
APP_UPDATE = 15

DEFAULT_PILOT_VELZ_MAX_VALUE = 133.0
ZVEL_FACTOR = 0.95

logger = shotLogger.logger

class OrbitShot():
    def __init__(self, vehicle, shotmgr):

        # copy vehicle object
        self.vehicle = vehicle

        # reference shotManager object
        self.shotmgr = shotmgr

        # initialize roi to None
        self.roi = None

        # Altitude difference between where the ROI is and where the camera should look
        self.ROIAltitudeOffset = 0
        
        # should we inform the app the ROI has moved
        self.roi_needsUpdate = False
        
        # counter to send perioidic app updates when needed
        self.appNeedsUpdate = 0

        # initialize path controller to None
        self.pathController = None

        # keep track of how long we've kept the paddle centered
        self.ticksPaddleCentered = float('inf')

        # initialize pathHandler to None
        self.pathHandler = None

        # get max climb rate from APM parameters
        self.maxClimbRate = self.shotmgr.getParam( "PILOT_VELZ_MAX", DEFAULT_PILOT_VELZ_MAX_VALUE ) / 100.0 * ZVEL_FACTOR

        # log the max altitude downloaded from APM
        logger.log("[orbit]: Maximum climb rate stored: %f" % self.maxClimbRate)

        # get max altitude from APM parameters
        self.maxAlt = self.shotmgr.getParam( "FENCE_ALT_MAX", DEFAULT_FENCE_ALT_MAX )

        # log the max altitude downloaded from APM
        logger.log("[orbit]: Maximum altitude stored: %f" % self.maxAlt)

        # check APM params to see if Altitude Limit should apply
        if self.shotmgr.getParam( "FENCE_ENABLE", DEFAULT_FENCE_ENABLE ) == 0:
            self.maxAlt = None
            logger.log("[Orbit]: Altitude Limit is disabled.")

        # Now change the vehicle into guided mode
        self.vehicle.mode = VehicleMode("GUIDED")

        # set gimbal targeting mode
        msg = self.vehicle.message_factory.mount_configure_encode(
                    0, 1,    # target system, target component
                    mavutil.mavlink.MAV_MOUNT_MODE_GPS_POINT,  #mount_mode
                    1,  # stabilize roll
                    1,  # stabilize pitch
                    1,  # stabilize yaw
                    )

        self.vehicle.send_mavlink(msg)

        # enable stick remappings
        self.shotmgr.rcMgr.enableRemapping( True )


    # channels are expected to be floating point values in the (-1.0, 1.0) range
    def handleRCs( self, channels ):

        # don't continue until an roi is set
        if not self.pathHandler or not self.roi:
            return
        
        # allow user to rotate the ROI about the vehicle
        if abs(channels[YAW]) > 0:
            # adding 180 flips the az (ROI to vehicle) to (vehicle to ROI)
            tmp = self.roi.alt
            self.pathController.azimuth += channels[YAW] * YAW_SPEED  * UPDATE_TIME

            self.roi = location_helpers.newLocationFromAzimuthAndDistance(
                        self.vehicle.location.global_relative_frame, 
                        180 + self.pathController.azimuth, 
                        self.pathController.radius)
            self.roi.alt = tmp
            self.roi_needsUpdate = True
        
        # call path controller
        pos, vel = self.pathController.move(channels, self.pathHandler.cruiseSpeed, self.roi)

        # mavlink expects 10^7 integer for accuracy
        latInt = int(pos.lat * 10000000)
        lonInt = int(pos.lon * 10000000)

        # create the SET_POSITION_TARGET_GLOBAL_INT command
        msg = self.vehicle.message_factory.set_position_target_global_int_encode(
             0,       # time_boot_ms (not used)
             0, 1,    # target system, target component
             mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, # frame
             0b0000110111000000, # type_mask - enable pos/vel
             latInt, lonInt, pos.alt, # x, y, z positions
             vel.x, vel.y, vel.z, # x, y, z velocity in m/s
             0, 0, 0, # x, y, z acceleration (not used)
             0, 0)    # yaw, yaw_rate (not used)

        # send command to vehicle
        self.vehicle.send_mavlink(msg)

        # pointing logic

        # Adjust the height of the ROI using the paddle
        # we pass in both the filtered gimbal paddle value as well as the raw one
        self.setROIAltitude( channels[5], channels[7] )
        
        # set ROI
        msg = self.vehicle.message_factory.command_long_encode(
                    0, 1,    # target system, target component
                    mavutil.mavlink.MAV_CMD_DO_SET_ROI, #command
                    0, #confirmation
                    0, 0, 0, 0, #params 1-4
                    self.roi.lat,
                    self.roi.lon,
                    self.roi.alt + self.ROIAltitudeOffset
                    )

        # send pointing message for either cam mode
        self.vehicle.send_mavlink(msg)
        self.updateApp()


    def updateApp(self):
        # used to limit the bandwidth needed to transmit many ROI updates
        self.appNeedsUpdate += 1

        if self.appNeedsUpdate > APP_UPDATE:
            self.appNeedsUpdate = 0
            if self.roi_needsUpdate:
                self.roi_needsUpdate = False
                # send this ROI to the app
                #logger.log("ROI %f %f" % (self.roi.lat, self.roi.lon))
                packet = struct.pack('<IIddf', app_packet.SOLO_MESSAGE_LOCATION, 20, self.roi.lat, self.roi.lon, self.roi.alt)
                self.shotmgr.appMgr.sendPacket(packet)


    def spotLock(self):
        '''take the angle of the copter and lock onto a ground level target'''
        logger.log("[Orbit] spotLock")
        
        # don't use a shallow angle resulting in massively distant ROIs
        pitch = min(camera.getPitch(self.vehicle), SHALLOW_ANGLE_THRESHOLD)

        # Get ROI for the vehicle to look at
        spotLock = location_helpers.getSpotLock(self.vehicle.location.global_relative_frame, pitch, camera.getYaw(self.vehicle))
        self.addLocation(spotLock)


    def addLocation(self, loc):
        '''Adds a new or overwrites the current orbit ROI'''        
        self.roi = loc

        # tell the app about the new ROI
        packet = struct.pack('<IIddf', app_packet.SOLO_MESSAGE_LOCATION, 20, self.roi.lat, self.roi.lon, self.roi.alt)
        self.shotmgr.appMgr.sendPacket(packet)

        # should we init the Orbit state machine
        if self.pathHandler is None:
            self.initOrbitShot()

        # Initialize the location of the vehicle
        startRadius = location_helpers.getDistanceFromPoints(self.roi, self.vehicle.location.global_relative_frame)
        startAz     = location_helpers.calcAzimuthFromPoints(self.roi, self.vehicle.location.global_relative_frame)
        startAlt    = self.vehicle.location.global_relative_frame.alt

        logger.log("[Orbit]: Add Location for Orbit controller.")
        logger.log("[Orbit]: -->radius: %f, azimuth: %f" % (startRadius, startAz))
        logger.log("[Orbit]: -->lat: %f, lon: %f, alt: %f" % (self.roi.lat, self.roi.lon, self.roi.alt))

        # Initialize the open-loop orbit controller
        self.pathController = orbitController.OrbitController(self.roi, startRadius, startAz, startAlt)
        self.pathController.setOptions(maxClimbRate = self.maxClimbRate, maxAlt = self.maxAlt)
        

    def initOrbitShot(self):
        '''Initialize the orbit autonomous controller - called once'''
        
        # create pathHandler object
        self.pathHandler = pathHandler.PathHandler( self.vehicle, self.shotmgr )

        # set button mappings
        self.setButtonMappings()
        

    def setButtonMappings(self):
        '''Map the controller buttons'''
        buttonMgr = self.shotmgr.buttonManager

        if self.roi:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_ORBIT, 0, "\0")
        else:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_ORBIT, btn_msg.ARTOO_BITMASK_ENABLED, "Begin\0")

        buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_ORBIT, 0, "\0")

    def handleButton(self, button, event):
        '''Handle a controller button press'''

        if button == btn_msg.ButtonA and event == btn_msg.ClickRelease:
            if self.roi is None:
                self.spotLock()
        if button == btn_msg.ButtonLoiter and event == btn_msg.ClickRelease:
            if self.pathHandler:
                self.pathHandler.togglePause()
                self.updateAppOptions()
                self.shotmgr.notifyPause(True)
            else:
                self.shotmgr.notifyPause(False)

    def updateAppOptions(self):
        '''send our current set of options to the app'''

        packet = struct.pack('<IIf', app_packet.SOLO_SHOT_OPTIONS, 4, self.pathHandler.cruiseSpeed)
        self.shotmgr.appMgr.sendPacket(packet)

    # Sets our ROI according to the filtered gimbal paddle.
    # We know the desired gimbal angle (linear conversion from filtered gimbal paddle value)
    # So we just need to convert that to an ROI altitude
    # We only use this to set our ROI if the user is actually adjusting it.
    # In order to tell, we compare rawPaddleValue to 0.0, but we need to wait a bit
    # so that filteredPaddleInput settles
    # NOTE:  This will not handle preset gimbal animations from Artoo.  But
    # I don't think there's a way to do that without adding more messaging between Artoo/shot manager.
    # Using a preset during an Orbit isn't something anyone's asked for.
    #
    # Note that we no longer update the actual ROI and instead just maintain an offset that is adjusted for pointing (but the vehicle is still controlled relative to the original ROI)
    def setROIAltitude(self, filteredPaddleInput, rawPaddleValue):
        # no gimbal, no reason to change ROI
        if self.vehicle.mount_status[0] == None:
            return

        # if the paddle is centered, we tick up our count
        # If it's been centered for long enough don't allow the filtered paddle value to
        # overwrite our ROI Alt
        # We want to wait a little bit after the gimbal paddle returns to center so that
        # the filtered value stabilizes
        if rawPaddleValue == 0.0:
            self.ticksPaddleCentered += 1
            if self.ticksPaddleCentered > TICKS_TO_IGNORE_PADDLE:
                return
        else:
            self.ticksPaddleCentered = 0

        # our input is in the range (-1.0, 1.0)
        # let's convert it to a desired angle, where -1.0 -> -90.0 and 1.0 -> 0.0
        input = ( filteredPaddleInput + 1.0 ) / 2.0
        # inverse it
        input = 1.0 - input
        # convert to gimbal range in radians
        theta = input * math.radians(90.0)

        # now we want to calculate our altitude difference of our ROI
        # we want our ROI to be at angle theta from our copter
        # tan theta = altDiff / radius
        # altDiff = radius * tan theta
        tanTheta = math.tan(theta)
        altDiff = self.pathController.radius * tanTheta
        # In the case that we're pointing straight down,
        # cap the number we're sending, because otherwise it'll cause issues.
        if altDiff > MAX_ALT_DIFF:
            altDiff = MAX_ALT_DIFF

        # XXX suspect - why bring in vehicle alt to open loop controller?
        self.ROIAltitudeOffset = self.vehicle.location.global_relative_frame.alt - altDiff

    def handlePacket(self, packetType, packetLength, packetValue):
        try:
            if packetType == app_packet.SOLO_RECORD_POSITION:
                logger.log("[orbit]: record spotlock")
                self.spotLock()

            elif packetType == app_packet.SOLO_MESSAGE_LOCATION:
                (lat, lon, alt) = struct.unpack('<ddf', packetValue)
                logger.log("[orbit]: Location received from app: %f, %f, %f." %( lat, lon, alt ) )
                # forces the controller to reset the pathhandler
                self.roi = None
                self.addLocation(LocationGlobalRelative(lat, lon, alt))
            
            elif packetType == app_packet.SOLO_SHOT_OPTIONS:
                if self.pathHandler:
                    (cruiseSpeed,) = struct.unpack('<f', packetValue)
                    self.pathHandler.setCruiseSpeed(cruiseSpeed)
                    logger.log("[orbit]: Cruise speed set to %.2f." % (cruiseSpeed,))
            else:
                return False
        except Exception as e:
            logger.log('[orbit]: Error handling packet. (%s)' % e)
            return False
        else:
            return True
