#  orbitController.py
#  shotmanager
#
#  The orbit movement controller.
#
#  Runs as a DroneKit-Python script
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
#
# Usage:
# Instantiated by Orbit and Follow shots.
# Inherited by leashController.

from pymavlink import mavutil
import location_helpers
import shotLogger
from shotManagerConstants import *
import math
from vector3 import Vector3

logger = shotLogger.logger

#Path accel/decel constants
PATH_ACCEL = 2.5
ACCEL_PER_TICK = PATH_ACCEL * UPDATE_TIME

ORBIT_MIN_SPEED = 3.0
ORBIT_MAX_SPEED = 8.0
ORBIT_RAD_FOR_MIN_SPEED = 2.0
ORBIT_RAD_FOR_MAX_SPEED = 30.0

THROTTLE = 0
ROLL = 1
PITCH = 2
YAW = 3
RAW_PADDLE = 7

class OrbitController(object):
    '''A cylindrical-coordinates based orbit motion controller than be permuted by user-sticks or a strafe cruise speed'''

    def __init__(self, roi, radius, azimuth, zOffset):
        '''Initialize the controller at a cylindrical coordinate relative to an ROI origin'''

        self.roi = roi
        self.radius = radius
        self.azimuth = azimuth
        self.zOffset = zOffset
        self.approachSpeed = 0.0
        self.strafeSpeed = 0.0

        # options attributes (never reset unless object is destroyed)
        self.maxAlt = None
        self.maxClimbRate = None

    def setOptions(self, maxClimbRate, maxAlt):
        '''Sets maximum limits in open-loop controller'''
        self.maxClimbRate = maxClimbRate
        self.maxAlt = maxAlt 

    def move(self, channels, cruiseSpeed, newroi=None, roiVel=None):
        '''Handles RC channels and a given strafeSpeed to return a position and velocity command
        location: location object, lat (deg), lon (deg), alt (meters)
        velocity: vector3 object, x, y, z (m/s) command'''

        if roiVel is None:
            roiVel = Vector3(0,0,0)

        # Approach
        approachVel = self._approach(-channels[PITCH])

        # Strafe
        strafeVel = self._strafe(channels[ROLL], cruiseSpeed)
 
        # Climb
        climbVel = self._climb(channels[THROTTLE])

        # calculate new LLA position
        if newroi is not None:
            self.roi = newroi
        currentPos = location_helpers.newLocationFromAzimuthAndDistance(self.roi, self.azimuth, self.radius)

        # set altitude (This is for generality with follow. In the Orbit shot, roi.alt should be zero.)
        currentPos.alt = self.roi.alt + self.zOffset

        # check altitude limit
        if self.maxAlt is not None:
            currentPos.alt = min(currentPos.alt, self.maxAlt)

        # sum velocities
        currentVel = approachVel + strafeVel + climbVel + roiVel

        return currentPos, currentVel

    def _approach(self,stick):
        '''Handles approach stick input to grow or shrink orbit radius'''

        # set to vehicle max speed
        maxSpeed = MAX_SPEED

        # Approach speed is controlled by user PITCH stick
        speed = stick * maxSpeed

        # Synthetic acceleration limit
        if speed > self.approachSpeed:
            self.approachSpeed += ACCEL_PER_TICK
            self.approachSpeed = min(self.approachSpeed, speed)
        elif speed < self.approachSpeed:
            self.approachSpeed -= ACCEL_PER_TICK
            self.approachSpeed = max(self.approachSpeed, speed)
        else:
            self.approachSpeed = speed

        # update current radius
        self.radius -= ( self.approachSpeed * UPDATE_TIME )

        # az from vehicle to ROI
        #az = location_helpers.calcAzimuthFromPoints(self.vehicle.location, self.roi)
        az = location_helpers.wrapTo360(self.azimuth + 180.0)
        az = math.radians( az )

        # rotate vehicle from entering min radius
        xVel = math.cos(az) * self.approachSpeed
        yVel = math.sin(az) * self.approachSpeed

        # stop vehicle from entering min radius
        if self.radius < ORBIT_RAD_FOR_MIN_SPEED:
            self.radius = ORBIT_RAD_FOR_MIN_SPEED
            xVel = yVel = 0.0

        return Vector3(xVel,yVel,0)

    def _strafe(self, stick, strafeSpeed = 0):
        '''Handles strafe stick input and cruiseSpeed to strafe left or right on the circle'''

        # get max speed at current radius
        maxSpeed = self._maxStrafeSpeed(self.radius)

        # cruiseSpeed can be permuted by user ROLL stick            
        if strafeSpeed == 0.0:
            speed = stick * maxSpeed
        else:
            speed = abs(strafeSpeed)

            # if sign of stick and cruiseSpeed don't match then...
            if math.copysign(1,stick) != math.copysign(1,strafeSpeed): # slow down
                speed *= (1.0 - abs(stick))
            else: # speed up
                speed += (maxSpeed - speed) * abs(stick)

            # carryover user input sign
            if strafeSpeed < 0:
                speed = -speed

            # limit speed
            if speed > maxSpeed:
                speed = maxSpeed
            elif -speed > maxSpeed:
                speed = -maxSpeed

        # Synthetic acceleration limit
        if speed > self.strafeSpeed:
            self.strafeSpeed += ACCEL_PER_TICK
            self.strafeSpeed = min(self.strafeSpeed, speed)
        elif speed < self.strafeSpeed:
            self.strafeSpeed -= ACCEL_PER_TICK
            self.strafeSpeed = max(self.strafeSpeed, speed)
        else:
            self.strafeSpeed = speed

        # circumference of current circle
        circum = self.radius * 2.0 * math.pi

        # # of degrees of our circle to shoot for moving to this update
        # had problems when we made this too small
        degrees = abs(self.strafeSpeed) * UPDATE_TIME / circum * 360.0

        # rotate heading by the number of degrees/update
        if self.strafeSpeed > 0:
            self.azimuth -= degrees
        else:
            self.azimuth += degrees

        # make sure we keep it 0-360
        self.azimuth = location_helpers.wrapTo360(self.azimuth)

        # generate a velocity tangent to our circle from our destination point
        if self.strafeSpeed > 0:
            tangent = self.azimuth - 90.0
        else:
            tangent = self.azimuth + 90.0

        tangent = math.radians(tangent)

        #based on that, construct a vector to represent what direction we should go in, scaled by our speed
        xVel = math.cos(tangent) * abs(self.strafeSpeed)
        yVel = math.sin(tangent) * abs(self.strafeSpeed)

        return Vector3(xVel,yVel,0)

    def _climb(self, stick):
        '''Handles altitude stick input to increase or decrease altitude'''

        # Z is down, so invert it
        zVel = stick * self.maxClimbRate
        self.zOffset += zVel * UPDATE_TIME

        return Vector3(0,0,zVel)

    def _maxStrafeSpeed(self, radius):
        '''Returns maximum strafe speed as a function of orbit radius'''
        
        # start out at max orbit strafe speed
        maxSpeed = ORBIT_MAX_SPEED

        # scale down max speed if we're really close to our target
        if self.radius < ORBIT_RAD_FOR_MIN_SPEED:
            maxSpeed = ORBIT_MIN_SPEED
        elif self.radius >= ORBIT_RAD_FOR_MAX_SPEED:
            maxSpeed = ORBIT_MAX_SPEED
        else:
            ratio = (self.radius - ORBIT_RAD_FOR_MIN_SPEED) / (ORBIT_RAD_FOR_MAX_SPEED - ORBIT_RAD_FOR_MIN_SPEED)
            maxSpeed = ORBIT_MIN_SPEED + ((ORBIT_MAX_SPEED - ORBIT_MIN_SPEED) * ratio)

        return maxSpeed
