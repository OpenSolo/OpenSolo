#  TestCableController.py
#  shotmanager
#
#  Unit tests for the cable controller.
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

import cableController
from cableController import *

import multipoint
from multipoint import *

from dronekit import LocationGlobalRelative

import unittest

import mock
from mock import call
from mock import Mock
from mock import MagicMock
from mock import patch


class TestPublicInterface(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread()
        self.controller.curvatureMapThread.join()

    def testReachedTarget(self):
        '''Tests that reachedTarget works'''

        retVal = self.controller.reachedTarget()
        self.assertEqual(retVal, True)

    def testSetTargetP(self):
        '''Test that setTargetP works'''

        self.controller.setTargetP(.3)
        self.assertEqual(self.controller.targetP, .3)

    def testTrackSpeed(self):
        '''Test that trackSpeed works'''

        self.controller.trackSpeed(4)
        self.assertEqual(self.controller.desiredSpeed, 4)

    @mock.patch('cableController.constrain', return_value = 3)
    def testUpdate(self, constrain):
        '''Test that update works'''

        #Mock _traverse
        self.controller._traverse = Mock()

        self.controller.update(UPDATE_TIME)
        self.assertEqual(self.controller.desiredSpeed, 0)
        self.assertEqual(self.controller.speed, 3)
        self.controller._traverse.assert_called_with(UPDATE_TIME)

    def testSetCurrentP(self):
        '''Test that setCurrentP works'''

        self.controller.setCurrentP(0.3)
        self.assertEqual(self.controller.currentP, 0.3)

    def testKillCurvatureMapThread(self):
        '''Test that poisonPill is set to True'''

        self.controller.killCurvatureMapThread()
        self.assertEqual(self.controller.poisonPill, True)

class Test_computeCurvatureMap(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die
        self.controller.curvatureMapSpeedLimits[0] = None

    def testPositiveSpeed(self):
        '''Test when self.speed is positive'''

        self.controller.speed = 3
        self.controller._computeCurvatureMapSpeedLimit = Mock(side_effect=[False,False,True])
        self.controller.poisonPill = True
        self.controller._computeCurvatureMap()

    def testNegativeSpeed(self):
        '''Test when self.speed is negative'''

        self.controller.speed = -3
        self.controller._computeCurvatureMapSpeedLimit = Mock(side_effect=[False,False,True])
        self.controller.poisonPill = True
        self.controller._computeCurvatureMap()

    def testZeroSpeed(self):
        '''Test when self.speed is zero'''

        self.controller.speed = 0
        self.controller._computeCurvatureMapSpeedLimit = Mock(side_effect=[False,False,True])
        self.controller.poisonPill = True
        self.controller._computeCurvatureMap()

class Test_computeCurvatureMapSpeedLimit(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die
        self.controller.curvatureMapSpeedLimits[0] = None

    def testSpeedLimitNotNone(self):
        '''Test when speed limit is already computed'''

        self.controller.curvatureMapSpeedLimits[0] = 3
        retVal = self.controller._computeCurvatureMapSpeedLimit(0)
        self.assertEqual(retVal, False)

    def testCurrentMapSegJointIsNone(self):
        '''Test when non dimensional index for the joint has not been computed yet'''

        self.controller.curvatureMapJointsNonDimensional[0] = None
        self.controller._computeCurvatureMapSpeedLimit(0)
        assert self.controller.curvatureMapJointsNonDimensional[0] is not None

    def testCurrentMapSegJointPlusOneIsNone(self):
        '''Test when non dimensional index for the joint has not been computed yet'''

        self.controller.curvatureMapJointsNonDimensional[1] = None
        self.controller._computeCurvatureMapSpeedLimit(0)
        assert self.controller.curvatureMapJointsNonDimensional[1] is not None

    def testAltitudeLimit(self):
        '''Tests that altitude limit breach sets maxAltExceeded flag'''

        self.controller.posZLimit = 10 # meters
        self.controller.spline.position = Mock(return_value = Vector3(0,0,-11)) # meters
        self.controller._computeCurvatureMapSpeedLimit(0)
        self.assertEqual(self.controller.maxAltExceeded, True)

    def testAltitudeLimitDisabled(self):
        '''Tests that altitude limit breach does not set maxAltExceeded flag if altitude limit is disabled'''

        self.controller.posZLimit = None
        self.controller.spline.position = Mock(return_value = Vector3(0,0,-11)) # meters
        self.controller._computeCurvatureMapSpeedLimit(0)
        self.assertEqual(self.controller.maxAltExceeded, False)


    def testNonZeroMaxCurvature(self):
        '''Test that a speed limit is calculated based on non-zero curvature'''

        self.controller.spline.curvature = Mock(return_value = 3.)
        self.controller._computeCurvatureMapSpeedLimit(0)
        self.assertEqual(self.controller.curvatureMapSpeedLimits[0], math.sqrt(NORM_ACCEL_LIMIT/3.))

    def testMinSpeedLimit(self):
        '''Test that a speed limit is capped at minimum for high curvature'''

        self.controller.spline.curvature = Mock(return_value = 300.)
        self.controller._computeCurvatureMapSpeedLimit(0)
        self.assertEqual(self.controller.curvatureMapSpeedLimits[0], MIN_CRUISE_SPEED)

    def testZeroCurvature(self):
        '''Test that speed limit is set to MAX_SPEED if max curvature is zero'''

        self.controller.spline.curvature = Mock(return_value = 0.)
        self.controller._computeCurvatureMapSpeedLimit(0)
        self.assertEqual(self.controller.curvatureMapSpeedLimits[0], MAX_SPEED)


class Test_getCurvatureMapSpeedLimit(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die

    def testSegmentLessThanZero(self):
        '''Test that 0. is returned if segment requested is less than zero'''

        retVal = self.controller._getCurvatureMapSpeedLimit(-1)
        self.assertEqual(retVal, 0.)

    def testSegmentGreaterThanNumOfSegments(self):
        '''Test that 0. is returned if segment requested is greater than available number of map segments'''

        self.controller.curvatureMapNumSegments = 3
        retVal = self.controller._getCurvatureMapSpeedLimit(4)
        self.assertEqual(retVal, 0.)

class Test_traverse(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die

    def testCurrentUGreaterThanOneNotLastSegment(self):
        '''Test that we advance segments if currentU is greater than 1 and it's not the last segment'''

        self.controller.currentSeg = 0
        self.controller.currentU = 1.0
        self.controller.speed = MAX_SPEED
        self.controller._traverse(UPDATE_TIME)
        self.assertEqual(self.controller.currentSeg, 1)
        self.assertEqual(self.controller.currentU , 0.)

    def testCurrentUGreaterThanOneLastSegment(self):
        '''Test that we do NOT advance segments if currentU is greater than 1 and it IS the last segment'''

        self.controller.currentSeg = 2
        self.controller.currentU = 1.0
        self.controller.speed = MAX_SPEED
        self.controller._traverse(UPDATE_TIME)
        self.assertEqual(self.controller.currentSeg, 2)
        self.assertEqual(self.controller.currentU , 1.)

    def testCurrentULessThanZeroNotFirstSegment(self):
        '''Test that we regress segments if currentU is less than 0 and it's not the first segment'''

        self.controller.currentSeg = 2
        self.controller.currentU = 0.0
        self.controller.speed = -MAX_SPEED
        self.controller._traverse(UPDATE_TIME)
        self.assertEqual(self.controller.currentSeg, 1)
        self.assertEqual(self.controller.currentU , 1.)

    def testCurrentULessThanZeroFirstSegment(self):
        '''Test that we do NOT regress segments if currentU is less than 0 and it IS the first segment'''

        self.controller.currentSeg = 0
        self.controller.currentU = 0.0
        self.controller.speed = -MAX_SPEED
        self.controller._traverse(UPDATE_TIME)
        self.assertEqual(self.controller.currentSeg, 0)
        self.assertEqual(self.controller.currentU , 0.)


class Test_constrainSpeed(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die

    def testMaxSpeedGreaterThanSpeedLimitGreaterThanSpeedGreaterThanZero(self):
        '''Test when 0 < speed < speed limit < max speed'''

        self.controller._getPosSpeedLimit = Mock(return_value = 6.)
        retVal = self.controller._constrainSpeed(4.)
        self.assertEqual(retVal, 4.)

    def testMaxSpeedGreaterThanSpeedGreaterThanSpeedLimitGreaterThanZero(self):
        '''Test when 0 < speed limit < speed < max speed'''

        self.controller._getPosSpeedLimit = Mock(return_value = 3.)
        retVal = self.controller._constrainSpeed(4.)
        self.assertEqual(retVal, 3.)

    def testSpeedGreaterThanMaxSpeedGreaterThanSpeedLimitGreaterThanZero(self):
        '''Test when 0 < speed limit < max speed < speed'''

        self.controller._getPosSpeedLimit = Mock(return_value = 3.)
        retVal = self.controller._constrainSpeed(9.)
        self.assertEqual(retVal, 3.)

    def testSpeedGreaterThanSpeedLimitGreaterThanMaxSpeedGreaterThanZero(self):
        '''Test when 0 < max speed < speed limit < speed'''

        self.controller._getPosSpeedLimit = Mock(return_value = 10.)
        retVal = self.controller._constrainSpeed(9.)
        self.assertEqual(retVal, MAX_SPEED)

    def testSpeedLessThanSpeedLimitLessThanMaxSpeedLessThanZero(self):
        '''Test when speed < speed limit < max speed < 0'''

        self.controller._getNegSpeedLimit = Mock(return_value = -9.)
        retVal = self.controller._constrainSpeed(-10.)
        self.assertEqual(retVal, -MAX_SPEED)

    def testSpeedLimitLessThanSpeedLessThanMaxSpeedLessThanZero(self):
        '''Test when speed limit < speed < max speed < 0'''

        self.controller._getNegSpeedLimit = Mock(return_value = -9.)
        retVal = self.controller._constrainSpeed(-8.5)
        self.assertEqual(retVal, -MAX_SPEED)

    def testSpeedLimitLessThanMaxSpeedLessThanSpeedLessThanZero(self):
        '''Test when speed limit < max speed < speed < 0'''

        self.controller._getNegSpeedLimit = Mock(return_value = -9.)
        retVal = self.controller._constrainSpeed(-4.)
        self.assertEqual(retVal, -4.)

    def testMaxSpeedLessThanSpeedLessThanSpeedLimitLessThanZero(self):
        '''Test when max speed < speed < speedLimit < 0'''

        self.controller._getNegSpeedLimit = Mock(return_value = -4.)
        retVal = self.controller._constrainSpeed(-5.)
        self.assertEqual(retVal, -4.)


class Test_speedCurve(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        self.smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, self.smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die

    def testSpeedGreaterThanLinearVelocity(self):
        '''Test that if speed is greater than linear_velocity then return sqrt curve speed profile'''

        lVelocity = TANGENT_ACCEL_LIMIT / self.smoothStopP
        lDist = lVelocity / self.smoothStopP
        speed = lVelocity + 1 #m/s

        dist = 10 #meters

        expectedVal = math.sqrt(2. * TANGENT_ACCEL_LIMIT * (speed**2/(2.*TANGENT_ACCEL_LIMIT) + dist))
        retVal = self.controller._speedCurve(dist, speed)
        self.assertEqual(retVal, expectedVal)

    def testSpeedLessThanLinearVelocityAndP2GreaterThanLinearDist(self):
        '''Test that if speed is less than linear_velocity and P2 is greater than linear distance then return linear speed profile'''

        lVelocity = TANGENT_ACCEL_LIMIT / self.smoothStopP
        lDist = lVelocity / self.smoothStopP
        speed = lVelocity - 1 #m/s
        p1 = speed / self.smoothStopP
        p2 = lDist + 1
        dist = p2 - p1 # meters
        expectedVal = math.sqrt(2. * TANGENT_ACCEL_LIMIT * (p2 - 0.5*lDist))
        retVal = self.controller._speedCurve(dist, speed)
        self.assertEqual(retVal, expectedVal)

    def testSpeedLessThanLinearVelocityAndP2LessThanLinearDist(self):
        '''Test that if speed is less than linear_velocity and P2 is less than linear distance then return linear speed profile'''

        lVelocity = TANGENT_ACCEL_LIMIT / self.smoothStopP
        lDist = lVelocity / self.smoothStopP
        speed = lVelocity - 1 #m/s
        p1 = speed / self.smoothStopP
        p2 = lDist - 1
        dist = p2 - p1 # meters
        expectedVal = p2 * self.smoothStopP
        retVal = self.controller._speedCurve(dist, speed)
        self.assertEqual(retVal, expectedVal)


class Test_maxLookAheadDist(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        self.smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, self.smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die

    def testAbsSpeedGreaterThanLinearVelocity(self):
        '''Test if absolute value of speed is greater than linear velocity then return distance required to stop at constant deceleration'''

        lVelocity = TANGENT_ACCEL_LIMIT / self.smoothStopP
        lDist = lVelocity / self.smoothStopP
        self.controller.speed = lVelocity + 1
        retVal = self.controller._maxLookAheadDist()
        self.assertEqual(retVal, 0.5 * abs(self.controller.speed)**2 / TANGENT_ACCEL_LIMIT + 0.5*lDist)

    def testAbsSpeedLessThanLinearVelocity(self):
        '''Test if absolute value of speed is less than linear velocity then return distance required to stop at constant deceleration'''

        lVelocity = TANGENT_ACCEL_LIMIT / self.smoothStopP
        lDist = lVelocity / self.smoothStopP
        self.controller.speed = lVelocity - 1
        retVal = self.controller._maxLookAheadDist()
        self.assertEqual(retVal, abs(self.controller.speed)/self.smoothStopP)


class Test_getCurvatureMapSegment(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die

    def testPIsOneHalf(self):
        '''Test if P = 0.5 for 100 segment map'''

        self.controller.curvatureMapNumSegments = 100 # segments
        self.controller.curvatureMapSegLengthP = 1./100 # p per map segment
        retVal = self.controller._getCurvatureMapSegment(0.5)
        self.assertEqual(retVal,50)


class Test_getDistToCurvatureMapSegmentBegin(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die

    def testP1IsOneHalf(self):
        '''Test if P1 = 0.5, P2 = 0.6, 100 meter cable'''

        self.controller.spline.totalArcLength = 100 #meters
        self.controller.curvatureMapJointsP[2] = 0.6 #p
        retVal = self.controller._getDistToCurvatureMapSegmentBegin(0.5, 2)
        self.assertAlmostEqual(retVal, 10)


class Test_getDistToCurvatureMapSegmentEnd(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die

    def testP1IsOneHalf(self):
        '''Test if P1 = 0.5, P2 = 0.4, 100 meter cable'''

        self.controller.spline.totalArcLength = 100 #meters
        self.controller.curvatureMapJointsP[2] = 0.4 #p
        retVal = self.controller._getDistToCurvatureMapSegmentBegin(0.5, 2)
        self.assertAlmostEqual(retVal, 10)


class Test_getPosSpeedLimit(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die

    def testTargetPGreaterThanCurrentP(self):
        '''Test if targetP is greater than currentP then speedLimit is compared with map segment speedlimit and speedCurve'''

        self.controller.targetP = .5
        self.controller.currentP = .3
        self.controller._speedCurve = Mock(side_effect = [2.,1.])
        retVal = self.controller._getPosSpeedLimit(self.controller.currentP)
        self.assertEqual(retVal, 1.)


class Test_getNegSpeedLimit(unittest.TestCase):
    def setUp(self):
        points = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)]
        maxSpeed = MAX_SPEED
        minSpeed = MIN_CRUISE_SPEED
        tanAccelLim = TANGENT_ACCEL_LIMIT
        normAccelLim = NORM_ACCEL_LIMIT 
        smoothStopP = 0.7
        maxAlt = 50
        self.controller = cableController.CableController(points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt)
        self.controller.killCurvatureMapThread() #send thread poison pill
        self.controller.curvatureMapThread.join() #wait for thread to die

    def testTargetPLessThanCurrentP(self):
        '''Test if targetP is less than currentP then speedLimit is compared with map segment speedlimit and speedCurve'''

        self.controller.targetP = .3
        self.controller.currentP = .5
        self.controller._speedCurve = Mock(side_effect = [2.,1.])
        retVal = self.controller._getNegSpeedLimit(self.controller.currentP)
        self.assertEqual(retVal, -1.)





























