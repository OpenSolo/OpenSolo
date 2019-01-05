#  cableController.py
#  shotmanager
#
#  The cable movement controller.
#  Runs as a DroneKit-Python script.
#
#  Created by Jon Challinger and Will Silva on 1/21/2015.
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

from catmullRom import CatmullRom
from vector3 import *
from numpy import linspace
import math
import threading
import itertools


# epsilon to detect if we've reached a target in meters
TARGET_EPSILON_M = 0.1

# Length of each segment that is assigned a maximum speed based on its maximum curvature
CURVATURE_MAP_RES = 1. # meters

def goldenSection(func, a, b, tol = 1e-5):
    gr = 0.61803398875

    c = b - gr * (b - a)
    d = a + gr * (b - a)

    fc = func(c)
    fd = func(d)
    while abs(c-d) > tol:
        if fc < fd:
            b = d
            d = c
            c = b - gr * (b - a)
            fd = fc
            fc = func(c)
        else:
            a = c
            c = d
            d = a + gr * (b - a)
            fc = fd
            fd = func(d)

    return (b+a) / 2.

def constrain(val,minval,maxval):
    if val < minval:
        return minval
    elif val > maxval:
        return maxval
    return val


class CableController():
    def __init__(self, points, maxSpeed, minSpeed, tanAccelLim, normAccelLim, smoothStopP, maxAlt):
        # Maximum tangential acceleration along the cable, m/s^2
        self.tanAccelLim = tanAccelLim

        # Maximum acceleration normal to the cable, m/s^2
        self.normAccelLim = normAccelLim

        # Smoothness of stops at the endpoints and at targets along the cable
        self.smoothStopP = smoothStopP

        # Maximum speed along the cable, m/s
        self.maxSpeed = maxSpeed

        # Minimum speed along the cable, m/s
        self.minSpeed = minSpeed

        # Minimum allowable position.z, meters (AKA max altitude), Convert Altitude (NEU) to NED
        if maxAlt is not None:
            self.posZLimit = -maxAlt
        else:
            self.posZLimit = None
        
        # Input speed
        self.desiredSpeed = 0.

        # Current speed along the cable, m/s
        self.speed = 0.

        # Catmull-Rom spline with added virtual tangency control points at either end
        self.spline = CatmullRom([points[0]*2 - points[1]]+points+[points[-1]*2 - points[-2]])

        # Number of spline segments (should really come from CatmullRom)
        self.numSegments = len(points)-1

        # Current position in P domain, parameter normalized to cable total arc length
        self.currentP = 1.0

        # Target position in P domain
        self.targetP = self.currentP

        # Previously reached target, once set
        self.prevReachedTarget = None

        # Current segment, ranges from 0 to # of segments-1
        self.currentSeg, self.currentU = self.spline.arclengthToNonDimensional(self.currentP)

        # Current position as a Vector3, meters
        self.position = self.spline.position(self.currentSeg, self.currentU)

        # Current velocity as a Vector3, m/s
        self.velocity = Vector3()

        # Flag to indicate that the maximum altitude has been exceeded
        self.maxAltExceeded = False

        # Number of segments in curvature map
        self.curvatureMapNumSegments = int(math.ceil(self.spline.totalArcLength/CURVATURE_MAP_RES))

        # Number of joints in curvature map
        self.curvatureMapNumJoints = self.curvatureMapNumSegments+1

        # Curvature map joint positions in p domain
        self.curvatureMapJointsP, self.curvatureMapSegLengthP = linspace(0., 1., self.curvatureMapNumJoints, retstep = True)

        # Curvature map segment length in meters
        self.curvatureMapSegLengthM = self.curvatureMapSegLengthP * self.spline.totalArcLength

        # Non-dimensional curvature map joint position (cache)
        self.curvatureMapJointsNonDimensional = [None for _ in range(self.curvatureMapNumJoints)]

        # Speed limits for each curvature map segment (cache)
        self.curvatureMapSpeedLimits = [None for _ in range(self.curvatureMapNumSegments)]

        # Thread lock on curvature map segments
        self.curvatureMapLocks = [threading.Lock() for _ in range(self.curvatureMapNumSegments)]
        self.curvatureMapSegmentsComputedLock = threading.Lock()

        # number of map segments that have been computed by the curvatureMapThread
        self.curvatureMapSegmentsComputed = 0

        # flag that indicates to the thread to die
        self.poisonPill = False

        # setup a worker thread to compute map segment maximum speeds
        self.curvatureMapThread = threading.Thread(target=self._computeCurvatureMap)
        self.curvatureMapThread.setDaemon(True)

        # start the worker thread
        self.curvatureMapThread.start()

    def __del__(self):
        self.poisonPill = True
        self.curvatureMapThread.join(timeout = 2)

    # Public interface:

    def reachedTarget(self):
        '''Return True if we've reached the target, else False'''

        return abs(self.currentP - self.targetP) * self.spline.totalArcLength < TARGET_EPSILON_M

    def setTargetP(self, targetP):
        '''Interface to set a target P'''

        self.targetP = targetP

    def trackSpeed(self, speed):
        '''Updates controller desired speed'''

        self.desiredSpeed = speed

    def update(self, dt):
        '''Advances controller along cable by dt'''

        # Speed always in direction of target
        self.desiredSpeed = math.copysign(self.desiredSpeed, self.targetP - self.currentP)
        self.speed = constrain(self._constrainSpeed(self.desiredSpeed), self.speed - self.tanAccelLim*dt, self.speed + self.tanAccelLim*dt)
        self._traverse(dt)

    def setCurrentP(self,p):
        '''Sets the controller's current P position on the cable'''
        
        self.currentP = p
        self.currentSeg, self.currentU = self.spline.arclengthToNonDimensional(self.currentP)

    def killCurvatureMapThread(self):
        '''Sets poisonPill to True so the curvatureMapThread knows to die'''

        self.poisonPill = True

    # Internal functions:
    def _computeCurvatureMap(self):
        '''Computes curvature map, prioritizes map construction based on vehicle position and direction of motion'''

        while True:
            searchStart = self._getCurvatureMapSegment(self.currentP)

            if self.speed > 0:
                # Search ahead, then behind
                for i in range(searchStart, self.curvatureMapNumSegments)+list(reversed(range(0, searchStart))):
                    if self._computeCurvatureMapSpeedLimit(i):
                        break
            elif self.speed < 0:
                # Search behind, then ahead
                for i in list(reversed(range(0, searchStart+1)))+range(searchStart+1, self.curvatureMapNumSegments):
                    if self._computeCurvatureMapSpeedLimit(i):
                        break
            else: # speed == 0
                # Search alternately ahead and behind
                searchList = [x for t in list(itertools.izip_longest(range(searchStart, self.curvatureMapNumSegments), reversed(range(0, searchStart)))) for x in t if x is not None]
                for i in searchList:
                    if self._computeCurvatureMapSpeedLimit(i):
                        break
            # if all map segments have been computed then quit the thread
            with self.curvatureMapSegmentsComputedLock:
                if self.curvatureMapSegmentsComputed == self.curvatureMapNumSegments:
                    self.poisonPill = True

            if self.poisonPill:
                break

    def _computeCurvatureMapSpeedLimit(self, mapSeg):
        '''Computes speed limit for the requested map segment'''

        with self.curvatureMapLocks[mapSeg]:

            # if the speed limit has already been computed for this map segment, then don't do any work
            if self.curvatureMapSpeedLimits[mapSeg] is not None:
                return False

            # if non-dimensional parameter has not yet been created for the associated left joint, then create it
            if self.curvatureMapJointsNonDimensional[mapSeg] is None:
                self.curvatureMapJointsNonDimensional[mapSeg] = self.spline.arclengthToNonDimensional(self.curvatureMapJointsP[mapSeg])

            # if non-dimensional parameter has not yet been created for the associated right joint, then create it
            if self.curvatureMapJointsNonDimensional[mapSeg+1] is None:
                self.curvatureMapJointsNonDimensional[mapSeg+1] = self.spline.arclengthToNonDimensional(self.curvatureMapJointsP[mapSeg+1])

            # split returned non-dimensional parameter tuple (seg,u) into separate values
            seg1, u1 = self.curvatureMapJointsNonDimensional[mapSeg]
            seg2, u2 = self.curvatureMapJointsNonDimensional[mapSeg+1]

            # returns arc length for current spline segment, or the larger of the two segments if our map segment spans across multiple spline segments
            maxSegLen = max(self.spline.arcLengths[seg1:seg2+1]) # m

            # run a golden section search to find the segment,u pair for the point of maximum curvature in the requested map segment
            # (segment,u) are stored as segment+u, e.g. segment 1, u = 0.25 -> 1.25
            maxCurvatureSegU = goldenSection(lambda x: -self.spline.curvature(int(x), x-int(x)), seg1+u1, seg2+u2, tol = 1e-1/maxSegLen)

            # run a golden section search to find the segment,u pair for the point of minimum Z (aka max altitude)
            minPosZSegU = goldenSection(lambda x: self.spline.position(int(x), x-int(x)).z, seg1+u1, seg2+u2, tol = 1e-1/maxSegLen)

            # split segment+u into segment,u and evaluate curvature at this point
            maxCurvature = self.spline.curvature(int(maxCurvatureSegU),maxCurvatureSegU-int(maxCurvatureSegU))

            #split segment+u into segment,u and evalute position.z at this point
            minPosZ = self.spline.position(int(minPosZSegU),minPosZSegU-int(minPosZSegU)).z #m

            # this prevents the copter from traversing segments of the cable
            # that are above its altitude limit
            if self.posZLimit is not None and minPosZ < self.posZLimit:
                self.maxAltExceeded = True
                #this cable will breach the altitude limit, make the speed limit for this segment 0 to stop the vehicle
                self.curvatureMapSpeedLimits[mapSeg] = 0.
            else:
                if maxCurvature != 0.:
                    # limit maxspeed by the max allowable normal acceleration at that point, bounded on the lower end by minSpeed
                    self.curvatureMapSpeedLimits[mapSeg] = max(math.sqrt(self.normAccelLim / maxCurvature), self.minSpeed)
                else:
                    # if curvature is zero, means a straight segment
                    self.curvatureMapSpeedLimits[mapSeg] = self.maxSpeed

            with self.curvatureMapSegmentsComputedLock:
                self.curvatureMapSegmentsComputed += 1

            return True

    def _getCurvatureMapSpeedLimit(self, mapSeg):
        '''Look up the speed limit for the requested map segment'''

        # sanitize mapSeg
        if mapSeg < 0 or mapSeg >= self.curvatureMapNumSegments:
            return 0.

        self._computeCurvatureMapSpeedLimit(mapSeg)

        return self.curvatureMapSpeedLimits[mapSeg]

    def _traverse(self, dt):
        ''' Advances the controller along the spline '''

        spline_vel_unit = self.spline.velocity(self.currentSeg, self.currentU)
        spline_vel_norm = spline_vel_unit.normalize()

        # advances u by the amount specified by our speed and dt
        self.currentU += self.speed * dt / spline_vel_norm

        # handle traversing spline segments
        if self.currentU > 1.:
            if self.currentSeg < self.numSegments-1:
                self.currentSeg += 1
                self.currentU = 0. # NOTE: this truncates steps which cross spline joints
            else:
                self.currentU = 1.
        elif self.currentU < 0.:
            if self.currentSeg > 0:
                self.currentSeg -= 1
                self.currentU = 1. # NOTE: this truncates steps which cross spline joints
            else:
                self.currentU = 0.

        # calculate our currentP
        self.currentP = self.spline.nonDimensionalToArclength(self.currentSeg, self.currentU)[0]

        # calculate our position and velocity commands
        self.position = self.spline.position(self.currentSeg, self.currentU)
        self.velocity = spline_vel_unit * self.speed

    def _constrainSpeed(self, speed):
        '''Looks ahead and behind current controller position and constrains to a speed limit'''

        if speed > 0:
            return min(self.maxSpeed, speed, self._getPosSpeedLimit(self.currentP))
        elif speed < 0:
            return max(-self.maxSpeed, speed, self._getNegSpeedLimit(self.currentP))

        return speed

    def _speedCurve(self, dist, speed):
        '''Returns speed based on the sqrt function or a linear ramp (depending on dist)'''

        linear_velocity = self.tanAccelLim / self.smoothStopP
        linear_dist = linear_velocity / self.smoothStopP

        if speed > linear_velocity:
            return math.sqrt(2. * self.tanAccelLim * (speed**2/(2.*self.tanAccelLim) + dist))
        else:
            p1 = speed / self.smoothStopP
            p2 = p1 + dist

            if p2 > linear_dist:
                return math.sqrt(2. * self.tanAccelLim * (p2 - 0.5*linear_dist))
            else:
                return p2 * self.smoothStopP

    def _maxLookAheadDist(self):
        '''Calculate how far it would take to come to a complete stop '''

        linear_velocity = self.tanAccelLim / self.smoothStopP
        linear_dist = linear_velocity / self.smoothStopP

        if abs(self.speed) > linear_velocity:
            return 0.5 * abs(self.speed)**2 / self.tanAccelLim + 0.5*linear_dist
        else:
            return abs(self.speed)/self.smoothStopP

    def _getCurvatureMapSegment(self, p):
        '''Get the curvature map segment index at the location p'''

        return int(min(math.floor(p / self.curvatureMapSegLengthP),self.curvatureMapNumSegments-1))

    def _getDistToCurvatureMapSegmentBegin(self, p1, idx):
        '''Get distance from p1 to the beginning of the idx curvature map segment in meters'''

        p2 = self.curvatureMapJointsP[idx]
        return abs(p1-p2) * self.spline.totalArcLength

    def _getDistToCurvatureMapSegmentEnd(self, p1, idx):
        '''Get distance from p1 to the end of the idx curvature map segment in meters'''

        p2 = self.curvatureMapJointsP[idx+1]
        return abs(p1-p2) * self.spline.totalArcLength

    def _getPosSpeedLimit(self, p):
        '''Returns speed limit for a requested arc length normalized parameter, p, moving in the positive direction'''

        # Identify our current curvature map segment
        mapSeg = self._getCurvatureMapSegment(p)

        # get speed limit for the upcoming curvature map segment
        nextMapSegSpeed = self._getCurvatureMapSpeedLimit(mapSeg+1)

        # get distance (in meters) from current position to start of next curvature map segment
        nextMapSegDist = self._getDistToCurvatureMapSegmentEnd(p, mapSeg)

        # set speed limit to the minimum of the current curvature map segment and the transition to the next curvature map segment speed
        speedLimit = min(self._getCurvatureMapSpeedLimit(mapSeg), self._speedCurve(nextMapSegDist, nextMapSegSpeed)) # m/s

        # loop through all remaining segments in that direction
        for mapSeg in range(mapSeg+1,self.curvatureMapNumSegments):
            # increment distance by another curvature map segment length
            nextMapSegDist += self.curvatureMapSegLengthM

            # if that distance is greater than the distance it would take to stop, then break to save time (no need to look ahead any further)
            if nextMapSegDist > self._maxLookAheadDist():
                break

            # get curvature map seg speed at this next segment
            nextMapSegSpeed = self._getCurvatureMapSpeedLimit(mapSeg+1) # NOTE: self.getCurvatureMapSpeedLimit(self.curvatureMapNumSegments) is 0

            # limit us if the new map segment speed is slower than our current speed limit
            speedLimit = min(speedLimit, self._speedCurve(nextMapSegDist, nextMapSegSpeed))

        # if targetP is ahead of currentP then check for a speed limit to slow down at the target
        if self.targetP >= self.currentP:
            speedLimit = min(speedLimit, self._speedCurve(abs(self.targetP - self.currentP)*self.spline.totalArcLength, 0))

        return speedLimit

    def _getNegSpeedLimit(self, p):
        '''Returns speed limit for a requested arc length normalized parameter, p, moving in the negative direction'''

        # Identify our current curvature map segment
        mapSeg = self._getCurvatureMapSegment(p)

        # get speed limit for the previous curvature map segment
        prevMapSegSpeed = self._getCurvatureMapSpeedLimit(mapSeg-1)

        # get distance (in meters) from current position to start of previous curvature map segment
        prevMapSegDist = self._getDistToCurvatureMapSegmentBegin(p, mapSeg)

        # set speed limit to the minimum of the current curvature map segment and the transition to the previous curvature map segment speed
        speedLimit = min(self._getCurvatureMapSpeedLimit(mapSeg), self._speedCurve(prevMapSegDist, prevMapSegSpeed)) # m/s

        # loop through all remaining segments in that direction
        for mapSeg in reversed(range(0,mapSeg)):
            # increment distance by another curvature map segment length
            prevMapSegDist += self.curvatureMapSegLengthM

            # if that distance is greater than the distance it would take to stop, then break to save time (no need to look ahead any further)
            if prevMapSegDist > self._maxLookAheadDist():
                break

            # get curvature map seg speed at this previous segment
            prevMapSegSpeed = self._getCurvatureMapSpeedLimit(mapSeg-1) # NOTE: self.getCurvatureMapSpeedLimit(-1) is 0

            # limit us if the new map segment speed is slower than our current speed limit
            speedLimit = min(speedLimit, self._speedCurve(prevMapSegDist, prevMapSegSpeed))

        if self.targetP <= self.currentP:
            speedLimit = min(speedLimit, self._speedCurve(abs(self.targetP - self.currentP)*self.spline.totalArcLength, 0))

        return -speedLimit