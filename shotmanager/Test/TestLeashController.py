#  TestLeashController.py
#  shotmanager
#
#  Unit tests for the orbit-based Leash controller.
#
#  Created by Nick Speal on 3/16/2016.
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

import leashController
from leashController import *

from dronekit import LocationGlobalRelative

import unittest

import mock
from mock import call
from mock import Mock
from mock import MagicMock
from mock import patch


class testInit(unittest.TestCase):
    def setUp(self):
        roi = LocationGlobalRelative(37.873168,-122.302062, 1) # lat,lon,alt
        self.startRadius = 20 # meters
        self.startAzimuth = 15 # deg
        self.startAltitude = 10 # meters

        self.startLocation = location_helpers.newLocationFromAzimuthAndDistance(roi,self.startAzimuth,self.startRadius)
        self.startLocation.alt = self.startAltitude

        #Run the controller constructor
        self.controller = leashController.LeashController(roi, self.startRadius, self.startAzimuth, self.startAltitude)

    def testInheritanceDidCall(self):
        # TODO
        # want to test if the orbitController class actually gets inherited. Not sure how exactly.
        pass


class testMove(unittest.TestCase):
    def setUp(self):
        self.oldROI = LocationGlobalRelative(37.873168,-122.302062, 1) # lat,lon,alt
        self.startRadius = 20 # meters
        self.startAzimuth = 15 # deg
        self.startAltitude = 10 # meters


        self.startLocation = location_helpers.newLocationFromAzimuthAndDistance(self.oldROI,self.startAzimuth,self.startRadius)
        self.startLocation.alt = self.startAltitude

        #Run the controller constructor
        self.controller = leashController.LeashController(self.oldROI, self.startRadius, self.startAzimuth, self.startAltitude)

        #Arbirary sticks
        throttle = 0.3
        roll = -0.4
        pitch = 0.5
        yaw = -0.6
        raw_paddle = 0.7
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, raw_paddle]

        #Attributes
        self.controller.maxClimbRate = 5.

        #methods
        self.controller._approach = Mock(return_value = Vector3())
        self.controller._climb = Mock(return_value = Vector3())


    def testRadiusReset(self):
        self.controller.approachSpeed = 1
        self.controller.distance = self.startRadius/2.
        newROI = location_helpers.newLocationFromAzimuthAndDistance(self.startLocation,self.startAzimuth,self.controller.distance)

        self.controller.move(self.channels, newroi = newROI)

        #No way to assert execution of the if statement..

    def testVelocityUpdateMethodsAreCalled(self):
        self.controller.move(self.channels, newroi = self.oldROI)
        assert self.controller._approach.called
        assert self.controller._climb.called


    def testStopCaseWithStaticROI(self):
        self.controller.approachSpeed = 0
        newROI = self.oldROI # Same as original roi
        self.controller.move(self.channels, newroi = newROI)

    def testStopCaseWithApproachSpeed(self):
        newROI = location_helpers.newLocationFromAzimuthAndDistance(self.oldROI,0.0, 50)
        self.controller.approachSpeed = 1
        self.controller.move(self.channels, newroi = newROI)

    def testDontStop(self):
        newROI = location_helpers.newLocationFromAzimuthAndDistance(self.oldROI,0.0, 50)
        self.controller.approachSpeed = 0
        self.controller.move(self.channels, newroi = newROI)        

