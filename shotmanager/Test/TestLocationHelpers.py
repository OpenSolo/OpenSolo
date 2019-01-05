# Unit tests for location_helpers
import math
import mock
import os
from os import sys, path
import unittest

from dronekit import LocationGlobalRelative
sys.path.append(os.path.realpath('..'))
import location_helpers
from vector3 import Vector3

# for distances and angles
ERROR = 0.1
# for lat and lon errors
ERROR_LOC = 0.000001

class TestDistanceFromPoints(unittest.TestCase):
    def testZeroDist(self):
        """ These points should be zero distance apart """
        loc = LocationGlobalRelative(-36.37485, 24.23846, 32.6545)
        self.assertTrue( abs( location_helpers.getDistanceFromPoints(loc, loc) ) < ERROR )
        loc = LocationGlobalRelative(72.4564, 26.23422, 0.0)
        self.assertTrue( abs( location_helpers.getDistanceFromPoints(loc, loc) ) < ERROR )
        loc = LocationGlobalRelative(-75.23453, -12.21835, 14.234873)
        self.assertTrue( abs( location_helpers.getDistanceFromPoints(loc, loc) ) < ERROR )

    def testLargeDist(self):
        """ These points are a known distance apart """
        loc = LocationGlobalRelative(50.2356, 5.2835723)
        loc2 = LocationGlobalRelative(50.7837, 3.444)
        dist = location_helpers.getDistanceFromPoints(loc, loc2)
        # Google Earth Pro Answer: 144022
        delta = abs( dist - 144336 )
        self.assertTrue( delta < ERROR )

    def testSmallDist(self):
        """ These points are a known distance apart """
        loc = LocationGlobalRelative(-45.23462, -22.2384)
        loc2 = LocationGlobalRelative(-45.2673, -22.123512)
        dist = location_helpers.getDistanceFromPoints(loc, loc2)
        # Google Earth Pro Answer: 9724
        delta = abs( dist - 9702.4 )
        self.assertTrue( delta < ERROR )

class TestDistanceFromPoints3d(unittest.TestCase):
    def test3dDistAltDiff(self):
        """ Only difference between these points is altitude """
        alt1 = 17.23463
        alt2 = 40.4564
        loc = LocationGlobalRelative(83.234632, -42.823752, alt1)
        loc2 = LocationGlobalRelative(83.234632, -42.823752, alt2)
        diff = alt2 - alt1
        dist = location_helpers.getDistanceFromPoints3d( loc, loc2 )
        delta = diff - dist
        self.assertTrue( abs( delta ) < ERROR )

    def testSomeKnown3dDist(self):
        """ Known 3d distance apart """
        alt1 = 64.234
        alt2 = 12.2345
        loc = LocationGlobalRelative(83.45234, 9.3452346, alt1)
        loc2 = LocationGlobalRelative(83.4523, 9.3452344, alt2)
        dist = location_helpers.getDistanceFromPoints3d( loc, loc2 )
        delta = dist - 52.1
        self.assertTrue( abs( delta ) < ERROR )

class TestNewLocationFromAzimuthAndDistance(unittest.TestCase):
    def testFirstLocation(self):
        """ Test that newLocationFromAzimuthAndDistance works """
        az = 17.234
        dist = 45.23643
        loc = LocationGlobalRelative(-43.2346234, 15.2385, 0.0)
        newloc = location_helpers.newLocationFromAzimuthAndDistance(loc, az, dist)
        calcDist = location_helpers.getDistanceFromPoints3d( loc, newloc )
        self.assertTrue( abs( dist - calcDist ) < ERROR )
        calcAz = location_helpers.calcAzimuthFromPoints( loc, newloc )
        self.assertTrue( abs( az - calcAz ) < ERROR )

    def testSecondLocation(self):
        """ Test that newLocationFromAzimuthAndDistance works """
        az = 84.546
        dist = 37.5464
        loc = LocationGlobalRelative(-22.65465, 4.351654, 0.0)
        newloc = location_helpers.newLocationFromAzimuthAndDistance(loc, az, dist)
        calcDist = location_helpers.getDistanceFromPoints3d( loc, newloc )
        self.assertTrue( abs( dist - calcDist ) < ERROR )
        calcAz = location_helpers.calcAzimuthFromPoints( loc, newloc )
        self.assertTrue( abs( az - calcAz ) < ERROR )

class TestCalcAzimuthFromPoints(unittest.TestCase):
    def testNorth(self):
        """ Test that calcAzimuthFromPoints knows when a point is north of another """
        loc = LocationGlobalRelative(-63.2346234, 15.2385)
        loc2 = LocationGlobalRelative(-33.2346234, 15.2385)
        az = location_helpers.calcAzimuthFromPoints(loc, loc2)
        self.assertTrue( abs( az ) < ERROR )

    def testSouth(self):
        """ Test that calcAzimuthFromPoints knows when a point is south of another """
        loc = LocationGlobalRelative(63.2346234, 32.3546)
        loc2 = LocationGlobalRelative(33.2346234, 32.3546)
        az = location_helpers.calcAzimuthFromPoints(loc, loc2)
        self.assertTrue( abs( az - 180.0 ) < ERROR )

    def testEast(self):
        """ Test that calcAzimuthFromPoints knows when a point is east of another """
        loc = LocationGlobalRelative(12.6465, 50.46845)
        loc2 = LocationGlobalRelative(12.6465, 50.55464)
        az = location_helpers.calcAzimuthFromPoints(loc, loc2)
        self.assertTrue( abs( az - 90.0 ) < ERROR )

    def testWest(self):
        """ Test that calcAzimuthFromPoints knows when a point is west of another """
        loc = LocationGlobalRelative(22.35465, 120.6546)
        loc2 = LocationGlobalRelative(22.35465, 120.5465)
        az = location_helpers.calcAzimuthFromPoints(loc, loc2)
        self.assertTrue( abs( az - 270.0 ) < ERROR )

    def testKnownAz(self):
        """ Test that calcAzimuthFromPoints correctly calculates a known azimuth """
        loc = LocationGlobalRelative(83.4523, 9.34521)
        loc2 = LocationGlobalRelative(83.45233, 9.34524)
        az = location_helpers.calcAzimuthFromPoints(loc, loc2)
        self.assertTrue( abs( az - 6.5 ) < ERROR )

    def testKnownAz2(self):
        """ Test2 that calcAzimuthFromPoints correctly calculates a known azimuth """
        loc = LocationGlobalRelative(83.5, 9.2)
        loc2 = LocationGlobalRelative(83.51, 9.21)
        az = location_helpers.calcAzimuthFromPoints(loc, loc2)
        self.assertTrue( abs( az - 6.458 ) < ERROR )
 
class TestGetVectorFromPoints(unittest.TestCase):
    def testAltUp(self):
        """ Test a vector straight up """
        alt1 = 30.28374
        alt2 = 11.234865
        loc = LocationGlobalRelative(23.5445, -12.3333, alt1)
        loc2 = LocationGlobalRelative(23.5445, -12.3333, alt2)
        diff = alt2 - alt1
        vec = location_helpers.getVectorFromPoints(loc, loc2)
        self.assertTrue( vec.x == 0.0 )
        self.assertTrue( vec.y == 0.0 )
        self.assertTrue( vec.z == diff )

    def testLength(self):
        """ Test a vector's length """
        loc = LocationGlobalRelative(-56.34563, -10.23463246, 11.1235235)
        loc2 = LocationGlobalRelative(-56.34561, -10.2346328, 16.3453)
        vec = location_helpers.getVectorFromPoints(loc, loc2)

        length = vec.normalize()
        dist = location_helpers.getDistanceFromPoints3d(loc, loc2)
        self.assertTrue( abs(length - dist) < ERROR )

    def testKnown(self):
        """ Test against Google Earth Data """
        loc = LocationGlobalRelative( 21.5, -77.8, 0)
        loc2 = LocationGlobalRelative( 21.51, -77.79, 0)
        vec = location_helpers.getVectorFromPoints(loc, loc2)
        self.assertTrue( abs( vec.x - 1111.950000 ) < ERROR_LOC )
        self.assertTrue( abs( vec.y - 1034.577815 ) < ERROR_LOC )

    def testKnown2(self):
        """ Test against Google Earth Data """
        loc = LocationGlobalRelative( 83.5, 9.2, 0)
        loc2 = LocationGlobalRelative( 83.51, 9.21, 0)
        vec = location_helpers.getVectorFromPoints(loc, loc2)
        self.assertTrue( abs( vec.x - 1111.950000 ) < ERROR_LOC )
        self.assertTrue( abs( vec.y - 125.876314 ) < ERROR_LOC )
        

class TestAddVectorToLocation(unittest.TestCase):
    def testAddZero(self):
        """ Test adding a zero vector to a location """
        loc = LocationGlobalRelative(34.54656, -20.846948, 8.654654)
        vec = Vector3( 0.0, 0.0, 0.0 )
        newloc = location_helpers.addVectorToLocation(loc, vec)
        dist = location_helpers.getDistanceFromPoints3d(loc, newloc)
        self.assertTrue( dist < ERROR )

    def testKnown(self):
        """ Test adding a zero vector to a location """
        loc = LocationGlobalRelative(83.5, 9.2, 0)
        vec = Vector3( 1111.95, 125.876314, 0 )
        newloc = location_helpers.addVectorToLocation(loc, vec)
        self.assertTrue( abs( newloc.lon - 9.21 ) < ERROR_LOC )
        self.assertTrue( abs( newloc.lat - 83.51 ) < ERROR_LOC )

    def testAddCancel(self):
        """ Test adding a vector and its inverse """
        loc = LocationGlobalRelative(-45.6549814, 65.216548, 45.25641)
        vec = Vector3( 85.6, -23.4, 3.4 )
        vecInv = Vector3( -85.6, 23.4, -3.4 )
        newloc = location_helpers.addVectorToLocation(loc, vec)
        newloc = location_helpers.addVectorToLocation(newloc, vecInv)
        dist = location_helpers.getDistanceFromPoints3d(loc, newloc)
        self.assertTrue( abs(dist) < ERROR )
        
class TestSpotLock(unittest.TestCase):
    def testSpotLockN(self):
        """ Test spot loc North """
        loc = LocationGlobalRelative(34.5, -20.8, 100)
        pitch = -45
        yaw = 0
        newloc = location_helpers.getSpotLock(loc, pitch, yaw)        
        self.assertTrue( abs( newloc.lat - 34.500899 ) < ERROR_LOC )
        self.assertTrue( abs( newloc.lon - -20.8 ) < ERROR_LOC )
        self.assertTrue( newloc.alt == 0.0 )

    def testSpotLockSE(self):
        """ Test spot loc SE """
        loc = LocationGlobalRelative(34.5, -20.8, 100)
        pitch = -70
        yaw = 135
        newloc = location_helpers.getSpotLock(loc, pitch, yaw)
        self.assertTrue( abs( newloc.lat - 34.499769 ) < ERROR_LOC )
        self.assertTrue( abs( newloc.lon - -20.799719 ) < ERROR_LOC )
        self.assertTrue( newloc.alt == 0.0 )

    def testSpotLockW(self):
        """ Test spot loc W at Shallow angle threshold """
        loc = LocationGlobalRelative(34.5, -20.8, 100)
        pitch = -6
        yaw = 270
        newloc = location_helpers.getSpotLock(loc, pitch, yaw)
        self.assertTrue( abs( newloc.lat - 34.5 ) < ERROR_LOC )
        self.assertTrue( abs( newloc.lon - -20.810382 ) < ERROR_LOC )
        self.assertTrue( newloc.alt == 0.0 )
