#  leashController.py
#  shotmanager
#
#  The leash movement controller.
#  A cylindrical-coordinates based orbit motion controller than be permuted by user-sticks or a strafe cruise speed
#  Automatically swings the copter around to be behind the direction of motion.
#
#  Runs as a DroneKit-Python script.
#
#  Created by Jason Short and Nick Speal on 2/26/2016.
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

from pymavlink import mavutil
from dronekit import Vehicle, LocationGlobalRelative
import location_helpers
import shotLogger
from shotManagerConstants import *
import math
from vector3 import Vector3
from orbitController import OrbitController

logger = shotLogger.logger

#Path accel/decel constants
PATH_ACCEL = 2.5
ACCEL_PER_TICK = PATH_ACCEL * UPDATE_TIME
ORBIT_RAD_FOR_MIN_SPEED = 2.0

''' Crosstrack control '''
CROSSTRACK_GAIN = 3
CROSSTRACK_MINSPEED = .25
# seems to be the safest limit (CS gain of 4)
CROSSTRACK_MAX = 360 * UPDATE_TIME

class LeashController(OrbitController):
    def __init__(self, roi, radius, azimuth, zOffset):
        super(LeashController, self).__init__(roi, radius, azimuth, zOffset)
        #initialize location
        self.currentLoc = location_helpers.newLocationFromAzimuthAndDistance(self.roi, self.azimuth, self.radius)
        self.currentLoc.altitude =  roi.alt + zOffset
        self.distance = radius
        

    def move(self, channels, newroi=None, roiVel=None):
        '''Handles RC channels to return a position and velocity command
        location: location object, lat (deg), lon (deg), alt (meters)
        velocity: vector3 object, x, y, z (m/s) command'''

        # If we are inside of the circle, we overide the radius
        # with our position to prevent sudden flight to or away from pilot
        if self.approachSpeed != 0 and self.distance < self.radius:
            self.radius = self.distance

        if roiVel is None:
            roiVel = Vector3(0,0,0)

        # Approach
        approachVel = self._approach(-channels[PITCH])
        
        # Climb
        climbVel = self._climb(channels[THROTTLE])

        # ROI heading is calculated and flipped 180deg to determine leash angle
        roiHeading = location_helpers.calcAzimuthFromPoints(self.roi, newroi)
        roiHeading += 180
        roiHeading = location_helpers.wrapTo360(roiHeading)

        # roiSpeed is used to determine if we apply crosstrack error correction
        roiSpeed = location_helpers.getDistanceFromPoints(self.roi, newroi) / UPDATE_TIME
                
        if roiSpeed < CROSSTRACK_MINSPEED or self.approachSpeed != 0:
            # we are not moving very fast, don't crosstrack
            # prevents swinging while we are still.
            crosstrackGain = 0
        else:
            crosstrackGain = CROSSTRACK_GAIN

        # Used to test are we inside the radius or on it?
        # we use old ROI because current location is not set yet
        # and wont be for the test function 
        self.distance = location_helpers.getDistanceFromPoints(self.roi, self.currentLoc)
        
        # overwrite old ROI with new
        self.roi = newroi

        # new Az from ROI to current position
        self.azimuth = location_helpers.calcAzimuthFromPoints(self.roi, self.currentLoc)
        
        # angle error of ROI Heading vs Azimuth
        headingError = roiHeading - self.azimuth
        headingError = location_helpers.wrapTo180(headingError)

        # used to determine if the copter in front of us or behind
        angleErrorTest = abs(headingError)
        
        # limit error
        if headingError > 90:
            headingError = 90
        elif headingError < -90:
            headingError = -90        

        if self.distance < (self.radius - 1) and self.approachSpeed == 0:
            # we are inside the circle with a margin of error to prevent small jerks
            # -1 on z is used as a dataflag for no desired velocity
            currentVel = Vector3(0,0,0)
            

        elif angleErrorTest > 90 and self.approachSpeed == 0:
            # We are outside the circle
            # We are walking toward copter
            currentVel = Vector3(0,0,0)
            
            
        else:
            # Follow leash and manage crosstrack
            # bring in the Az to match the ROI heading
            crosstrack = headingError * crosstrackGain * UPDATE_TIME
            crosstrack = min(crosstrack, CROSSTRACK_MAX)
            
            # scale down the crosstracking with the distance (min 1m to avoid div/0)
            self.azimuth += crosstrack / max(self.distance - 1, 1)
            
            # for calculating velocity vector (unpack and then pack object to copy the values not the reference)
            oldPos = LocationGlobalRelative(self.currentLoc.lat, self.currentLoc.lon, self.currentLoc.alt)

            # get new location from Az and radius
            self.currentLoc = location_helpers.newLocationFromAzimuthAndDistance(self.roi, self.azimuth, self.radius)
        
            # calc velocity to new position
            currentVel = location_helpers.getVectorFromPoints(oldPos, self.currentLoc)
            
            # convert to speed
            currentVel = (currentVel * UPDATE_TIME) + approachVel + roiVel
            

        # Climb/descend in all cases, even if holding still translationally
        currentVel += climbVel

        # set altitude
        self.currentLoc.alt = self.roi.alt + self.zOffset

        # check altitude limit
        if self.maxAlt is not None:
            self.currentLoc.alt = min(self.currentLoc.alt, self.maxAlt)

        return self.currentLoc, currentVel