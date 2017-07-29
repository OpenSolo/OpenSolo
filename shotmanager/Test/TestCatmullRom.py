#  TestCatmullRom.py
#  shotmanager
#
#  Unit tests for the CatmullRom class in catmullRom.py
#
#  Created by Will Silva on 11/22/2015.
#  Copyright (c) 2015 3D Robotics.
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

import unittest
from catmullRom import CatmullRom
from vector3 import Vector3


class TestConstructor(unittest.TestCase):

    def testMinNumofPoints2(self):
        '''Tests that catmull raises an exception if less than one waypoint is passed to it'''
        Pts = [Vector3(0.0, 0.0, 0.0)] * 3
        self.assertRaises(ValueError, CatmullRom, Pts)


class TestCatmullRom(unittest.TestCase):

    def setUp(self):
        self.spline = CatmullRom(
            [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)])

    def testUpdateSplineCoefficientsError(self):
        '''Tests that an error is raised if we call updateSplineCoefficients with an out of range segment'''
        self.assertRaises(ValueError, self.spline.updateSplineCoefficients, 3)

    def testPosition(self):
        '''For an evenly spaced straight-line spline, test that position is traversed'''
        seg = 0
        u = 0
        q = self.spline.position(seg, u)
        self.assertEqual(q, Vector3(1.0, 0.0, 0.0))
        u = 0.5
        q = self.spline.position(seg, u)
        self.assertEqual(q, Vector3(1.5, 0.0, 0.0))
        u = 1.0
        q = self.spline.position(seg, u)
        self.assertEqual(q, Vector3(2.0, 0.0, 0.0))

    def testVelocity(self):
        '''For an evenly spaced straight-line spline, test that velocity is constant'''
        seg = 0
        u = 0
        dq = self.spline.velocity(seg, u)
        self.assertEqual(dq, Vector3(1.0, 0.0, 0.0))
        u = 0.5
        dq = self.spline.velocity(seg, u)
        self.assertEqual(dq, Vector3(1.0, 0.0, 0.0))
        u = 1.0
        dq = self.spline.velocity(seg, u)
        self.assertEqual(dq, Vector3(1.0, 0.0, 0.0))

    def testAcceleration(self):
        '''For an evenly spaced straight-line spline, test that acceleration is zero'''
        seg = 0
        u = 0
        ddq = self.spline.acceleration(seg, u)
        self.assertEqual(ddq, Vector3(0.0, 0.0, 0.0))
        u = 0.5
        ddq = self.spline.acceleration(seg, u)
        self.assertEqual(ddq, Vector3(0.0, 0.0, 0.0))
        u = 1.0
        ddq = self.spline.acceleration(seg, u)
        self.assertEqual(ddq, Vector3(0.0, 0.0, 0.0))

    def testCurvature(self):
        '''For an evenly spaced straight-line spline, test that curvature is zero'''
        seg = 0
        u = 0
        curv = self.spline.curvature(seg, u)
        self.assertEqual(curv, 0.0)
        u = 0.5
        curv = self.spline.curvature(seg, u)
        self.assertEqual(curv, 0.0)
        u = 1.0
        curv = self.spline.curvature(seg, u)
        self.assertEqual(curv, 0.0)


class TestArcLength(unittest.TestCase):

    def setUp(self):
        self.spline = CatmullRom(
            [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)])

    def testStandardInput(self):
        '''Calculate arc length of the segment and verify that it's close to 1 (within 7 decimal places)'''
        seg = 0
        u1 = 0
        u2 = 1
        length = self.spline.arcLength(seg, u1, u2)
        self.assertAlmostEqual(1, length, 7)

    def testU2LessU1(self):
        '''Tests case where u2 < u1'''
        seg = 0
        u2 = 0.5
        u1 = 0.75
        length = self.spline.arcLength(seg, u1, u2)
        self.assertEqual(0, length)

    def testU1OutOfBounds(self):
        '''Test when u1 is not between 0-1'''
        seg = 0
        u1 = -0.2
        u2 = 0.5
        length = self.spline.arcLength(seg, u1, u2)
        self.assertAlmostEqual(0.5, length)

    def testU2OutOfBounds(self):
        '''Test when u2 is not between 0-1'''
        seg = 0
        u1 = 0.5
        u2 = 1.5
        length = self.spline.arcLength(seg, u1, u2)
        self.assertAlmostEqual(0.5, length)

    def testU1andU2OutOfBounds(self):
        '''Test when u1 and u2 are not between 0-1'''
        seg = 0
        u1 = 1.1
        u2 = 1.2
        length = self.spline.arcLength(seg, u1, u2)
        self.assertAlmostEqual(0, length)

        u1 = -0.7
        u2 = -0.5
        length = self.spline.arcLength(seg, u1, u2)
        self.assertAlmostEqual(0, length)

    def testAgainstBruteForceIntegration(self):
        '''Make sure our numerical integrator is doing a decent job at estimating arc length'''

        self.spline = CatmullRom(
            [Vector3(0, 0, 0), Vector3(1, 5, 0), Vector3(2, -3, 0), Vector3(3, 0, 0)])
        seg = 0
        u1 = 0
        u2 = 1
        gaussResult = self.spline.arcLength(seg, u1, u2)

        # Let's use Brute Force
        n = 1000
        dt = 1.0 / n
        L = 0
        t = 0
        for i in range(0, n):
            L += self.spline.velocity(seg, t).length() * dt
            t += dt

        # within a millimeter
        self.assertAlmostEqual(gaussResult, L, 3)


class TestParameterByDistance(unittest.TestCase):

    def setUp(self):
        self.spline = CatmullRom(
            [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)])

    def testStandardInput(self):
        '''Calculate parameter u that is s meters ahead of u1 (within 7 decimal places'''
        seg = 0
        u1 = 0.25
        s = 0.25  # meters
        uLive = self.spline.findParameterByDistance(seg, u1, s)
        # test with 300 newton iterations
        uAccurate = self.spline.findParameterByDistance(seg, u1, s, 300)
        self.assertAlmostEqual(uLive, uAccurate, 7)

    def testSTooLong(self):
        '''Test when s (in meters) extends beyond the segment'''
        seg = 0
        u1 = 0.5
        s = 0.75
        u = self.spline.findParameterByDistance(seg, u1, s)
        self.assertEqual(1.0, u)

    def testSNegative(self):
        '''Test when s is negative (doesn't make sense for this algorithm)'''
        seg = 0
        u1 = 0.5
        s = -0.75
        u = self.spline.findParameterByDistance(seg, u1, s)
        self.assertEqual(u1, u)


class TestArclengthToNonDimensional(unittest.TestCase):

    def setUp(self):
        # 1 meter long spline
        self.spline = CatmullRom(
            [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)])

    def testPTooBig(self):
        '''Test when p is not between 0-1'''
        p = 1.5  # should default to 1.0
        dp = .1  # should be .1 m/s
        seg, u, v = self.spline.arclengthToNonDimensional(p, dp)
        self.assertEqual(seg, 0)
        self.assertEqual(u, 1.0)
        self.assertAlmostEqual(v, 0.1)

    def testPTooSmall(self):
        '''Test when p is not between 0-1'''
        p = -1.5  # should default to 0
        dp = .1  # should be .1 m/s
        seg, u, v = self.spline.arclengthToNonDimensional(p, dp)
        self.assertEqual(seg, 0)
        self.assertEqual(u, 0)
        self.assertAlmostEqual(v, 0.1)

    def testConversionFromArclength(self):
        '''Test conversion in an ideal 1 meter spline'''
        p = 0.5  # should be halfway through spline distance (0.5 meters)
        dp = .1  # should be .1 m/s
        seg, u, v = self.spline.arclengthToNonDimensional(p, dp)
        self.assertEqual(seg, 0)
        self.assertEqual(u, 0.5)
        self.assertAlmostEqual(v, 0.1)

    def testConversionFromArclength2Seg(self):
        '''Test conversion on a 2 segment spline'''
        self.spline = CatmullRom([Vector3(0, 0, 0), Vector3(
            1, 0, 0), Vector3(2, 0, 0), Vector3(4, 0, 0), Vector3(5, 0, 0)])
        # x x-x--x x
        p = 0.5  # should be halfway through spline distance (1.5 meters)
        dp = .1
        seg, u, v = self.spline.arclengthToNonDimensional(p, dp)
        self.assertEqual(seg, 1)
        self.assertAlmostEqual(u, 0.27272727)
        self.assertAlmostEqual(v, 0.3)


class TestNonDimensionalToArclength(unittest.TestCase):

    def setUp(self):
        # 1 meter long spline
        self.spline = CatmullRom(
            [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(2, 0, 0), Vector3(3, 0, 0)])

    def testSegTooBig(self):
        '''Test when segment doesn't exist (too high)'''
        seg = 1  # for a 4 point spline, we only have 1 segment with index 0 x  x----x   x
        u = 0.5
        v = 1
        p, dp = self.spline.nonDimensionalToArclength(seg, u, v)
        self.assertEqual(p, 0.5)
        self.assertAlmostEqual(dp, 1.0)

    def testSegTooSmall(self):
        '''Test when segment doesn't exist (no negative segments allowed)'''
        seg = - \
            1  # for a 4 point spline, we only have 1 segment with index 0 x  x----x   x
        u = 0.5
        v = 1
        p, dp = self.spline.nonDimensionalToArclength(seg, u, v)
        self.assertEqual(p, 0.5)
        self.assertAlmostEqual(dp, 1.0)

    def testUTooBig(self):
        '''Test when U is not between 0-1'''
        seg = 0
        u = 1.5
        v = 1
        p, dp = self.spline.nonDimensionalToArclength(seg, u, v)
        self.assertEqual(p, 1.0)
        self.assertAlmostEqual(dp, 1.0)

    def testUTooSmall(self):
        '''Test when U is not between 0-1'''
        seg = 0
        u = -1
        v = 1
        p, dp = self.spline.nonDimensionalToArclength(seg, u, v)
        self.assertEqual(p, 0.0)
        self.assertAlmostEqual(dp, 1.0)

    def testConversionFromNonDimensional(self):
        '''Test conversion on an ideal 1 meter spline'''
        seg = 0
        u = .75
        v = 2
        p, dp = self.spline.nonDimensionalToArclength(seg, u, v)
        self.assertEqual(p, 0.75)
        self.assertAlmostEqual(dp, 2.0)

    def testConversionFromNonDimensional2Seg(self):
        '''Test conversion on a 2 segment spline'''
        self.spline = CatmullRom([Vector3(0, 0, 0), Vector3(
            1, 0, 0), Vector3(2, 0, 0), Vector3(4, 0, 0), Vector3(5, 0, 0)])
        # x x-x--x x
        seg = 1
        u = .5
        v = 2
        p, dp = self.spline.nonDimensionalToArclength(seg, u, v)
        self.assertAlmostEqual(p, 0.66666666)
        self.assertAlmostEqual(dp, 0.66666666)
