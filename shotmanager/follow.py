'''
follow.py
shotmanager

The Follow Me smart shot controller.
Runs as a DroneKit-Python script.
Created by Will Silva on 12/14/2015.
Altitude and Leash follow created by Jason Short 2/25/2016

Copyright (c) 2016 3D Robotics.
Licensed under the Apache License, Version 2.0 (the "License");
You may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import os
import math
import struct
import monotonic
import collections
import app_packet
import camera
import location_helpers
import pathHandler
import shotLogger
import shots
import socket
from dronekit import Vehicle, LocationGlobalRelative, VehicleMode
from pymavlink import mavutil
from shotManagerConstants import *
from orbitController import OrbitController
from lookAtController import LookAtController
from flyController import FlyController
from leashController import LeashController
from os import sys, path
from vector3 import Vector3
from sololink import btn_msg
sys.path.append(os.path.realpath(''))

FOLLOW_PORT = 14558
SOCKET_TIMEOUT = 0.01

DEFAULT_PILOT_VELZ_MAX_VALUE = 133.0
ZVEL_FACTOR = 0.95

# in degrees per second for FREE CAM
YAW_SPEED = 120.0

MIN_RAW_ROI_QUEUE_LENGTH = 5
MIN_FILT_ROI_QUEUE_LENGTH = 4

#Path accel/decel constants
PATH_ACCEL = 2.5
ACCEL_PER_TICK = PATH_ACCEL * UPDATE_TIME

FOLLOW_ALT_NUDGE_SPEED = 6 # m/s
FOLLOW_ALT_ROI_OFFSET = 100
FOLLOW_ALT_PADDLE_DEADZONE = 0.02

FOLLOW_YAW_SPEED = 60.0 # deg/s
FOLLOW_PITCH_SPEED = 60.0 # deg/s

ROI_ALT_FILTER_GAIN = 0.65 # Relative contribution of the previous and new data in the phone altitude filter. Higher is slower and smoother.

logger = shotLogger.logger

'''
Define the different followStates:

Follow Wait
    Initial state before everything is ready. This state exits when the
    first ROI is sent from the app. (in filterROI()) The shot will probably
    only be in this state for a few ticks.
    
Look At Me
    Copter does not move unless commanded by stick actions, but the camera
    rotates to keep the ROI in frame
    
Follow Orbit: Default behaviour.
   Copter translates to keep the user in frame, maintining a offset in a
   particular direction (i.e. North) of the user. Once the orbit is started
   (cruise via the app or with sticks) then the copter orbits around the ROI,
   keeping the subject in frame.
   
Follow Leash
    Copter tries to stay behind the user's direction of motion.
    If the copter is within the leash length from the user, the leash is
    "slack" so the copter rotates but does not move. Once the copter gets
    further from the user. It swings around to get behind the user and keep up.
    User can adjust altitude and radius with sticks but cannot strafe manually.
    
Follow Free Look
    Copter maintains an offset from the ROI and can get dragged around as
    the ROI moves. User can move the copter with the roll/pitch sticks
    like FLY mode. User can adjust the altitude with the controller paddle.
    User can freely control the camera pan/tilt with the left stick. 
    Camera maintains constant yaw/pitch unless the user permutes it.
'''

FOLLOW_WAIT = 0
FOLLOW_LOOKAT = 1
FOLLOW_ORBIT = 2
FOLLOW_LEASH = 3
FOLLOW_FREELOOK = 4

# used to manage user preferences for different follow styles
FOLLOW_PREF_HOLD_ANGLE = 0
FOLLOW_PREF_FREELOOK = 1
FOLLOW_PREF_LEASH = 2


class FollowShot():
    def __init__(self, vehicle, shotmgr):
        # initialize vehicle object
        self.vehicle = vehicle

        # initialize shotmanager object
        self.shotmgr = shotmgr

        # initialize pathController to None
        self.pathController = None

        # used to manage cruise speed and pause control for orbiting
        self.pathHandler = pathHandler.PathHandler( self.vehicle, self.shotmgr )


        ''' Shot State '''
        self.followState = FOLLOW_WAIT

        self.followPreference = FOLLOW_PREF_HOLD_ANGLE

        # init camera mount style 
        self.updateMountStatus()


        ''' ROI control '''
        # initialize raw & filtered rois to None
        self.filteredROI = None
        self.rawROI = None

        # initialize raw and filtered roi queues
        self.rawROIQueue = collections.deque(maxlen=MIN_RAW_ROI_QUEUE_LENGTH)
        self.filteredROIQueue = collections.deque(maxlen=MIN_FILT_ROI_QUEUE_LENGTH)

        # initialize roiVelocity to None
        self.roiVelocity = None

        # for limiting follow acceleration could lead to some bad lag
        self.translateVel = Vector3()
        

        ''' Altitude Limit'''
        # get maxClimbRate and maxAltitude from APM params
        self.maxClimbRate = shotmgr.getParam( "PILOT_VELZ_MAX", DEFAULT_PILOT_VELZ_MAX_VALUE ) / 100.0 * ZVEL_FACTOR
        self.maxAlt = self.shotmgr.getParam( "FENCE_ALT_MAX", DEFAULT_FENCE_ALT_MAX )
        logger.log("[follow]: Maximum altitude stored: %f" % self.maxAlt)

        # check APM params to see if Altitude Limit should apply
        if self.shotmgr.getParam( "FENCE_ENABLE", DEFAULT_FENCE_ENABLE ) == 0:
            self.maxAlt = None
            logger.log("[Follow Me]: Altitude Limit disabled.")


        # the open loop altitude of the follow controllers, relative to the ROI
        self.followControllerAltOffset = 0
        
        # used to adjust frame of ROI vertically (Just affects camera pointing, not copter position)
        self.ROIAltitudeOffset = 0
        
        
        ''' Communications '''
        # configure follow socket
        self.setupSocket()

        # take away user control of vehicle
        self.vehicle.mode = VehicleMode("GUIDED")
        self.shotmgr.rcMgr.enableRemapping( True )


    # channels are expected to be floating point values in the (-1.0, 1.0) range
    def handleRCs( self, channels ):

        # check socket for a new ROI from the app
        self.checkSocket()

        # if we have never received an ROI
        if not self.rawROI:
            return

        # smooth ROI and calculate translateVel for follow
        self.filterROI()

        # if we are not warmed up, dont do anything
        if self.followState == FOLLOW_WAIT:
            return
        
        '''
        Position Control
        Note: All follow controllers return position and velocity of the
        drone in "absolute" space (as opposed to relative to the ROI)
            Pos: Lat, lon, alt. Alt is relative to home location. NEU frame..
            Vel: Speed in the x,y, and z directions. NEU frame. vel.z needs
                 to be inverted before passing to the autopilot.
        '''
        
        # Look At Me Mode (Vehicle stays put)
        if self.followState == FOLLOW_LOOKAT:
            pos, vel = self.pathController.move(channels)            
            
        # Free Look Follow Mode (Vehicle controls are similar to FLY)
        elif self.followState == FOLLOW_FREELOOK:
            pos, vel = self.pathController.move(channels, newHeading = self.camYaw, newOrigin = self.filteredROI, roiVel = self.translateVel)
            
        # Follow Me Mode (Vehicle controls are similar to ORBIT)
        elif self.followState == FOLLOW_ORBIT:
            pos, vel = self.pathController.move(channels, cruiseSpeed = self.pathHandler.cruiseSpeed, newroi = self.filteredROI, roiVel = self.translateVel)
            
        elif self.followState == FOLLOW_LEASH:
            pos, vel = self.pathController.move(channels, newroi = self.filteredROI, roiVel = self.translateVel)


        # learn any changes to controller alt offset to apply it to other controllers when instantiated (to avoid jerks)
        self.followControllerAltOffset = pos.alt - self.filteredROI.alt

        # mavlink expects 10^7 integer for accuracy
        latInt = int(pos.lat * 10000000)
        lonInt = int(pos.lon * 10000000)

        # Convert from NEU to NED to send to autopilot
        vel.z *= -1

        # create the SET_POSITION_TARGET_GLOBAL_INT command
        msg = self.vehicle.message_factory.set_position_target_global_int_encode(
             0,       # time_boot_ms (not used)
             0, 1,    # target system, target component
             mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, # frame
             0b0000110111000000, # Pos Vel type_mask
             latInt, lonInt, pos.alt, # x, y, z positions
             vel.x, vel.y, vel.z, # x, y, z velocity in m/s
             0, 0, 0, # x, y, z acceleration (not used)
             0, 0)    # yaw, yaw_rate (not used)

        # send command to vehicle
        self.vehicle.send_mavlink(msg)


        ''' Pointing Control'''

        # If followState mandates that the user controls the pointing
        if self.followState == FOLLOW_FREELOOK:
            self.manualPitch(channels[THROTTLE])
            self.manualYaw(channels)            
            self.handleFreeLookPointing()

        # If followState mandates that the copter should point at the ROI
        else:
            # Adjust the height of the ROI using the paddle
            # we pass in both the filtered gimbal paddle value as well as the raw one
            self.updateROIAltOffset(channels[RAW_PADDLE])
            # we make a copy of the ROI to allow us to add in an altitude offset
            # this means the ROI doesn't get polluted with the alt nudging
            tempROI = LocationGlobalRelative(self.filteredROI.lat, self.filteredROI.lon, self.filteredROI.alt)
            self.handleLookAtPointing(tempROI)


    # moves an offset of the ROI altitude up or down
    def updateROIAltOffset(self, rawPaddleValue):
        # no gimbal, no reason to change ROI
        if self.vehicle.mount_status[0] == None:
            return

        if abs(rawPaddleValue) > FOLLOW_ALT_PADDLE_DEADZONE:
            self.ROIAltitudeOffset += (rawPaddleValue * FOLLOW_ALT_NUDGE_SPEED * UPDATE_TIME)

    # if we can handle the button we do
    def handleButton(self, button, event):
        
        if button == btn_msg.ButtonA and event == btn_msg.ClickRelease:

            # Allow the user to exit Look At Me mode (into the previous follow mode) with the A button
            if self.followPreference == FOLLOW_PREF_LEASH:
                self.initState(FOLLOW_LEASH)
            elif self.followPreference == FOLLOW_PREF_FREELOOK:
                self.initState(FOLLOW_FREELOOK)
            else:
                self.initState(FOLLOW_ORBIT)

        # Change Follow Mode to Look At Me on Pause button press
        if button == btn_msg.ButtonLoiter and event == btn_msg.ClickRelease:
            self.initState(FOLLOW_LOOKAT)
            self.shotmgr.notifyPause(True)
            self.updateAppOptions()
                    
        self.setButtonMappings()


    def setButtonMappings(self):
        buttonMgr = self.shotmgr.buttonManager

        # Allow the user to exit Look At Me mode (into the previous follow mode) with the A button
        if self.followState == FOLLOW_LOOKAT:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_FOLLOW, btn_msg.ARTOO_BITMASK_ENABLED, "Resume\0")            
        else:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_FOLLOW, 0, "\0")
        
        
        buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_FOLLOW, 0, "\0")

    

    # pass in the value portion of the SOLO_FOLLOW_OPTIONS packet
    def handleOptions(self, options, version):
        if version == 1:
            logger.log("[Follow Me]: Received Follow Me Options v1 packet.")
            (cruiseSpeed, _lookat) = struct.unpack('<fi', options)

        elif version == 2:
            logger.log("[Follow Me]: Received Follow Me Options v2 packet.")
            (cruiseSpeed, _lookat, self.followPreference) = struct.unpack('<fii', options)
        else:
            logger.log("[follow]: Unknown packet version requested.")
            return
            
        logger.log( "[Follow Me]: -->Cruise speed: %f" % cruiseSpeed)
        logger.log( "[Follow Me]: -->Look At: %i" % _lookat)
        logger.log( "[Follow Me]: -->Follow Pref: %i" % self.followPreference)

        self.pathHandler.setCruiseSpeed(cruiseSpeed)
        
        # if user presses cruise arrows, force user into Orbit mode
        if cruiseSpeed != 0:
            # if we press cruise, force user into Orbit mode
            # only work on state changes
            # force follow Pref into Orbit
            self.followPreference = FOLLOW_PREF_HOLD_ANGLE
            newState = FOLLOW_ORBIT
                    
        elif _lookat == 1:
            # Lookat overrides the follow preferences
            newState = FOLLOW_LOOKAT
        else:
            # we may be exiting lookat into Orbit, Freelook or Leash
            if self.followPreference == FOLLOW_PREF_FREELOOK:
                newState = FOLLOW_FREELOOK
            elif self.followPreference == FOLLOW_PREF_LEASH:
                newState = FOLLOW_LEASH
            else:            
                # enter default state
                newState = FOLLOW_ORBIT
        
        self.initState(newState)


    def initState(self, newState):
        '''Manages state changes'''        
        # Don't change state until we've received at least one ROI from phone
        # Don't re-init previous state
        if not self.rawROI or self.followState == newState:
            return
        
        self.followState = newState
        
        if self.followState == FOLLOW_LOOKAT:
            logger.log("[Follow Me]: enter Lookat")
            self.initLookAtMeController()
        
        elif self.followState == FOLLOW_ORBIT:
            logger.log("[Follow Me]: enter Orbit")
            self.initOrbitController()
        
        elif self.followState == FOLLOW_LEASH:
            logger.log("[Follow Me]: enter Leash")
            self.initLeashController()

        elif self.followState == FOLLOW_FREELOOK:
            logger.log("[Follow Me]: enter Freelook")
            self.initFreeLookController()

        self.updateMountStatus()

        # update UI
        self.updateAppOptions()
        self.setButtonMappings()

                
    # send our current set of options to the app
    def updateAppOptions(self):        
        
        _lookAtMe = self.followState == FOLLOW_LOOKAT

        packetV1 = struct.pack('<IIfi', app_packet.SOLO_FOLLOW_OPTIONS, 8, self.pathHandler.cruiseSpeed, _lookAtMe)
        self.shotmgr.appMgr.sendPacket(packetV1)
        
        packetV2 = struct.pack('<IIfii', app_packet.SOLO_FOLLOW_OPTIONS_V2, 12, self.pathHandler.cruiseSpeed, _lookAtMe, self.followPreference)
        self.shotmgr.appMgr.sendPacket(packetV2)

    def setupSocket(self):
        '''Sets up the socket for GPS data from app'''

        # Follow me creates a socket to get new ROIs
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setblocking(0)
        try:
            self.socket.bind(("", FOLLOW_PORT))
        except Exception as e:
            logger.log("[follow]: failed to bind follow socket - %s"%(type(e)))

        self.socket.settimeout(SOCKET_TIMEOUT)


    def checkSocket(self):
        '''check our socket to see if a new follow roi is there'''

        packetsConsumed = 0
        #consume from socket until it's empty
        while True:
            try:
                data, addr = self.socket.recvfrom(28)
            except socket.timeout:
                break
            else:
                newestData = data
                packetsConsumed += 1

        # make sure we have a packet to work with
        if packetsConsumed > 0:
            (id, length, lat, lon, alt) = struct.unpack('<IIddf', newestData)
            if id == app_packet.SOLO_MESSAGE_LOCATION:
                now = monotonic.monotonic()
                if self.rawROI is None:
                    self.roiDeltaTime = None
                else:
                    self.roiDeltaTime = now - self.previousROItime
                self.previousROItime = now
                self.rawROI = LocationGlobalRelative(lat,lon,alt)
            else:
                logger.log("[follow]: got an invalid packet from follow socket")
        else:
            pass # will implement 2 second timeout to kill shot here

    def filterROI(self):
        '''Filters app ROI using a 5th order linear filter and calculates an associated roi velocity'''
        
        # store last 5 raw roi values
        self.rawROIQueue.append(self.rawROI)

        # only run filter if we have enough data in the queues.
        if len(self.rawROIQueue) == MIN_RAW_ROI_QUEUE_LENGTH and len(self.filteredROIQueue) == MIN_FILT_ROI_QUEUE_LENGTH:
            num = [0,0.000334672774973874,0.00111965413719632,-0.000469533537393159,-0.000199779184127412]
            den = [1,-3.48113699710809,4.56705782792063,-2.67504447769757,0.589908661075676]

            filteredLat = ( (num[4]*self.rawROIQueue[0].lat + num[3]*self.rawROIQueue[1].lat + num[2]*self.rawROIQueue[2].lat + num[1]*self.rawROIQueue[3].lat + num[0]*self.rawROIQueue[4].lat) - (den[4]*self.filteredROIQueue[0].lat + den[3]*self.filteredROIQueue[1].lat + den[2]*self.filteredROIQueue[2].lat + den[1]*self.filteredROIQueue[3].lat) ) / den[0]
            filteredLon = ( (num[4]*self.rawROIQueue[0].lon + num[3]*self.rawROIQueue[1].lon + num[2]*self.rawROIQueue[2].lon + num[1]*self.rawROIQueue[3].lon + num[0]*self.rawROIQueue[4].lon) - (den[4]*self.filteredROIQueue[0].lon + den[3]*self.filteredROIQueue[1].lon + den[2]*self.filteredROIQueue[2].lon + den[1]*self.filteredROIQueue[3].lon) ) / den[0]
            filteredAlt = ROI_ALT_FILTER_GAIN * self.filteredROIQueue[-1].alt + (1-ROI_ALT_FILTER_GAIN) * self.rawROI.alt# index -1 should refer to most recent value in the queue.
            self.filteredROI = LocationGlobalRelative(filteredLat,filteredLon,filteredAlt)
        else:
            self.filteredROI = self.rawROI
            

        # store last 4 filtered roi values
        self.filteredROIQueue.append(self.filteredROI)

        # only called once - when we have an ROI from phone
        if len(self.filteredROIQueue) == 1:
            # initialize ROI velocity for Guided controller
            self.roiVelocity = Vector3(0,0,0)
            
            # initialize the altitude maintained for each controller
            # the first ROI sent from the app is supposed to have 0 altitude, but in case it doesn't subtract it out.
            self.followControllerAltOffset = self.vehicle.location.global_relative_frame.alt - self.rawROI.alt
            logger.log('[Follow Me]: First ROI received from app has altitude: %f m' %self.rawROI.alt)

                    
            # go into Look At Me as default state. iOS app changes state to Orbit after 3 seconds.
            self.initState(FOLLOW_LOOKAT)

        elif len(self.filteredROIQueue) > 1 and self.roiDeltaTime:
            #calculate vector from previous to new roi in North,East,Up
            vec = location_helpers.getVectorFromPoints(self.filteredROIQueue[-2] , self.filteredROIQueue[-1])

            # calculate velocity based on time difference
            # roiVelocity in NEU frame
            self.roiVelocity = vec/self.roiDeltaTime

            # calculate desiredYaw and desiredPitch from new ROI
            self.desiredYaw, self.desiredPitch = location_helpers.calcYawPitchFromLocations(self.vehicle.location.global_relative_frame, self.filteredROI)


        #x component accel limit
        if self.roiVelocity.x > self.translateVel.x:
            self.translateVel.x += ACCEL_PER_TICK
            self.translateVel.x = min(self.translateVel.x, self.roiVelocity.x)
        elif self.roiVelocity.x < self.translateVel.x:
            self.translateVel.x -= ACCEL_PER_TICK
            self.translateVel.x = max(self.translateVel.x, self.roiVelocity.x)

        #y component accel limit
        if self.roiVelocity.y > self.translateVel.y:
            self.translateVel.y += ACCEL_PER_TICK
            self.translateVel.y = min(self.translateVel.y, self.roiVelocity.y)
        elif self.roiVelocity.y < self.translateVel.y:
            self.translateVel.y -= ACCEL_PER_TICK
            self.translateVel.y = max(self.translateVel.y, self.roiVelocity.y)

        #z component accel limit
        if self.roiVelocity.z > self.translateVel.z:
            self.translateVel.z += ACCEL_PER_TICK
            self.translateVel.z = min(self.translateVel.z, self.roiVelocity.z)
        elif self.roiVelocity.z < self.translateVel.z:
            self.translateVel.z -= ACCEL_PER_TICK
            self.translateVel.z = max(self.translateVel.z, self.roiVelocity.z)
    

    def initOrbitController(self):
        '''Resets the controller'''
        
        # reset Orbit
        resetRadius = location_helpers.getDistanceFromPoints(self.filteredROI, self.vehicle.location.global_relative_frame)
        resetAz     = location_helpers.calcAzimuthFromPoints(self.filteredROI, self.vehicle.location.global_relative_frame)
        
        # Initialize the feed-forward orbit controller
        self.pathController = OrbitController(self.filteredROI, resetRadius, resetAz, self.followControllerAltOffset)
        
        # set controller options
        self.pathController.setOptions(maxClimbRate = self.maxClimbRate, maxAlt = self.maxAlt)

    def initLeashController(self):
        '''Resets the controller'''
        # reset leash
        resetRadius = location_helpers.getDistanceFromPoints(self.filteredROI, self.vehicle.location.global_relative_frame)
        resetAz     = location_helpers.calcAzimuthFromPoints(self.filteredROI, self.vehicle.location.global_relative_frame)
        
        # Initialize the feed-forward orbit controller
        self.pathController = LeashController(self.filteredROI, resetRadius, resetAz, self.followControllerAltOffset)
        
        # set controller options

        self.pathController.setOptions(maxClimbRate = self.maxClimbRate, maxAlt = self.maxAlt)


    def initFreeLookController(self):
        '''Enter/exit free look'''
        
        vectorOffset = location_helpers.getVectorFromPoints(self.filteredROI, self.vehicle.location.global_relative_frame)
        xOffset = vectorOffset.x
        yOffset = vectorOffset.y
        zOffset = self.followControllerAltOffset
        
        heading = camera.getYaw(self.vehicle)
 
        # Initialize the feed-forward orbit controller
        self.pathController = FlyController(self.filteredROI, xOffset, yOffset, zOffset, heading)

        # set controller options
        self.pathController.setOptions(maxClimbRate = self.maxClimbRate, maxAlt = self.maxAlt)
        
        # default camPitch and Yaw from vehicle
        self.camPitch = camera.getPitch(self.vehicle)
        self.camYaw = camera.getYaw(self.vehicle)

        # only used for non-gimbaled copters
        self.camDir = 1

    def initLookAtMeController(self):
        '''Enter lookat mode'''
        # zero out any cruise speed
        self.pathHandler.pause()

        # Initialize the feed-forward orbit controller. Look at me is unique in that we pass total altitude, not just the offset
        self.pathController = LookAtController(self.vehicle, self.followControllerAltOffset + self.filteredROI.alt)
        
        # set controller options
        self.pathController.setOptions(maxClimbRate = self.maxClimbRate, maxAlt = self.maxAlt)

    def updateMountStatus(self):
        if self.followState == FOLLOW_FREELOOK:
            msg = self.vehicle.message_factory.mount_configure_encode(
                    0, 1,    # target system, target component
                    mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,  #mount_mode
                    1,  # stabilize roll
                    1,  # stabilize pitch
                    1,  # stabilize yaw
                    )
        else:
            # set gimbal targeting mode
            msg = self.vehicle.message_factory.mount_configure_encode(
                        0, 1,    # target system, target component
                        mavutil.mavlink.MAV_MOUNT_MODE_GPS_POINT,  #mount_mode
                        1,  # stabilize roll
                        1,  # stabilize pitch
                        1,  # stabilize yaw
                        )
        self.vehicle.send_mavlink(msg)


    def manualPitch(self, stick):          
        self.camPitch += stick * FOLLOW_PITCH_SPEED * UPDATE_TIME
        
        if self.camPitch > 0.0:
            self.camPitch = 0.0
        elif self.camPitch < -90:
            self.camPitch = -90
 
 
    def manualYaw(self, channels):
        if channels[YAW] == 0:
            return
        self.camYaw += channels[YAW] * FOLLOW_YAW_SPEED * UPDATE_TIME
        if channels[YAW] > 0:
            self.camDir = 1
        else:
            self.camDir = -1
        
        self.camYaw = location_helpers.wrapTo360(self.camYaw)

    def handleFreeLookPointing(self):
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


    def handleLookAtPointing(self, tempROI):
        # set ROI
        msg = self.vehicle.message_factory.command_int_encode(
                0, 1,    # target system, target component
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, #frame
                mavutil.mavlink.MAV_CMD_DO_SET_ROI, #command
                0, #current
                0, #autocontinue
                0, 0, 0, 0, #params 1-4
                tempROI.lat*1.E7,
                tempROI.lon*1.E7,
                tempROI.alt + self.ROIAltitudeOffset #offset for ROI
        )

        # send pointing message
        self.vehicle.send_mavlink(msg)

    def handlePacket(self, packetType, packetLength, packetValue):
        try:
            if packetType == app_packet.SOLO_FOLLOW_OPTIONS:
                logger.log("[follow]: Received Follow Me Options v1 packet.")
                self.handleOptions(packetValue, version=1)

            elif packetType == app_packet.SOLO_FOLLOW_OPTIONS_V2:
                logger.log("[follow]: Received Follow Me Options v2 packet.")
                self.handleOptions(packetValue, version=2)
            
            else:
                return False
        except Exception as e:
            logger.log('[follow]: Error handling packet. (%s)' % e)
            return False
        else:
            return True

