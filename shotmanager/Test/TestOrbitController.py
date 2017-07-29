#  TestOrbitController.py
#  shotmanager
#
#  Unit tests for the orbit controller.
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

import orbitController
from orbitController import *

from dronekit import LocationGlobalRelative

import unittest

import mock
from mock import call
from mock import Mock
from mock import MagicMock
from mock import patch


class TestSetOptions(unittest.TestCase):
    def setUp(self):
        roi = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startRadius = 20 # meters
        self.startAzimuth = 15 # deg
        self.startAltitude = 10 # meters

        self.startLocation = location_helpers.newLocationFromAzimuthAndDistance(roi,self.startAzimuth,self.startRadius)
        self.startLocation.alt = self.startAltitude

        #Run the controller constructor
        self.controller = orbitController.OrbitController(roi, self.startRadius, self.startAzimuth, self.startAltitude+roi.alt)
    
    def testSetBoth(self):
        '''Tests setting both options'''

        self.controller.setOptions(maxClimbRate = 3, maxAlt = 75)
        self.assertEqual(self.controller.maxClimbRate, 3)
        self.assertEqual(self.controller.maxAlt, 75)

class TestMove(unittest.TestCase):
    def setUp(self):
        roi = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startRadius = 20 # meters
        self.startAzimuth = 15 # deg
        self.startAltitude = 10 # meters

        self.startLocation = location_helpers.newLocationFromAzimuthAndDistance(roi,self.startAzimuth,self.startRadius)
        self.startLocation.alt = self.startAltitude

        #Run the controller constructor
        self.controller = orbitController.OrbitController(roi, self.startRadius, self.startAzimuth, self.startAltitude+roi.alt)
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

        self.controller.move(self.channels, cruiseSpeed = 1, newroi = LocationGlobalRelative(37.873168,-122.302062, 20))


    def testCallApproach(self):
        '''Tests that _approach() is called'''

        self.controller._approach.assert_called_with(-0.5)

    def testCallStrafe(self):
        '''Tests that _strafe() is called'''
        
        self.controller._strafe.assert_called_with(-0.4, 1)

    def testCallClimb(self):
        '''Tests that _climb() is called'''
        
        self.controller._climb.assert_called_with(0.3)

    def testNewROI(self):
        '''Tests that a new roi is set when passed via optional argument'''
        
        self.assertEqual(self.controller.roi.alt, 20)

    @mock.patch('location_helpers.newLocationFromAzimuthAndDistance')
    def testCallNewLocationFromAzimuthAndDistance(self, location_helpers_newLocationFromAzimuthAndDistance):
        '''Tests that location_helpers.newLocationFromAzimuthAndDistance() is called'''
        
        self.controller.move(self.channels, cruiseSpeed = 1)
        location_helpers_newLocationFromAzimuthAndDistance.assert_called_with(mock.ANY, mock.ANY, mock.ANY)

class TestApproach(unittest.TestCase):
    def setUp(self):
        roi = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startRadius = 20 # meters
        self.startAzimuth = 15 # deg
        self.startAltitude = 10 # meters

        self.startLocation = location_helpers.newLocationFromAzimuthAndDistance(roi,self.startAzimuth,self.startRadius)
        self.startLocation.alt = self.startAltitude

        #Run the controller constructor
        self.controller = orbitController.OrbitController(roi, self.startRadius, self.startAzimuth, self.startAltitude+roi.alt)

        # set options
        self.controller.setOptions(maxClimbRate=1.5 ,maxAlt=45)

    def testShrinkRadius(self):
        '''Stick/pitch forwards to shrink radius'''

        approachVel = self.controller._approach(1.0)

        expectedXVel = math.cos(math.radians(self.controller.azimuth+180)) * self.controller.approachSpeed
        expectedYVel = math.sin(math.radians(self.controller.azimuth+180)) * self.controller.approachSpeed

        self.assertEqual(self.controller.approachSpeed, ACCEL_PER_TICK)
        self.assertEqual(self.controller.radius, self.startRadius - ACCEL_PER_TICK*UPDATE_TIME)
        self.assertEqual(approachVel, Vector3(expectedXVel, expectedYVel))

    def testGrowRadius(self):
        '''Stick/pitch backwards to grow radius'''

        approachVel = self.controller._approach(-1.0)

        expectedXVel = math.cos(math.radians(self.controller.azimuth+180)) * self.controller.approachSpeed
        expectedYVel = math.sin(math.radians(self.controller.azimuth+180)) * self.controller.approachSpeed

        self.assertEqual(self.controller.approachSpeed, -ACCEL_PER_TICK)
        self.assertEqual(self.controller.radius, self.startRadius + ACCEL_PER_TICK*UPDATE_TIME)
        self.assertEqual(approachVel, Vector3(expectedXVel, expectedYVel))

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

    def testEnforceMinRadius(self):
        '''Test that our radius can't fall below the minimum radius'''
        self.controller.radius = ORBIT_RAD_FOR_MIN_SPEED
        self.controller._approach(1.0)
        self.assertEqual(self.controller.radius,ORBIT_RAD_FOR_MIN_SPEED)


class TestStrafe(unittest.TestCase):
    def setUp(self):
        roi = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startRadius = 20 # meters
        self.startAzimuth = 15 # deg
        self.startAltitude = 10 # meters

        self.startLocation = location_helpers.newLocationFromAzimuthAndDistance(roi,self.startAzimuth,self.startRadius)
        self.startLocation.alt = self.startAltitude

        #Run the controller constructor
        self.controller = orbitController.OrbitController(roi, self.startRadius, self.startAzimuth, self.startAltitude+roi.alt)

        # set options
        self.controller.setOptions(maxClimbRate=1.5 ,maxAlt=45)

    def testStrafeRight(self):
        '''Stick/roll right to decrease azimuth'''

        strafeVel = self.controller._strafe(1.0)

        tangent = self.controller.azimuth - math.copysign(90,self.controller.strafeSpeed)
        expectedXVel = math.cos(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        expectedYVel = math.sin(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        degreesDelta = 360. * self.controller.strafeSpeed / (2. * math.pi * self.controller.radius) * UPDATE_TIME

        self.assertEqual(self.controller.strafeSpeed, ACCEL_PER_TICK)
        self.assertEqual(self.controller.azimuth, self.startAzimuth - degreesDelta)
        self.assertEqual(strafeVel, Vector3(expectedXVel, expectedYVel))

    def testStrafeLeft(self):
        '''Stick/roll left to increase azimuth'''

        strafeVel = self.controller._strafe(-1.0)

        tangent = self.controller.azimuth - math.copysign(90,self.controller.strafeSpeed)
        expectedXVel = math.cos(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        expectedYVel = math.sin(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        degreesDelta = 360. * self.controller.strafeSpeed / (2. * math.pi * self.controller.radius) * UPDATE_TIME

        self.assertEqual(self.controller.strafeSpeed, -ACCEL_PER_TICK)
        self.assertEqual(self.controller.azimuth, self.startAzimuth - degreesDelta)
        self.assertEqual(strafeVel, Vector3(expectedXVel, expectedYVel))

    def testStrafeMaxSpeedUsingStick(self):
        '''Test that the dynamic strafe speed limit (function of radius) is enforced with sticks'''

        speedLimit = self.controller._maxStrafeSpeed(self.controller.radius)
        self.controller.strafeSpeed = speedLimit
        strafeVel = self.controller._strafe(1.0)
        self.assertEqual(self.controller.strafeSpeed,speedLimit)

    def testStrafeMaxSpeedUsingCruise(self):
        '''Test that the dynamic strafe speed limit (function of radius) is enforced with cruise'''

        speedLimit = self.controller._maxStrafeSpeed(self.controller.radius)
        self.controller.strafeSpeed = speedLimit
        strafeVel = self.controller._strafe(1.0, strafeSpeed = speedLimit)
        self.assertEqual(self.controller.strafeSpeed,speedLimit)

    def testCruiseRight(self):
        '''Test cruising to the right'''

        strafeVel = self.controller._strafe(0.0, strafeSpeed = 5)

        tangent = self.controller.azimuth - math.copysign(90,self.controller.strafeSpeed)
        expectedXVel = math.cos(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        expectedYVel = math.sin(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        degreesDelta = 360. * self.controller.strafeSpeed / (2. * math.pi * self.controller.radius) * UPDATE_TIME

        self.assertEqual(self.controller.strafeSpeed, ACCEL_PER_TICK)
        self.assertEqual(self.controller.azimuth, self.startAzimuth - degreesDelta)
        self.assertEqual(strafeVel, Vector3(expectedXVel, expectedYVel))

    def testCruiseLeft(self):
        '''Test cruising to the left'''

        strafeVel = self.controller._strafe(0.0, strafeSpeed = -5)

        tangent = self.controller.azimuth - math.copysign(90,self.controller.strafeSpeed)
        expectedXVel = math.cos(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        expectedYVel = math.sin(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        degreesDelta = 360. * self.controller.strafeSpeed / (2. * math.pi * self.controller.radius) * UPDATE_TIME

        self.assertEqual(self.controller.strafeSpeed, -ACCEL_PER_TICK)
        self.assertEqual(self.controller.azimuth, self.startAzimuth - degreesDelta)
        self.assertEqual(strafeVel, Vector3(expectedXVel, expectedYVel))

    def testCruiseSpeedUpRight(self):
        '''Test that we can speed up cruiseSpeed using stick'''

        self.controller.strafeSpeed = 4
        strafeVel = self.controller._strafe(0.5, strafeSpeed = 4)

        tangent = self.controller.azimuth - math.copysign(90,self.controller.strafeSpeed)
        expectedXVel = math.cos(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        expectedYVel = math.sin(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        degreesDelta = 360. * self.controller.strafeSpeed / (2. * math.pi * self.controller.radius) * UPDATE_TIME

        self.assertEqual(self.controller.strafeSpeed, 4 + ACCEL_PER_TICK)
        self.assertEqual(self.controller.azimuth, self.startAzimuth - degreesDelta)
        self.assertEqual(strafeVel, Vector3(expectedXVel, expectedYVel))

    def testCruiseSlowDownRight(self):
        '''Test that we can slow down cruiseSpeed using stick left'''

        self.controller.strafeSpeed = 4
        strafeVel = self.controller._strafe(-0.5, strafeSpeed = 4)

        tangent = self.controller.azimuth - math.copysign(90,self.controller.strafeSpeed)
        expectedXVel = math.cos(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        expectedYVel = math.sin(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        degreesDelta = 360. * self.controller.strafeSpeed / (2. * math.pi * self.controller.radius) * UPDATE_TIME

        self.assertEqual(self.controller.strafeSpeed, 4 - ACCEL_PER_TICK)
        self.assertEqual(self.controller.azimuth, self.startAzimuth - degreesDelta)
        self.assertEqual(strafeVel, Vector3(expectedXVel, expectedYVel))

    def testCruiseSpeedUpLeft(self):
        '''Test that we can speed up cruiseSpeed using stick left'''

        self.controller.strafeSpeed = -4
        strafeVel = self.controller._strafe(-0.5, strafeSpeed = -4)

        tangent = self.controller.azimuth - math.copysign(90,self.controller.strafeSpeed)
        expectedXVel = math.cos(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        expectedYVel = math.sin(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        degreesDelta = 360. * self.controller.strafeSpeed / (2. * math.pi * self.controller.radius) * UPDATE_TIME

        self.assertEqual(self.controller.strafeSpeed, -4 - ACCEL_PER_TICK)
        self.assertEqual(self.controller.azimuth, self.startAzimuth - degreesDelta)
        self.assertEqual(strafeVel, Vector3(expectedXVel, expectedYVel))

    def testCruiseSlowDownLeft(self):
        '''Test that we can slow down cruiseSpeed using stick right'''

        self.controller.strafeSpeed = -4
        strafeVel = self.controller._strafe(0.5, strafeSpeed = -4)

        tangent = self.controller.azimuth - math.copysign(90,self.controller.strafeSpeed)
        expectedXVel = math.cos(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        expectedYVel = math.sin(math.radians(tangent)) * abs(self.controller.strafeSpeed)
        degreesDelta = 360. * self.controller.strafeSpeed / (2. * math.pi * self.controller.radius) * UPDATE_TIME

        self.assertEqual(self.controller.strafeSpeed, -4 + ACCEL_PER_TICK)
        self.assertEqual(self.controller.azimuth, self.startAzimuth - degreesDelta)
        self.assertEqual(strafeVel, Vector3(expectedXVel, expectedYVel))


class TestClimb(unittest.TestCase):
    def setUp(self):
        roi = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startRadius = 20 # meters
        self.startAzimuth = 15 # deg
        self.startAltitude = 10 # meters

        self.startLocation = location_helpers.newLocationFromAzimuthAndDistance(roi,self.startAzimuth,self.startRadius)
        self.startLocation.alt = self.startAltitude

        #Run the controller constructor
        self.controller = orbitController.OrbitController(roi, self.startRadius, self.startAzimuth, self.startAltitude+roi.alt)

        # set options
        self.controller.setOptions(maxClimbRate=1.5 ,maxAlt=45)

    def testClimbUp(self):
        '''Test climbing up with stick up'''

        climbVel = self.controller._climb(1.0)
        self.assertEqual(self.controller.zOffset, self.startAltitude + self.controller.maxClimbRate*UPDATE_TIME)

    def testClimbDown(self):
        '''Test descending with stick down'''

        climbVel = self.controller._climb(-1.0)
        self.assertEqual(self.controller.zOffset, self.startAltitude - self.controller.maxClimbRate*UPDATE_TIME)


class TestMaxStrafeSpeed(unittest.TestCase):
    def setUp(self):
        roi = LocationGlobalRelative(37.873168,-122.302062, 0) # lat,lon,alt
        self.startRadius = 20 # meters
        self.startAzimuth = 15 # deg
        self.startAltitude = 10 # meters

        self.startLocation = location_helpers.newLocationFromAzimuthAndDistance(roi,self.startAzimuth,self.startRadius)
        self.startLocation.alt = self.startAltitude

        #Run the controller constructor
        self.controller = orbitController.OrbitController(roi, self.startRadius, self.startAzimuth, self.startAltitude)

        # set options
        self.controller.setOptions(maxClimbRate=1.5 ,maxAlt=45)

    def testBigRadius(self):
        '''Test that maxSpeed is limited to ORBIT_MAX_SPEED at a large radius'''
        
        self.controller.radius = ORBIT_RAD_FOR_MAX_SPEED + 1
        maxSpeed = self.controller._maxStrafeSpeed(self.controller.radius)
        self.assertEqual(maxSpeed, ORBIT_MAX_SPEED)

    def testSmallRadius(self):
        '''Test that maxSpeed is limited to ORBIT_MIN_SPEED at a small radius'''
        
        self.controller.radius = ORBIT_RAD_FOR_MIN_SPEED - 1
        maxSpeed = self.controller._maxStrafeSpeed(self.controller.radius)
        self.assertEqual(maxSpeed, ORBIT_MIN_SPEED)

    def testIntermediateRadius(self):
        '''Test that an intermediate maxSpeed is adhered at an intermediate radius'''

        self.controller.radius = (ORBIT_RAD_FOR_MAX_SPEED - ORBIT_RAD_FOR_MIN_SPEED) / 2.
        expectedMaxSpeed = 5.14285714286 # pre-calculated
        maxSpeed = self.controller._maxStrafeSpeed(self.controller.radius)
        self.assertAlmostEqual(maxSpeed, expectedMaxSpeed)




