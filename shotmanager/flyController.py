#  flyController.py
#  shotmanager
#
#  The fly movement controller.
#  Runs as a DroneKit-Python script.
#
#  Created by Will Silva on 1/22/2015.
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
import location_helpers
import shotLogger
from shotManagerConstants import *
import math
from vector3 import Vector3

logger = shotLogger.logger

#Path accel/decel constants
PATH_ACCEL = 3
ACCEL_PER_TICK = PATH_ACCEL * UPDATE_TIME


class FlyController():
    '''A rectangular-coordinates based motion controller than be permuted by user-sticks (operates similarly to Solo's FLY mode)'''

    def __init__(self, origin, xOffset, yOffset, zOffset, heading):
        '''Initialize the controller at a rectangular coordinate relative to an origin origin
        NEU frame (x-North,y-East,z-Up)'''

        self.origin = origin
        self.offset = Vector3(xOffset, yOffset, zOffset)
        self.heading = heading * math.pi/180.

        self.approachSpeed = 0.0
        self.strafeSpeed = 0.0
        self.climbSpeed = 0.0

        # options attributes
        self.maxAlt = None
        self.maxClimbRate = None
        self.maxSpeed = MAX_SPEED

    def setOptions(self, maxClimbRate, maxAlt):
        '''Sets maximum limits in open-loop controller'''
        self.maxClimbRate = maxClimbRate
        self.maxAlt = maxAlt 


    def move(self, channels, newHeading=None, newOrigin=None, roiVel=None):
        '''Handles RC channels to return a position and velocity command
        location: location object, lat (deg), lon (deg), alt (meters)
        velocity: vector3 object, x, y, z (m/s) command'''

        if newOrigin is not None:
            self.origin = newOrigin

        if newHeading is not None:
            self.heading = newHeading * math.pi/180.

        if roiVel is None:
            roiVel = Vector3(0,0,0)

        # Approach
        approachVel = self._approach(-channels[PITCH])

        # Strafe
        strafeVel = self._strafe(channels[ROLL])
 
        # Climb
        climbVel = self._climb(channels[RAW_PADDLE])

        # add up velocities
        currentVel = approachVel + strafeVel + climbVel

        # add up positions
        self.offset += currentVel * UPDATE_TIME

        # check altitude limit
        if self.maxAlt is not None:
            self.offset.z = min(self.maxAlt, self.offset.z)

        # convert x,y,z to inertial LLA    
        currentPos = location_helpers.addVectorToLocation(self.origin, self.offset)
        currentVel += roiVel
    
        return currentPos, currentVel

    def _approach(self,stick):
        '''Handles approach stick input to move forwards or backwards'''

        # get max approach speed based on current strafe speed
        maxSpeed = self._maxApproachSpeed(self.strafeSpeed)

        # Approach speed is controlled by user PITCH stick
        speed = stick * maxSpeed

        # Synthetic acceleration limit
        if speed > self.approachSpeed:
            self.approachSpeed += ACCEL_PER_TICK
            self.approachSpeed = min(self.approachSpeed, speed)
        elif speed < self.approachSpeed:
            self.approachSpeed -= ACCEL_PER_TICK
            self.approachSpeed = max(self.approachSpeed, speed)

        # rotate vehicle into NEU frame
        xVel = math.cos(self.heading) * self.approachSpeed
        yVel = math.sin(self.heading) * self.approachSpeed

        return Vector3(xVel,yVel,0)

    def _strafe(self, stick):
        '''Handles strafe stick input to move left or right'''

        # get max strafe speed
        maxSpeed = self._maxStrafeSpeed(self.approachSpeed)

        # Strafe speed is controlled by user ROLL stick
        speed = stick * maxSpeed

        # Synthetic acceleration limit
        if speed > self.strafeSpeed:
            self.strafeSpeed += ACCEL_PER_TICK
            self.strafeSpeed = min(self.strafeSpeed, speed)
        elif speed < self.strafeSpeed:
            self.strafeSpeed -= ACCEL_PER_TICK
            self.strafeSpeed = max(self.strafeSpeed, speed)
        
        # rotate vehicle into NEU frame
        xVel = math.cos(self.heading+math.pi/2.) * self.strafeSpeed
        yVel = math.sin(self.heading+math.pi/2.) * self.strafeSpeed

        return Vector3(xVel,yVel,0)

    def _climb(self, stick):
        '''Handles altitude stick input to increase or decrease altitude'''

        # calculate z vel
        zVel = stick * self.maxClimbRate

        return Vector3(0,0,zVel)

    def _maxApproachSpeed(self, strafeSpeed):
        '''Returns maximum approach speed as a function of strafe speed'''
        
        maxSpeed = math.sqrt(self.maxSpeed**2 - strafeSpeed**2)

        return maxSpeed

    def _maxStrafeSpeed(self, approachSpeed):
        '''Returns maximum strafe speed as a function of approach speed'''
        
        maxSpeed = math.sqrt(self.maxSpeed**2 - approachSpeed**2)

        return maxSpeed

