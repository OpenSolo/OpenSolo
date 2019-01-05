#  lookAtController.py
#  shotmanager
#
#  The lookAt movement controller. The drone stays still unless permuted by sticks or phone altitude.
#  Runs as a DroneKit-Python script.
#
#  Created by Jason Short on 2/26/2016.
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

logger = shotLogger.logger

class LookAtController():
    '''Manages altitude while holding XY position'''

    def __init__(self, vehicle, altitude):
        '''Initialize the controller'''

        # used to prevent user from going lower than initial alitide - prevents failed "landings"
        self.initial_altitude = altitude
        self.altitude = altitude
        
        # options attributes
        self.maxAlt = None
        self.maxClimbRate = None

        #initialize location
        self.currentLoc = LocationGlobalRelative(vehicle.location.global_relative_frame.lat, vehicle.location.global_relative_frame.lon, self.altitude)


    def setOptions(self, maxClimbRate, maxAlt):
        '''Sets maximum limits in open-loop controller'''
        self.maxClimbRate = maxClimbRate
        self.maxAlt = maxAlt
        
    def move(self, channels):
        '''Handles RC channels to return a position and velocity command
        location: location object, lat (deg), lon (deg), alt (meters)
        velocity: vector3 object, x, y, z (m/s) command'''

        # Climb
        currentVel = self._climb(channels[THROTTLE])

        # set altitude
        self.currentLoc.alt = self.altitude

        return self.currentLoc, currentVel
        

    def _climb(self, stick):
        '''Handles altitude stick input to increase or decrease altitude'''
        zVel = stick * self.maxClimbRate

        self.altitude += zVel * UPDATE_TIME

        # prevent landing in LookAt mode
        if self.altitude <= self.initial_altitude:
            self.altitude = self.initial_altitude
            return Vector3(0,0,0)
            
        # check altitude limit
        # In Follow Shot, this enforces alt limit relative to the initial ROI. (The ROI when the look at controller is instantiated)
        #   If the initial ROI is above the takeoff point, we depend on the follow shot to limit the superimposed altitude
        #   If the initial ROI is below the takeoff point, then the altitude limit relative to the ROI is enforced here.
        if self.maxAlt is not None:
            self.altitude = min(self.altitude, self.maxAlt)

        return Vector3(0,0,zVel)

