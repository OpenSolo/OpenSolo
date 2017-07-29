#
#  catmullRom.py
#  shotmanager
#
#  A Catmull-Rom spline class.
#
#  Created by Will Silva on 11/22/2015.
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

from vector3 import Vector3

TOL = 1.0e-3

class CatmullRom:
    # Derivation: https://en.wikipedia.org/wiki/Centripetal_Catmull%E2%80%93Rom_spline
    # Class inspiration:
    # https://code.google.com/p/gamekernel/source/browse/kgraphics/math/CatmullRom.cpp

    def __init__(self, Pts):
        # internal point storage
        self.points = Pts

        # make sure we have enough points
        if len(Pts) < 4:
            raise ValueError(
                'Not enough points provided to generate a spline.')

        # calculate total length of the spline
        self.splineCoefficients = []
        self.arcLengths = []
        self.totalArcLength = 0.0
        for seg in range(0, len(self.points) - 3):
            self.splineCoefficients.append(self.updateSplineCoefficients(seg))
            self.arcLengths.append(self.arcLength(seg, 0, 1))

        self.totalArcLength = sum(self.arcLengths)

    def updateSplineCoefficients(self, seg):
        if seg < 0 or seg > len(self.points) - 4:
            raise ValueError(
                'Invalid segment number received (%d). Check the number of spline control points.' % seg)

        P0 = self.points[seg]
        P1 = self.points[seg + 1]
        P2 = self.points[seg + 2]
        P3 = self.points[seg + 3]

        A = 3.0 * P1 \
            - P0 \
            - 3.0 * P2 \
            + P3
        B = 2.0 * P0 \
            - 5.0 * P1 \
            + 4.0 * P2 \
            - P3
        C = P2 - P0

        return P0,P1,P2,P3,A,B,C

    def position(self, seg, u):
        '''Returns x,y,z position of spline at parameter u'''
        P0,P1,P2,P3,A,B,C = self.splineCoefficients[seg]

        return P1 + (0.5 * u) * (C + u * (B + u * A))

    def velocity(self, seg, u):
        '''Returns x,y,z velocity of spline at parameter u'''
        P0,P1,P2,P3,A,B,C = self.splineCoefficients[seg]

        return (0.5 * C + u * (B + 1.5 * u * A))

    def acceleration(self, seg, u):
        '''Returns x,y,z acceleration of spline at parameter u'''
        P0,P1,P2,P3,A,B,C = self.splineCoefficients[seg]

        return B + (3.0 * u) * A

    def curvature(self, seg, u):
        '''Returns Frenet curvature of spline at parameter u'''

        # https://en.wikipedia.org/wiki/Frenet-Serret_formulas
        vel = self.velocity(seg,u)
        return Vector3.cross(vel, self.acceleration(seg, u)).length() / (vel.length())**3

    def arcLength(self, seg, u1, u2):
        '''Calculates arc length between u1 and u2 using Gaussian Quadrature'''

        # sanitize u1,u2
        if u2 <= u1 or u1 > 1.0 or u2 < 0.0:
            return 0.0

        if u1 < 0.0:
            u1 = 0.0

        if u2 > 1.0:
            u2 = 1.0

        # Gaussian Quadrature weights and abscissae for n = 5

        abscissae = [
            0.0000000000, 0.5384693101, -0.5384693101, 0.9061798459, -0.9061798459]
        weights = [0.5688888889, 0.4786286705,
                   0.4786286705, 0.2369268850, 0.2369268850]

        # Gaussian Quadrature
        length = 0.0
        for j in range(0, 5):
            u = 0.5 * ((u2 - u1) * abscissae[j] + u2 + u1)
            length += weights[j] * self.velocity(seg, u).length()

        length *= 0.5 * (u2 - u1)

        return length

    def findParameterByDistance(self, seg, u1, s, newtonIterations = 32):
        '''Returns a parameter u that is s meters ahead of u1'''

        '''From CatmullRom.cpp: This extends the approach in the text and uses a mixture of bisection and 
            Newton-Raphson to find the root.  The result is more stable than Newton-
            Raphson alone because a) we won't end up with a situation where we divide by 
            zero in the Newton-Raphson step and b) the end result converges faster.
        
            See Numerical Recipes or http://www.essentialmath.com/blog for more details.'''

        # if desired arclength is beyond the end of the current segment then
        # just return end of segment
        if s >= self.arcLength(seg, u1, 1.0):
            return 1.0

        # can't do negative distances
        if s <= 0.0:
            return u1

        a = u1
        b = 1.0

        # make first guess
        p = u1 + s * (1 / self.arcLengths[seg])

        # iterate and look for zeros
        for i in range(0, newtonIterations):
            # compute function value and test against zero
            func = self.arcLength(seg, u1, p) - s

            # if within tolerance, return root
            if abs(func) < TOL:
                return p

            # if result less than zero then adjust lower limit
            if func < 0.0:
                a = p
            # if result greater than zero then adjust upper limit
            else:
                b = p

            # Use speed to do a bisection method (will accelerate convergence)
            # get speed along the curve
            speed = self.velocity(seg, p).length()

            # if result lies outside [a,b]
            if ((p - a) * speed - func) * ((p - b) * speed - func) > -TOL:
                # do bisection
                p = 0.5 * (a + b)
            else:
                p -= func / speed

        return float("inf")

    def arclengthToNonDimensional(self, p, dp=None):
        ''' 
                inputs:
                p - spline position reparameterized to total spline arcLength
                dp - spline velocity reparameterized to total spline arclength

                returns:
                seg - current spline segment
                u - current non-dimensional spline parameter on segment "seg"
                v - velocity along spline in meters per second
        '''

        # sanitize p
        if p > 1:
            p = 1
        elif p < 0:
            p = 0

        # calculate target arc length
        targetArcLength = p * self.totalArcLength

        # find out what segment that's in
        for seg in range(1, len(self.arcLengths) + 1):
            if sum(self.arcLengths[0:seg]) > targetArcLength:
                break
        # increment down one
        seg -= 1

        # calculate distance in that segment
        dist = targetArcLength - sum(self.arcLengths[0:seg])

        # calculate dist ahead of u = 0 on seg
        u = self.findParameterByDistance(seg, 0, dist)

        if dp is not None:
            v = dp * self.totalArcLength
            return (seg, u, v)
        else:
            return (seg, u)

    def nonDimensionalToArclength(self, seg, u, v=None):
        '''
                inputs:
                seg - current spline segment
                u - current non-dimensional spline parameter on segment "seg"
                v - velocity along spline in meters per second

                returns:
                p - spline position reparameterized to total spline arcLength
                dp - spline velocity reparameterized to total spline arcLength
        '''

        # sanitize seg
        if seg < 0:
            seg = 0
        elif seg > len(self.points) - 4:
            seg = len(self.points) - 4

        # sanitize u
        if u < 0:
            u = 0
        elif u > 1:
            u = 1

        # calculate distance along in segment
        dist = self.arcLength(seg, 0, u)

        # add all previous segment distances
        dist += sum(self.arcLengths[0:seg])

        # convert to arclength parameter
        p = dist / self.totalArcLength

        if v is not None:
            dp = v / self.totalArcLength
            return (p, dp)
        else:
            return (p,)