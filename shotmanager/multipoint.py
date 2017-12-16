#  multipoint.py
#  shotmanager
#
#  The multipoint cable cam smart shot controller.
#  Runs as a DroneKit-Python script.
#
#  Created by Will Silva on 11/22/2015.
#  Copyright (c) 2016 3D Robotics.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from dronekit import Vehicle, LocationGlobalRelative, VehicleMode
from pymavlink import mavutil
import math
import struct
import app_packet
import camera
import location_helpers
import shotLogger
from shotManagerConstants import *
import shots
import yawPitchOffsetter
from catmullRom import CatmullRom
from vector3 import Vector3
from vector2 import Vector2
from sololink import btn_msg
import cableController
from cableController import CableController
import monotonic

# initiate logger
logger = shotLogger.logger

# CONSTANTS

ACCEL_LIMIT = 2.0 #m/s^2
NORM_ACCEL_LIMIT = 1.75 #m/s^2
TANGENT_ACCEL_LIMIT = math.sqrt(ACCEL_LIMIT**2-NORM_ACCEL_LIMIT**2) #m/s^2

# Yaw rate (deg/s)
YAW_SPEED = 100.0

# Minimum cruise speed that can be set by the app
MIN_CRUISE_SPEED = 0.1 #m/s

# change in speed required to send the app a notification of speed/location for
# visualization purposes
SPEED_CHANGE_NOTIFICATION_THRESHOLD = 0.5 #m/s

# speed at which vehicle attaches to cable
ATTACH_SPEED = 2 #m/s

# yaw speed at which vehicle transitions to cable
ATTACH_YAW_SPEED = 80 #deg/s

# cm / s from APM
DEFAULT_WPNAV_SPEED_VALUE = 1100.0 # cm/s

# Number of times we notify the app of our playback status
NOTIFICATIONS_PER_SECOND = 10

# Maximum time, in seconds, that any cable can take
MAXIMUM_CABLE_DURATION = 20*60.

# constants for cruiseState
RIGHT = 1
PAUSED = 0
LEFT = -1


class Waypoint():

    def __init__(self, loc, pitch, yaw):
        self.loc = loc
        self.yaw = yaw
        self.pitch = pitch
        if self.pitch is None:
            self.pitch = 0.0


class MultipointShot():

    def __init__(self, vehicle, shotmgr):
        # assign vehicle object
        self.vehicle = vehicle

        # assign shotmanager object
        self.shotmgr = shotmgr

        # initialize YawPitchOffsetter object
        self.yawPitchOffsetter = yawPitchOffsetter.YawPitchOffsetter()

        # enable yaw nudge by default
        self.yawPitchOffsetter.enableNudge()

        # initializes/resets most member vars
        self.resetShot()

        # get current altitude limit
        self.maxAlt = self.shotmgr.getParam( "FENCE_ALT_MAX", DEFAULT_FENCE_ALT_MAX ) # in meters
        logger.log("[Multipoint]: Maximum altitude stored: %f" % self.maxAlt)

        # check APM params to see if Altitude Limit should apply
        if self.shotmgr.getParam( "FENCE_ENABLE", DEFAULT_FENCE_ENABLE ) == 0:
            self.maxAlt = None
            logger.log("[Multipoint]: Altitude Limit disabled.")


    def resetShot(self):
        '''initializes/resets most member vars'''

        # camInterpolation == 1: free look
        # camInterpolation == 0: tween pitch/yaw between keyframes
        self.camInterpolation = 0

        # True - Play mode, False - Record mode
        self.cableCamPlaying = False

        # initialize waypoints list
        self.waypoints = []

        # stores list of which direction to yaw while on the cable
        self.yawDirections = []

        # desired speed set by sticks or cruise speed
        self.desiredSpeed = 0.0

        # active cruise speed being used by controller
        self.cruiseSpeed = 0

        # stored cruise speed set from app
        self.storedCruiseSpeed = 0

        # current state of cruise (-1 = moving left, 0 = paused, 1 = moving right)
        self.cruiseState = PAUSED

        # declare camera spline object
        self.camSpline = None

        # initialize commanded velocity
        self.commandVel = None

        # initialize commanded position
        self.commandPos = None

        # flag that indicates whether we are in the attaching state
        self.attaching = True

        # last speed that was reported to the app for visualization purposes
        self.lastNotifiedSpeed = 0.0

        # last segment that was reported to the app for visualization purposes
        self.lastNotifiedSegment = None

        # Index to attach on spline during a cable load
        self.attachIndex = -1

        # ticks to track when to notify app with playback status update
        self.ticksSinceNotify = 0

        # default targetP
        self.targetP = 0.0

        # initialize cable to None
        self.cable = None        

        # solo spline point version
        self.splinePointVersion = 0

        # absolute altitude reference
        self.absAltRef = None

        # initialize min/max times
        self.maxTime = None
        self.minTime = None

        # last time that the controller was advanced
        self.lastTime = None

    def handleRCs(self, channels):
        '''Handles RC inputs and runs the high level shot controller'''
        # channels are expected to be floating point values
        # in the (-1.0, 1.0) range don't enter the guided shot
        # mode until the user has recorded the cable endpoints

        # block controller from running until we enter play mode
        if not self.cableCamPlaying:
            return

        # if we are still attaching to the spline
        if self.attaching:
            self.listenForAttach()
            return

        # determine if we should send a PLAYBACK_STATUS update to app
        self.checkToNotifyApp()

        # select the larger of the two stick values (between pitch and roll)
        if abs(channels[ROLL]) > abs(channels[PITCH]):
            value = channels[ROLL]
        else:
            value = -channels[PITCH]

        # Check if we're in a cruise mode or not
        if self.cruiseSpeed == 0:
            # scale max speed by stick value
            self.desiredSpeed = value * MAX_SPEED
        else:
            speed = abs(self.cruiseSpeed)
            # if sign of stick and cruiseSpeed don't match then...
            # slow down
            if math.copysign(1, value) != math.copysign(1, self.cruiseSpeed):
                speed *= (1.0 - abs(value))
            else:  # speed up
                speed += (MAX_SPEED - speed) * abs(value)

            # speedlimit
            if speed > MAX_SPEED:
                speed = MAX_SPEED

            # carryover user input sign
            if self.cruiseSpeed < 0:
                speed = -speed

            # assign to desired velocity
            self.desiredSpeed = speed

        if self.desiredSpeed > 0:
            self.targetP = 1.0
        elif self.desiredSpeed < 0:
            self.targetP = 0.0

        self.cable.setTargetP(self.targetP)

        # give cable controller our desired speed
        self.cable.trackSpeed(abs(self.desiredSpeed))

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

        if self.camInterpolation == 0:
            # calculate interpolated pitch & yaw
            newPitch, newYaw = self.interpolateCamera()
        else:
            # free look pitch and yaw
            newPitch, newYaw = (0.0, 0.0)

        # calculate nudge offset or free-look offset
        self.yawPitchOffsetter.Update(channels)

        # add offsets
        newPitch += self.yawPitchOffsetter.pitchOffset
        newYaw += self.yawPitchOffsetter.yawOffset

        # Formulate mavlink message for mount controller. Use mount_control if using a gimbal. Use just condition_yaw if no gimbal.        
        # Modified by Matt 2017-05-18 for ArducCopter master compatibility
        
        # mav_cmd_do_mount_control should handle gimbal pitch and copter yaw, but yaw is not working in master. 
        # So this mount_control command is only going to do the gimbal pitch for now.
        if self.vehicle.mount_status[0] is not None:
            pointingMsg = self.vehicle.message_factory.mount_control_encode(
                0, 1,    # target system, target component
                newPitch * 100,  # pitch (centidegrees)
                0.0,  # roll (centidegrees)
                newYaw * 100,  # yaw (centidegrees)
                0  # save position
            )
            self.vehicle.send_mavlink(pointingMsg)
            
            # Temporary fix while the yaw control is not working in the above mount_control command.
            pointingMsg = self.vehicle.message_factory.command_long_encode(
                0, 0,    # target system, target component
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,  # command
                0,  # confirmation
                newYaw,  # param 1 - target angle (degrees)
                YAW_SPEED,  # param 2 - yaw speed (deg/s)
                0,  # param 3 - direction, always shortest route for now...
                0.0,  # relative offset
                0, 0, 0  # params 5-7 (unused)
            )
            self.vehicle.send_mavlink(pointingMsg)

            
        # if no gimbal, assume fixed mount and use condition_yaw only
        else:
            # if we don't have a gimbal, just set CONDITION_YAW
            pointingMsg = self.vehicle.message_factory.command_long_encode(
                0, 0,    # target system, target component
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,  # command
                0,  # confirmation
                newYaw,  # param 1 - target angle (degrees)
                YAW_SPEED,  # param 2 - yaw speed (deg/s)
                0,  # param 3 - direction, always shortest route for now...
                0.0,  # relative offset
                0, 0, 0  # params 5-7 (unused)
            )
            self.vehicle.send_mavlink(pointingMsg)
        

    def interpolateCamera(self):
        '''Interpolate (linear) pitch and yaw between cable control points'''

        perc = self.cable.currentU

        # sanitize perc
        if perc < 0.0:
            perc = 0.0
        elif perc > 1.0:
            perc = 1.0

        # get pitch and yaw from spline (x is pitch, y is yaw)
        pitchYaw = self.camSpline.position(self.cable.currentSeg,perc)

        return pitchYaw.x, location_helpers.wrapTo360(pitchYaw.y)

    def recordLocation(self):
        '''record a cable control point'''

        # don't run this function if we're already in the cable
        if self.cableCamPlaying:
            logger.log("[multipoint]: Cannot record a location when in PLAY mode.")
            return

        # record HOME absolute altitude reference if this is the first waypoint
        if len(self.waypoints) == 0:
            self.absAltRef = self.vehicle.location.global_frame.alt - self.vehicle.location.global_relative_frame.alt
            logger.log("[multipoint]: HOME absolute altitude recorded: %f meters" % self.absAltRef)

        # capture current pitch and yaw state
        pitch = camera.getPitch(self.vehicle)
        degreesYaw = location_helpers.wrapTo360(camera.getYaw(self.vehicle))

        # check if last recorded point is a duplicate with this new one
        if self.duplicateCheck(self.vehicle.location.global_relative_frame, len(self.waypoints)):
            logger.log("[multipoint]: Overwriting last point.")
            # overwrite last point
            self.waypoints[-1].loc = self.vehicle.location.global_relative_frame
            self.waypoints[-1].pitch = pitch
            self.waypoints[-1].yaw = degreesYaw
        else:
            # append a new point
            self.waypoints.append(
                Waypoint(self.vehicle.location.global_relative_frame, pitch, degreesYaw))

        # log this point
        logger.log("[multipoint]: Successfully recorded waypoint #%d. Lat: %f, Lon: %f, Alt: %f, Pitch: %f, Yaw: %f" %
                   (len(self.waypoints)-1, self.vehicle.location.global_relative_frame.lat, self.vehicle.location.global_relative_frame.lon, self.vehicle.location.global_relative_frame.alt, pitch, degreesYaw))

        # send the spline point to the app
        self.sendSoloSplinePoint(self.splinePointVersion, self.absAltRef, len(self.waypoints) - 1, self.vehicle.location.global_relative_frame.lat, self.vehicle.location.global_relative_frame.lon, self.vehicle.location.global_relative_frame.alt, pitch, degreesYaw, 0, app_packet.SPLINE_ERROR_NONE)
        logger.log("[multipoint]: Sent spline point #%d to app." % (len(self.waypoints)-1))

        # update button mappings
        self.setButtonMappings()

    def loadSplinePoint(self, point):
        '''load a cable control point'''
        (version, absAltRef, index, lat, lon, alt, pitch, yaw, uPosition, app_packet.SPLINE_ERROR_MODE) = point
        if self.cableCamPlaying:
            logger.log("[multipoint]: Shot in PLAY mode, cannot load waypoint.")
            self.sendSoloSplinePoint(version, absAltRef, index, lat, lon, alt, pitch, yaw, uPosition, app_packet.SPLINE_ERROR_MODE)
            logger.log("[multipoint]: Sent failed spline point #%d to app." % index)
            return

        if version == 0:
            if self.cableCamPlaying:
                logger.log("[multipoint]: Shot in PLAY mode, cannot load waypoint.")
                self.sendSoloSplinePoint(version, absAltRef, index, lat, lon, alt, pitch, yaw, uPosition, app_packet.SPLINE_ERROR_MODE)
                logger.log("[multipoint]: Sent failed spline point #%d to app." % index)
                return

            if self.duplicateCheck(LocationGlobalRelative(lat, lon, alt), index):
                logger.log("[multipoint]: Duplicate detected, rejecting waypoint #%d." % index)
                self.sendSoloSplinePoint(version, absAltRef, index, lat, lon, alt, pitch, yaw, uPosition, app_packet.SPLINE_ERROR_DUPLICATE)
                logger.log("[multipoint]: Sent failed spline point #%d to app." % index)
                return

            # if this is the first loaded waypoint, store absolute altitude reference and version
            if len(self.waypoints) == 0:
                self.splinePointVersion = version
                self.absAltRef = absAltRef
                logger.log("[multipoint]: previous HOME absolute altitude loaded: %f meters" % self.absAltRef)
        else:
            logger.log("[multipoint]: Spline point version (%d) not supported, cannot load waypoint." % version)
            return

        # if loaded waypoint index is higher than current waypoint list size
        # then extend waypoint list to accomodate
        if (index + 1) > len(self.waypoints):
            self.waypoints.extend([None] * (index + 1 - len(self.waypoints)))

        # store received waypoint
        self.waypoints[index] = Waypoint(LocationGlobalRelative(lat, lon, alt), pitch, yaw)

        # log waypoint
        logger.log("[multipoint]: Successfully loaded waypoint #%d. Lat: %f, Lon: %f, Alt: %f, Pitch: %f, Yaw: %f" % (
            index, lat, lon, alt, pitch, yaw))

        # send the spline point to the app
        self.sendSoloSplinePoint(self.splinePointVersion, self.absAltRef, index, lat, lon, alt, pitch, yaw, uPosition, app_packet.SPLINE_ERROR_NONE)
        logger.log("[multipoint]: Sent spline point #%d to app." % index)

        # update button mappings
        self.setButtonMappings()

    def sendSoloSplinePoint(self, version, absAltReference, index, lat, lon, alt, pitch, yaw, uPosition, status):
        if version == 0:
            packet = struct.pack('<IIhfIddffffh', app_packet.SOLO_SPLINE_POINT, 44,
                                 version, absAltReference, index, lat, lon, alt, pitch, yaw, uPosition, status)
            self.shotmgr.appMgr.sendPacket(packet)

    def duplicateCheck(self, loc, desiredIndex):
        '''Checks for duplicate waypoints
        loc - desired waypoint location
        desiredIndex - index that we would like to add the waypoint to in self.waypoints
        '''
        isDuplicate = False

        # check point on the right
        if desiredIndex < len(self.waypoints)-1:
            if self.waypoints[desiredIndex+1] is not None:
                if location_helpers.getDistanceFromPoints3d(self.waypoints[desiredIndex+1].loc, loc) < WAYPOINT_NEARNESS_THRESHOLD:
                    logger.log("[multipoint]: Duplicate waypoint detected. Conflicts with index %d." % (desiredIndex + 1))
                    isDuplicate = True

        # check point on the left
        if 0 < desiredIndex <= len(self.waypoints):
            if self.waypoints[desiredIndex-1] is not None:
                if location_helpers.getDistanceFromPoints3d(self.waypoints[desiredIndex-1].loc, loc) < WAYPOINT_NEARNESS_THRESHOLD:
                    logger.log("[multipoint]: Duplicate waypoint detected. Conflicts with index %d." % (desiredIndex - 1))
                    isDuplicate = True

        return isDuplicate

    def setButtonMappings(self):
        buttonMgr = self.shotmgr.buttonManager

        if len(self.waypoints) == 0:
            buttonMgr.setArtooButton(
                btn_msg.ButtonA, shots.APP_SHOT_MULTIPOINT, btn_msg.ARTOO_BITMASK_ENABLED, "Record Point\0")
            buttonMgr.setArtooButton(
                btn_msg.ButtonB, shots.APP_SHOT_MULTIPOINT, 0, "\0")
        elif not self.cableCamPlaying:
            buttonMgr.setArtooButton(
                btn_msg.ButtonA, shots.APP_SHOT_MULTIPOINT, btn_msg.ARTOO_BITMASK_ENABLED, "Record Point\0")
            buttonMgr.setArtooButton(
                btn_msg.ButtonB, shots.APP_SHOT_MULTIPOINT, btn_msg.ARTOO_BITMASK_ENABLED, "Finish Point\0")
        else:
            buttonMgr.setArtooButton(
                btn_msg.ButtonA, shots.APP_SHOT_MULTIPOINT, 0, "\0")
            buttonMgr.setArtooButton(
                btn_msg.ButtonB, shots.APP_SHOT_MULTIPOINT, 0, "\0")

    def handleButton(self, button, event):
        '''handle actions for button presses'''
        if not self.cableCamPlaying:
            if button == btn_msg.ButtonA and event == btn_msg.ClickRelease:
                self.recordLocation()
            if button == btn_msg.ButtonB and event == btn_msg.ClickRelease:
                self.recordLocation()
                # only try to start a cable if we have more than 2 points
                if len(self.waypoints) > 1:
                    # initialize multiPoint cable
                    self.enterPlayMode()

        # handle pause button
        if button == btn_msg.ButtonLoiter and event == btn_msg.ClickRelease:
            self.setCruiseSpeed(state = PAUSED)
            logger.log("[multipoint]: Pause button pressed on Artoo.")

    def handlePathSettings(self, pathSettings):
        '''pass in the value portion of the SOLO_SPLINE_PATH_SETTINGS packet'''

        (cameraMode, desiredTime) = pathSettings

        # don't run this function if we're not in Play Mode
        if not self.cableCamPlaying:
            logger.log("[multipoint]: Can't set cable settings. Not in play mode.")
            return

        # change pointing modes
        if cameraMode != self.camInterpolation:
            if cameraMode == 0:
                self.yawPitchOffsetter.enableNudge()
                logger.log("[multipoint]: Entering InterpolateCam.")
                self.camInterpolation = 0
            elif cameraMode == 1:
                self.yawPitchOffsetter.disableNudge(
                    camera.getPitch(self.vehicle), camera.getYaw(self.vehicle))
                logger.log("[multipoint]: Entering FreeCam.")
                self.camInterpolation = 1
            else:
                logger.log("[multipoint]: Camera mode not recognized (%d)." % self.camInterpolation)
                self.yawPitchOffsetter.enableNudge()

        # calculate cruise speed from desiredTime
        self.setCruiseSpeed(speed = self.estimateCruiseSpeed(desiredTime))
            

    def setCruiseSpeed(self, speed=None, state=None):
        '''Uses storedCruiseSpeed and cruiseState to assign a cruiseSpeed for the controller'''

        # RIGHT == 1
        # PAUSED == 0
        # LEFT == -1

        if speed is not None and speed != self.storedCruiseSpeed:
            # limit it
            if abs(speed) > MAX_SPEED:
                speed = MAX_SPEED
            self.storedCruiseSpeed = speed
            logger.log("[multipoint]: New cruise speed stored: %f m/s." % self.storedCruiseSpeed)

        if state is not None and state != self.cruiseState:
            self.cruiseState = state
            logger.log("[multipoint]: New cruise state set: %d" % self.cruiseState)

        if self.cruiseState == RIGHT:
            self.cruiseSpeed = self.storedCruiseSpeed * math.copysign(1,self.cruiseState)
            self.cable.setTargetP(1.0)
        elif self.cruiseState == LEFT:
            self.cruiseSpeed = self.storedCruiseSpeed * math.copysign(1,self.cruiseState)
            self.cable.setTargetP(0.0)
        else:
            self.cruiseSpeed = 0

    def updatePathTimes(self):
        '''Sends min and max path times to app'''

        # don't run this function if we're not in Play Mode
        if self.cable is None:
            logger.log("[multipoint]: Can't estimate cable times. A spline hasn't been generated yet!")
            return
    
        # pack it up and send to app
        packet = struct.pack('<IIff', app_packet.SOLO_SPLINE_DURATIONS, 8, self.minTime, self.maxTime)
        self.shotmgr.appMgr.sendPacket(packet)
        logger.log("[multipoint]: Sent times to app.")

    def updatePlaybackStatus(self):
        if self.cable is None:
            logger.log("[multipoint]: A spline hasn't been generated yet!")
            return

        if self.cable.reachedTarget():
            reportP = self.targetP
            self.setCruiseSpeed(state = PAUSED)
        else:
            reportP = self.cable.currentP

        packet = struct.pack('<IIfi', app_packet.SOLO_SPLINE_PLAYBACK_STATUS, 8, reportP, self.cruiseState)
        self.shotmgr.appMgr.sendPacket(packet)

    def handleSeek(self, seek):
        (p, cruiseState) = seek
        if self.cable is None:
            logger.log("[multipoint]: A spline hasn't been generated yet!")
            return

        if self.attaching:
            logger.log("[multipoint]: Can't seek yet, Solo still attaching to cable.")
            return

        # update cruise state
        self.setCruiseSpeed(state = cruiseState)

        logger.log("[multipoint]: New SEEK packet received. p: %f, cruiseState: %d" % (p,cruiseState))

        # notify the app
        self.checkToNotifyApp(notify=True)

    def enterRecordMode(self):
        logger.log("[multipoint]: Entering RECORD mode.")

        # send record to app
        packet = struct.pack('<II', app_packet.SOLO_SPLINE_RECORD, 0)
        self.shotmgr.appMgr.sendPacket(packet)
        logger.log("[multipoint]: Sent RECORD mode to app.")

        # Change the vehicle into loiter mode
        self.vehicle.mode = VehicleMode("LOITER")

        # reset shot
        self.resetShot()

    def enterPlayMode(self):
        logger.log("[multipoint]: Entering PLAY mode.")

        if self.cableCamPlaying:
            logger.log("[multipoint]: Already in PLAY mode.")
            return

        # make sure no waypoints are empty
        if None in self.waypoints:
            logger.log("[multipoint]: Missing at least one keyframe, reverting to RECORD mode.")
            self.enterRecordMode()
            return

        # make sure we have at least 2 waypoints recorded before continuing
        if len(self.waypoints) < 2:
            logger.log("[multipoint]: Tried to begin multipoint cable with less than 2 keyframes. Reverting to RECORD mode.")
            self.enterRecordMode()
            return

        # generate position and camera splines
        if not self.generateSplines(self.waypoints):
            logger.log("[multipoint]: Spline generation failed. Reverting to RECORD mode.")
            self.enterRecordMode()
            return

        # send play to app
        packet = struct.pack('<II', app_packet.SOLO_SPLINE_PLAY, 0)
        self.shotmgr.appMgr.sendPacket(packet)
        logger.log("[multipoint]: Sent PLAY mode to app.")

        # send path min/max times to app
        self.updatePathTimes()

        # send all waypoints to app with arc length normalized parameters
        for index, pt in enumerate(self.waypoints):
            # special case: handle last point
            if index == len(self.waypoints) - 1:
                seg = index - 1
                u = 1
            else:
                seg = index
                u = 0
            # calculate p for point (segment usually at index, u = 0, v doesn't
            # matter)
            p = self.cable.spline.nonDimensionalToArclength(seg, u, 0)[0]

            # send point packet to app
            self.sendSoloSplinePoint(self.splinePointVersion, self.absAltRef, index, pt.loc.lat, pt.loc.lon, pt.loc.alt, pt.pitch, pt.yaw, p, app_packet.SPLINE_ERROR_NONE)
            logger.log("[multipoint]: Sent spline point %d of %d to app." % (index,len(self.waypoints)-1))

        # Change the vehicle into guided mode
        self.vehicle.mode = VehicleMode("GUIDED")

        # set gimbal to MAVLink targeting mode
        msg = self.vehicle.message_factory.mount_configure_encode(
            0, 1,    # target system, target component
            mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,  # mount_mode
            1,  # stabilize roll
            1,  # stabilize pitch
            1,  # stabilize yaw
        )

        # send gimbal targeting message to vehicle
        self.vehicle.send_mavlink(msg)

        # remap the sticks
        self.shotmgr.rcMgr.enableRemapping( True )

        # set state flag to true (partially unblocks controller)
        # (also needs unblock of attaching flag)
        self.cableCamPlaying = True

        # update button mappings
        self.setButtonMappings()

        # wait for app to send an attach request
        logger.log("[multipoint]: Waiting for ATTACH command from app to continue.") # wait for a SPLINE_ATTACH message to tell us where to go

    def generateSplines(self, waypoints):
        '''Generate the multi-point spline'''

        # shortest distance between each angle
        for i in range(0, len(waypoints) - 1):
            # calculate difference of yaw and next yaw
            delta = self.waypoints[i + 1].yaw - self.waypoints[i].yaw

            # don't take the long way around
            if abs(delta) > 180:
                # add 360 to all following yaws (CW)
                if delta < 0.0:
                    direction = 1
                # or remove 360 from all following yaws (CCW)
                else:
                    direction = -1

                # list tracking directions
                self.yawDirections.append(direction)

                # update all following yaws
                for j in range(i + 1, len(self.waypoints)):
                    self.waypoints[j].yaw = self.waypoints[
                        j].yaw + direction * 360

        # generate camera spline
        camPts = [Vector2(x.pitch, x.yaw) for x in self.waypoints]

        # Generate artificial end points for spline
        # extend slope of first two points to generate initial control point
        endPt1 = camPts[0] + (camPts[0] - camPts[1])
        # extend slope of last two points to generate final control point
        endPt2 = camPts[-1] + (camPts[-1] - camPts[-2])

        # append virtual control points to cartesian list
        camPts = [endPt1] + camPts + [endPt2]

        # Build spline object
        try:
            self.camSpline = CatmullRom(camPts)
        except ValueError, e:
            logger.log("%s", e)
            self.shotMgr.enterShot(shots.APP_SHOT_NONE)  # exit the shot
            return False

        # generate 3d position spline
        ctrlPtsLLA = [x.loc for x in self.waypoints]
        ctrlPtsCart = []
        # set initial control point as origin
        ctrlPtsCart.append(Vector3(0, 0, 0))
        self.splineOrigin = ctrlPtsLLA[0]
        for n in range(1, len(ctrlPtsLLA)):
            ctrlPtsCart.append(location_helpers.getVectorFromPoints(self.splineOrigin, ctrlPtsLLA[n]))
            ctrlPtsCart[-1].z *= -1. #NED

        # Build spline object
        try:
            self.cable = cableController.CableController(points = ctrlPtsCart, maxSpeed = MAX_SPEED, minSpeed = MIN_CRUISE_SPEED, tanAccelLim = TANGENT_ACCEL_LIMIT, normAccelLim = NORM_ACCEL_LIMIT, smoothStopP = 0.7, maxAlt = self.maxAlt)
        except ValueError, e:
            logger.log("%s", e)
            self.shotMgr.enterShot(shots.APP_SHOT_NONE)  # exit the shot
            return False

        # calculate min and max parametrix velocities for the spline
        self.minTime = self.estimateTime(MAX_SPEED)
        self.maxTime = min(MAXIMUM_CABLE_DURATION, self.estimateTime(MIN_CRUISE_SPEED))

        logger.log("[multipoint]: min time for cable: %f s." % (self.minTime))
        logger.log("[multipoint]: max time for cable: %f s." % (self.maxTime))

        return True

    def estimateTime(self,speed):
        '''Tries to guess a time from a given cruiseSpeed (inverse of estimateCruiseSpeed())'''

        #AKA f(s) = l/s + s/a [in seconds]

        rampUpTime = speed / TANGENT_ACCEL_LIMIT

        rampUpDistance = 0.5*TANGENT_ACCEL_LIMIT*(rampUpTime**2)

        cruiseTime = (self.cable.spline.totalArcLength - 2.*rampUpDistance) / speed

        timeToComplete = (rampUpTime + cruiseTime + rampUpTime)

        return timeToComplete

    def estimateCruiseSpeed(self,time):
        '''Tries to guess a cruiseSpeed from a desired time (inverse of estimateTime())'''

        #AKA s^2 - ast + al = 0
        # quadratic equation: A = 1, B = -at, C = al
        # (-B +/- sqrt(B^2 - 4AC)) / 2A
        # solving for f(s) = (at +/- sqrt(a^2 * t^2 - 4*1*al))/2*1
        # re-written f(s) = (1/2) * (at +/- sqrt(a^2 * t^2 - 4*a*l)) [in m/s]

        speed = 0.5 * (TANGENT_ACCEL_LIMIT * time - math.sqrt(TANGENT_ACCEL_LIMIT**2 * time**2 - 4 * TANGENT_ACCEL_LIMIT * self.cable.spline.totalArcLength))
        # speed2 = 0.5 * (TANGENT_ACCEL_LIMIT * time + math.sqrt(TANGENT_ACCEL_LIMIT**2 * time**2 - 4 * TANGENT_ACCEL_LIMIT * self.cable.spline.totalArcLength))
        
        return speed

    def handleAttach(self, attach):
        '''Requests that the vehicle attach to a cable at the given index'''
        (self.attachIndex,) = attach

        if not self.cableCamPlaying:
            logger.log("[multipoint]: Attach request not valid in RECORD mode. Will not attach.")
            return

        if self.attachIndex >= len(self.waypoints):
            logger.log("[multipoint]: Invalid keypointIndex received. Waypoint range is 0 to %d but received %d. Will not attach." % (len(self.waypoints)-1, self.attachIndex))
            self.attachIndex = -1
            return

        logger.log("[multipoint]: Attaching to spline point %d at %.1f m/s." % (self.attachIndex,ATTACH_SPEED))

        # set currentSegment and currentU for this keyframe.
        # currentU is 0 unless we're talking about the end point
        if self.attachIndex == len(self.waypoints)-1:
            attachSeg = self.attachIndex - 1
            attachU = 1.
        else:
            attachSeg = self.attachIndex
            attachU = 0.
        p = self.cable.spline.nonDimensionalToArclength(attachSeg, attachU)[0]
        self.cable.setCurrentP(p)

        self.commandPos = self.waypoints[self.attachIndex].loc

        # Go to keyframe
        self.vehicle.simple_goto(self.commandPos)

        # Set attach speed
        speedMsg = self.vehicle.message_factory.command_long_encode(
             0, 1,    # target system, target component
             mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
             0,       # confirmation
             1, ATTACH_SPEED, -1, # params 1-3
             0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)

        # send command to vehicle
        self.vehicle.send_mavlink(speedMsg)

        # yaw to appropriate heading
        startYaw = self.waypoints[self.attachIndex].yaw
        startPitch = self.waypoints[self.attachIndex].pitch

        if self.vehicle.mount_status[0] is not None:
            pointingMsg = self.vehicle.message_factory.mount_control_encode(
                0, 1,    # target system, target component
                newPitch * 100,  # pitch (centidegrees)
                0.0,  # roll (centidegrees)
                newYaw * 100,  # yaw (centidegrees)
                0  # save position
            )
            self.vehicle.send_mavlink(pointingMsg)
            
            pointingMsg = self.vehicle.message_factory.command_long_encode(
                0, 0,    # target system, target component
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,  # command
                0,  # confirmation
                startYaw,  # param 1 - target angle (degrees)
                ATTACH_YAW_SPEED,  # param 2 - yaw speed (deg/s)
                0,  # param 3 - direction, always shortest route for now...
                0.0,  # relative offset
                0, 0, 0  # params 5-7 (unused)
            )
            self.vehicle.send_mavlink(pointingMsg)
            
            # pointingMsg = self.vehicle.message_factory.mount_control_encode(
                # 0, 1,    # target system, target component
                # startPitch * 100,  # pitch (centidegrees)
                # 0.0,  # roll (centidegrees)
                # startYaw * 100,  # yaw (centidegrees)
                # 0  # save position
            # )
        # if not, assume fixed mount
        else:
            # if we don't have a gimbal, just set CONDITION_YAW
            pointingMsg = self.vehicle.message_factory.command_long_encode(
                0, 0,    # target system, target component
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,  # command
                0,  # confirmation
                startYaw,  # param 1 - target angle (degrees)
                ATTACH_YAW_SPEED,  # param 2 - yaw speed (deg/s)
                0,  # param 3 - direction, always shortest route for now...
                0.0,  # relative offset
                0, 0, 0  # params 5-7 (unused)
            )
            self.vehicle.send_mavlink(pointingMsg)

    def listenForAttach(self):
        '''Checks if vehicle attaches to cable'''

        # don't check until a valid attachIndex has been set
        if self.attachIndex == -1:
            return

        # if distance to spline point is less than threshold
        distToSpline = location_helpers.getDistanceFromPoints3d(self.vehicle.location.global_relative_frame,self.waypoints[self.attachIndex].loc)

        # check if we are in range
        if distToSpline < WAYPOINT_NEARNESS_THRESHOLD:

            # locked on
            logger.log("[multipoint]: Attached to cable at index %d." % self.attachIndex)

            # and notify the app that we've attached
            packet = struct.pack('<III', app_packet.SOLO_SPLINE_ATTACH, 4, self.attachIndex)
            self.shotmgr.appMgr.sendPacket(packet)
            logger.log("[multipoint]: Sent attach message to app for index %d." % (self.attachIndex))

            # reset attaching flag
            self.attaching = False

            # reset attachIndex
            self.attachIndex = -1

            # get APM WPNAV_SPEED parameter to reset speed
            speed = self.shotmgr.getParam( "WPNAV_SPEED", DEFAULT_WPNAV_SPEED_VALUE ) / 100.0

            # reset MAV_CMD_DO_CHANGE_SPEED
            msg = self.vehicle.message_factory.command_long_encode(
                 0, 1,    # target system, target component
                 mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                 0,       # confirmation
                 1, speed, -1, # params 1-3
                 0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)

            # send command to vehicle
            self.vehicle.send_mavlink(msg)

    def checkToNotifyApp(self, notify=False):
        '''Checks if we should notify the app of our position on spline.

        Conditions to notify app:
        -if we haven't notified the app within NOTIFICATIONS_PER_SECOND (s)
        '''

        self.ticksSinceNotify += 1

        # notify at 5Hz
        if self.ticksSinceNotify >= UPDATE_RATE/NOTIFICATIONS_PER_SECOND or notify == True:
            self.ticksSinceNotify = 0
            self.updatePlaybackStatus()

    def handlePacket(self, packetType, packetLength, packetValue):
        try:
            if packetType == app_packet.SOLO_RECORD_POSITION:
                    self.recordLocation()

            elif packetType == app_packet.SOLO_SPLINE_RECORD:
                    self.enterRecordMode()

            elif packetType == app_packet.SOLO_SPLINE_PLAY:
                    self.enterPlayMode()

            elif packetType == app_packet.SOLO_SPLINE_POINT:
                point = struct.unpack('<hfIddffffh', packetValue)
                self.loadSplinePoint(point)

            elif packetType == app_packet.SOLO_SPLINE_SEEK:
                seek = struct.unpack('<fi', packetValue)
                self.handleSeek(seek)

            elif packetType == app_packet.SOLO_SPLINE_PATH_SETTINGS:
                pathSettings = struct.unpack('<If', packetValue)
                self.handlePathSettings(pathSettings)

            elif packetType == app_packet.SOLO_SPLINE_ATTACH:
                attach = struct.unpack('<I', packetValue)
                self.handleAttach(attach)
            else:
                return False
        except Exception as e:
            logger.log('[multipoint]: Error handling packet. (%s)' % e)
            return False
        else:
            return True
