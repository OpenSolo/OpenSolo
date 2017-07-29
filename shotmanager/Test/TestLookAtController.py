#  TestLookAtController.py
#  shotmanager
#
#  Unit tests for the orbit controller.
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


import lookAtController
from lookAtController import *

from dronekit import LocationGlobalRelative

import unittest

import mock
from mock import call
from mock import Mock
from mock import MagicMock
from mock import patch


class TestSetOptions(unittest.TestCase):
    def setUp(self):
        origin = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        
        '''Create a mock vehicle object'''
        vehicle = mock.create_autospec(Vehicle)
        controllerAlt = 5

        #Run the controller constructor
        self.controller = lookAtController.LookAtController(vehicle, controllerAlt)
        
    def testSetBothOptions(self):
        '''Tests setting both options'''
        self.controller.setOptions(maxClimbRate = 3, maxAlt = 75)
        self.assertEqual(self.controller.maxClimbRate, 3)
        self.assertEqual(self.controller.maxAlt, 75)

    def testSetOptionsNoAltLimit(self):
        '''Tests setting both options, with disabled altitude limit'''
        self.controller.setOptions(maxClimbRate = 3, maxAlt = None)
        self.assertEqual(self.controller.maxClimbRate, 3)
        self.assertEqual(self.controller.maxAlt, None)

class TestMove(unittest.TestCase):
    def setUp(self):
        '''Create a mock vehicle object'''
        vehicle = mock.create_autospec(Vehicle)
        controllerAlt = 105

        #Run the controller constructor
        self.controller = lookAtController.LookAtController(vehicle, controllerAlt)

        self.controller._climb = Mock(return_value = Vector3())

        #Set options
        self.controller.maxClimbRate = 5 # m/s
        self.controller.maxAlt = 100 #m

        #Arbirary sticks
        throttle = 0.3
        roll = -0.4
        pitch = 0.5
        yaw = -0.6
        raw_paddle = 0.7
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, raw_paddle]

        self.controller.move(self.channels)


    def testCallClimb(self):
        '''Tests that _climb() is called'''
        
        self.controller._climb.assert_called_with(0.3)

    


class TestClimb(unittest.TestCase):
    def setUp(self):
        '''Create a mock vehicle object'''
        vehicle = mock.create_autospec(Vehicle)
        controllerAlt = 5

        #Run the controller constructor
        self.controller = lookAtController.LookAtController(vehicle, controllerAlt)

        # set options
        self.controller.setOptions(maxClimbRate=1.5 ,maxAlt=45)

    def testClimbUp(self):
        '''Test climbing up with stick up'''

        self.controller.altitude = 100
        climbVel = self.controller._climb(1.0)
        self.assertEqual(climbVel, Vector3(0,0,1.0*self.controller.maxClimbRate))

    def testClimbDown(self):
        '''Test descending with stick down'''

        self.controller.altitude = 100
        climbVel = self.controller._climb(-1.0)
        self.assertEqual(climbVel, Vector3(0,0,-1.0*self.controller.maxClimbRate))

    def testAltitudeLimit(self):
        '''Test that maximum altitude is enforced when climbing'''
        self.controller.altitude = 105
        climbVel = self.controller._climb(-1.0)
        self.assertEqual(self.controller.altitude, self.controller.maxAlt)        


