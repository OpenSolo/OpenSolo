#  TestFlyController.py
#  shotmanager
#
#  Unit tests for the orbit controller.
#
#  Created by Will Silva and Eric Liao on 1/19/2015.
#  Modified by Nick Speal on 3/16/2016
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

import flyController
from flyController import *

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
        self.startxOffset = 20 # meters
        self.startyOffset = 15 # meters
        self.startzOffset = 10 # meters
        self.startHeading = 0 # deg

        self.startLocation = location_helpers.addVectorToLocation(origin,Vector3(self.startxOffset, self.startyOffset, self.startzOffset))

        #Run the controller constructor
        self.controller = flyController.FlyController(origin, self.startxOffset, self.startyOffset, self.startzOffset, self.startHeading)
        
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
        origin = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startxOffset = 20 # meters
        self.startyOffset = 15 # meters
        self.startzOffset = 130 # meters
        self.startHeading = 0 # deg

        self.startLocation = location_helpers.addVectorToLocation(origin,Vector3(self.startxOffset, self.startyOffset, self.startzOffset))

        #Run the controller constructor
        self.controller = flyController.FlyController(origin, self.startxOffset, self.startyOffset, self.startzOffset, self.startHeading)
        self.controller._approach = Mock(return_value = Vector3())
        self.controller._strafe = Mock(return_value = Vector3())
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

        self.controller.move(self.channels, newHeading = 0, newOrigin = LocationGlobalRelative(37.873168,-122.302062, 20))


    def testCallApproach(self):
        '''Tests that _approach() is called'''

        self.controller._approach.assert_called_with(-0.5)

    def testCallStrafe(self):
        '''Tests that _strafe() is called'''
        
        self.controller._strafe.assert_called_with(-0.4)

    def testCallClimb(self):
        '''Tests that _climb() is called'''
        
        self.controller._climb.assert_called_with(0.7)

    def testAltitudeLimit(self):
        '''Test that maximum altitude is enforced when climbing'''
        self.assertEqual(self.controller.offset.z, self.controller.maxAlt)

    def testNeworigin(self):
        '''Tests that a new origin is set when passed via optional argument'''
        self.assertEqual(self.controller.origin.alt, 20)

    @mock.patch('location_helpers.addVectorToLocation')
    def testCallAddVectorToLocation(self, location_helpers_addVectorToLocation):
        '''Tests that location_helpers.addVectorToLocation() is called'''
        
        self.controller.move(self.channels)
        location_helpers_addVectorToLocation.assert_called_with(mock.ANY, mock.ANY)

class TestApproach(unittest.TestCase):
    def setUp(self):
        origin = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startxOffset = 20 # meters
        self.startyOffset = 15 # meters
        self.startzOffset = 10 # meters
        self.startHeading = 0 # deg

        self.startLocation = location_helpers.addVectorToLocation(origin,Vector3(self.startxOffset, self.startyOffset, self.startzOffset))

        #Run the controller constructor
        self.controller = flyController.FlyController(origin, self.startxOffset, self.startyOffset, self.startzOffset, self.startHeading)

        # set options
        self.controller.setOptions(maxClimbRate=1.5 ,maxAlt=45)

    def testPitchForwards(self):
        '''Stick/pitch forwards to move forwards'''

        approachVel = self.controller._approach(1.0)

        expectedXVel = math.cos(self.controller.heading) * self.controller.approachSpeed
        expectedYVel = math.sin(self.controller.heading) * self.controller.approachSpeed

        self.assertEqual(self.controller.approachSpeed, ACCEL_PER_TICK)
        self.assertEqual(approachVel, Vector3(expectedXVel, expectedYVel, 0))

    def testPitchBackwards(self):
        '''Stick/pitch backwards to move backwards'''

        approachVel = self.controller._approach(-1.0)

        expectedXVel = math.cos(self.controller.heading) * self.controller.approachSpeed
        expectedYVel = math.sin(self.controller.heading) * self.controller.approachSpeed

        self.assertEqual(self.controller.approachSpeed, -ACCEL_PER_TICK)
        self.assertEqual(approachVel, Vector3(expectedXVel, expectedYVel, 0))

    def testApproachSpeedDoNotExceed(self):
        '''Test that the incremented speed doesn't exceed approachSpeed'''

        self.controller.approachSpeed = 3.99
        self.controller._approach(0.5) #desired approach speed is 4 but an increment will put it over 4
        self.assertEqual(self.controller.approachSpeed,4) #make sure we're limited to 4

    def testApproachSpeedDoNotFallBelow(self):
        '''Test that the incremented speed doesn't fall below approachSpeed'''

        self.controller.approachSpeed = -3.99
        self.controller._approach(-0.5) #desired approach speed is 4 but an increment will put it under 4
        self.assertEqual(self.controller.approachSpeed,-4) #make sure we're limited to 4


class TestStrafe(unittest.TestCase):
    def setUp(self):
        origin = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startxOffset = 20 # meters
        self.startyOffset = 15 # meters
        self.startzOffset = 10 # meters
        self.startHeading = 0 # deg

        self.startLocation = location_helpers.addVectorToLocation(origin,Vector3(self.startxOffset, self.startyOffset, self.startzOffset))

        #Run the controller constructor
        self.controller = flyController.FlyController(origin, self.startxOffset, self.startyOffset, self.startzOffset, self.startHeading)

        # set options
        self.controller.setOptions(maxClimbRate=1.5 ,maxAlt=45)

    def testStrafeRight(self):
        '''Stick/roll right to move right'''

        strafeVel = self.controller._strafe(1.0)

        expectedXVel = math.cos(self.controller.heading + math.pi/2.) * self.controller.strafeSpeed
        expectedYVel = math.sin(self.controller.heading + math.pi/2.) * self.controller.strafeSpeed

        self.assertEqual(self.controller.strafeSpeed, ACCEL_PER_TICK)
        self.assertEqual(strafeVel, Vector3(expectedXVel, expectedYVel, 0))

    def testStrafeLeft(self):
        '''Stick/roll left to move left'''

        strafeVel = self.controller._strafe(-1.0)

        expectedXVel = math.cos(self.controller.heading + math.pi/2.) * self.controller.strafeSpeed
        expectedYVel = math.sin(self.controller.heading + math.pi/2.) * self.controller.strafeSpeed

        self.assertEqual(self.controller.strafeSpeed, -ACCEL_PER_TICK)
        self.assertEqual(strafeVel, Vector3(expectedXVel, expectedYVel, 0))

    def testApproachSpeedDoNotExceed(self):
        '''Test that the incremented speed doesn't exceed approachSpeed'''

        self.controller.strafeSpeed = 3.99
        self.controller._strafe(0.5) #desired approach speed is 4 but an increment will put it over 4
        self.assertEqual(self.controller.strafeSpeed,4) #make sure we're limited to 4

    def testApproachSpeedDoNotFallBelow(self):
        '''Test that the incremented speed doesn't fall below approachSpeed'''

        self.controller.strafeSpeed = -3.99
        self.controller._strafe(-0.5) #desired approach speed is 4 but an increment will put it under 4
        self.assertEqual(self.controller.strafeSpeed,-4) #make sure we're limited to 4


class TestClimb(unittest.TestCase):
    def setUp(self):
        origin = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startxOffset = 20 # meters
        self.startyOffset = 15 # meters
        self.startzOffset = 10 # meters
        self.startHeading = 0 # deg

        self.startLocation = location_helpers.addVectorToLocation(origin,Vector3(self.startxOffset, self.startyOffset, self.startzOffset))

        #Run the controller constructor
        self.controller = flyController.FlyController(origin, self.startxOffset, self.startyOffset, self.startzOffset, self.startHeading)

        # set options
        self.controller.setOptions(maxClimbRate=1.5 ,maxAlt=45)

    def testClimbUp(self):
        '''Test climbing up with stick up'''

        climbVel = self.controller._climb(1.0)
        self.assertEqual(climbVel, Vector3(0,0,1.0*self.controller.maxClimbRate))

    def testClimbDown(self):
        '''Test descending with stick down'''

        climbVel = self.controller._climb(-1.0)
        self.assertEqual(climbVel, Vector3(0,0,-1.0*self.controller.maxClimbRate))


class TestMaxApproachSpeed(unittest.TestCase):
    def setUp(self):
        origin = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startxOffset = 20 # meters
        self.startyOffset = 15 # meters
        self.startzOffset = 10 # meters
        self.startHeading = 0 # deg

        self.startLocation = location_helpers.addVectorToLocation(origin,Vector3(self.startxOffset, self.startyOffset, self.startzOffset))

        #Run the controller constructor
        self.controller = flyController.FlyController(origin, self.startxOffset, self.startyOffset, self.startzOffset, self.startHeading)

        # set options
        self.controller.setOptions(maxClimbRate=1.5 ,maxAlt=45)

    def testZeroStrafeSpeed(self):
        '''Test that approachSpeed gets all of MAX_SPEED if strafeSpeed is zero'''
        
        strafeSpeed = 0.0
        maxSpeed = self.controller._maxApproachSpeed(strafeSpeed)
        self.assertEqual(maxSpeed, MAX_SPEED)

    def testHalfStrafeSpeed(self):
        '''Test that approachSpeed is equal to strafeSpeed if strafeSpeed is sqrt(MAX_SPEED*4)'''
        
        strafeSpeed = math.sqrt(MAX_SPEED*4)
        maxSpeed = self.controller._maxApproachSpeed(strafeSpeed)
        self.assertAlmostEqual(maxSpeed, strafeSpeed)

    def testAllStrafeSpeed(self):
        '''Test that approachSpeed is zero if strafeSpeed is MAX_SPEED'''

        strafeSpeed = MAX_SPEED
        maxSpeed = self.controller._maxApproachSpeed(strafeSpeed)
        self.assertEqual(maxSpeed, 0.0)
        

class TestMaxStrafeSpeed(unittest.TestCase):
    def setUp(self):
        origin = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startxOffset = 20 # meters
        self.startyOffset = 15 # meters
        self.startzOffset = 10 # meters
        self.startHeading = 0 # deg

        self.startLocation = location_helpers.addVectorToLocation(origin,Vector3(self.startxOffset, self.startyOffset, self.startzOffset))

        #Run the controller constructor
        self.controller = flyController.FlyController(origin, self.startxOffset, self.startyOffset, self.startzOffset, self.startHeading)

        # set options
        self.controller.setOptions(maxClimbRate=1.5 ,maxAlt=45)

    def testZeroApproachSpeed(self):
        '''Test that strafeSpeed gets all of MAX_SPEED if approachSpeed is zero'''
        
        approachSpeed = 0.0
        maxSpeed = self.controller._maxStrafeSpeed(approachSpeed)
        self.assertEqual(maxSpeed, MAX_SPEED)

    def testHalfApproachSpeed(self):
        '''Test that strafeSpeed is equal to approachSpeed if approachSpeed is sqrt(MAX_SPEED*4)'''
        
        approachSpeed = math.sqrt(MAX_SPEED*4)
        maxSpeed = self.controller._maxStrafeSpeed(approachSpeed)
        self.assertAlmostEqual(maxSpeed, approachSpeed)

    def testAllApproachSpeed(self):
        '''Test that strafeSpeed is zero if approachSpeed is MAX_SPEED'''

        approachSpeed = MAX_SPEED
        maxSpeed = self.controller._maxStrafeSpeed(approachSpeed)
        self.assertEqual(maxSpeed, 0.0)

