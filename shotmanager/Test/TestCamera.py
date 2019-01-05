# Unit tests for camera
import math
import mock
import os
from os import sys, path
import unittest

from dronekit import LocationGlobalRelative
sys.path.append(os.path.realpath('..'))
import camera

class Attitude():
    def __init__( self,  yaw = 0.0 ):
        self.yaw = yaw

# mock vehicle for tests
class Vehicle():
    def __init__( self,  yaw = 0.0, pitch = None ):
        self.attitude = Attitude( yaw )
        self.mount_status = [ pitch, math.degrees( yaw ), 0.0 ]


class TestCameraYaw(unittest.TestCase):
    def testCameraGetYawZeroNoGimbal(self):
        """ retrieve yaw 0 from camera class (no gimbal) """
        v = Vehicle( yaw = 0.0 )
        self.assertEqual( camera.getYaw(v), 0.0 )

    def testCameraGetYaw90NoGimbal(self):
        """ retrieve yaw 90 from camera class (no gimbal) """
        v = Vehicle( yaw = math.radians(90.0) )
        self.assertEqual( camera.getYaw(v), 90.0 )

    def testCameraGetYawZeroWithGimbal(self):
        """ retrieve yaw 0 from camera class (gimbal) """
        v = Vehicle( yaw = 0.0, pitch = 35.2 )
        v.attitude.yaw = math.radians(13.0)
        #self.assertEqual( camera.getYaw(v), 0.0 )
        # for now, we are using vehicle yaw in all cases
        self.assertEqual( camera.getYaw(v), 13.0 )

    def testCameraGetYaw90WithGimbal(self):
        """ retrieve yaw 90 from camera class (gimbal) """
        v = Vehicle( yaw = math.radians(90.0), pitch = 78.3 )
        v.attitude.yaw = math.radians(13.0)
        #self.assertEqual( camera.getYaw(v), 90.0 )
        # for now, we are using vehicle yaw in all cases
        self.assertEqual( camera.getYaw(v), 13.0 )


class TestCameraPitch(unittest.TestCase):
    def testCameraGetPitchNoGimbal(self):
        """ retrieve pitch from camera class (no gimbal) """
        v = Vehicle()
        self.assertEqual( camera.getPitch(v), 0.0 )

    def testCameraGetPitch45(self):
        """ retrieve 45 pitch from camera class """
        v = Vehicle( pitch = 45.0 )
        self.assertEqual( camera.getPitch(v), 45.0 )

    def testCameraGetPitch70(self):
        """ retrieve 70 pitch from camera class """
        v = Vehicle( pitch = 70.0 )
        self.assertEqual( camera.getPitch(v), 70.0 )