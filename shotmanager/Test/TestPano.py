#  TestOrbit.py
#  shotmanager
#
#  Unit tests for the orbit smart shot.
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

import pano
from pano import *

import shotManager
from shotManager import ShotManager

import unittest

import mock
from mock import call
from mock import Mock
from mock import MagicMock
from mock import patch


class TestShotInit(unittest.TestCase):
    def setUp(self):
        '''Create a mock vehicle object'''
        vehicle = mock.create_autospec(Vehicle)
        vehicle.attitude.yaw = math.radians(0)

        '''Create a mock shotManager object'''
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.appMgr = Mock()
        shotmgr.buttonManager = Mock()
        shotmgr.goproManager = Mock()
        shotmgr.rcMgr = Mock(specs=['remapper'])        
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds

        '''Run the shot constructor'''
        self.shot = pano.PanoShot(vehicle, shotmgr)


    def testInit(self):
        '''Test that the shot initialized properly'''

        # vehicle object should be created (not None)
        assert self.shot.vehicle is not None

        # shotManager object should be created (not None)
        assert self.shot.shotmgr is not None

        # filtered roi should be None
        self.assertEqual(self.shot.state, PANO_SETUP)
        self.assertEqual(self.shot.panoType, PANO_CYLINDER)
        self.assertEqual(self.shot.degSecondYaw, PANO_DEFAULT_VIDEO_YAW_RATE)
        self.assertEqual(self.shot.cylinder_fov, PANO_DEFAULT_FOV)
        
        # enter Guided
        self.assertEqual(self.shot.vehicle.mode.name, "GUIDED")

    def testRCSetupState(self):
        self.shot.state = PANO_SETUP
        #Neutral sticks
        throttle = 0.0
        roll = 0.0
        pitch = 0.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        self.shot.handleRCs(self.channels)

    def testCylinder(self):
        self.shot.state = PANO_SETUP

        #Neutral sticks
        throttle = 0.0
        roll = 0.0
        pitch = 0.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        self.shot.initCylinder()
        #print "angles %s" % str(self.shot.cylinderAngles).strip('[]')
        self.assertEqual(self.shot.cylinderAngles[0], 270)
        self.assertEqual(self.shot.cylinderAngles[1], 306)
        self.assertEqual(self.shot.cylinderAngles[2], 342)
        self.assertEqual(self.shot.cylinderAngles[3], 18)
        self.assertEqual(self.shot.cylinderAngles[4], 54)
        
        # check we are incrementing ticks correctly
        self.assertEqual(self.shot.ticks, -25)
        self.shot.runCylinder()
        self.assertEqual(self.shot.ticks, -24)

        # handle RCs runs
        self.shot.state = PANO_RUN
        self.shot.handleRCs(self.channels)
        self.assertEqual(self.shot.ticks, -23)

        self.assertEqual(self.shot.camYaw, 90)
        #print "self.shot.camYaw %d", self.shot.camYaw
        
        # Force us to grab next Yaw and verify
        self.shot.ticks = PANO_MOVE_DELAY
        self.shot.runCylinder()         
        self.assertEqual(self.shot.camYaw, 54)

        # Force us to grab next Yaw and verify
        self.shot.ticks = PANO_MOVE_DELAY
        self.shot.runCylinder()         
        self.assertEqual(self.shot.camYaw, 18)

        # Force us to grab next Yaw and verify
        self.shot.ticks = PANO_MOVE_DELAY
        self.shot.runCylinder()
        self.assertEqual(self.shot.camYaw, 342)

        # Force us to grab next Yaw and verify
        self.shot.ticks = PANO_MOVE_DELAY
        self.shot.runCylinder()
        self.assertEqual(self.shot.camYaw, 306)

        # Force us to grab next Yaw and verify
        self.shot.ticks = PANO_MOVE_DELAY
        self.shot.runCylinder()         
        self.assertEqual(self.shot.camYaw, 270)


        # Force us to exit shot
        self.assertEqual(self.shot.state, PANO_RUN)
        self.shot.ticks = PANO_MOVE_DELAY
        self.shot.runCylinder()
        self.assertEqual(self.shot.state, PANO_EXIT)


    def testSphere(self):
        self.shot.state = PANO_SETUP
        self.shot.panoType = PANO_SPHERE

        #Neutral sticks
        throttle = 0.0
        roll = 0.0
        pitch = 0.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        self.shot.initSphere()
        #print "angles %s" % str(self.shot.sphereAngles).strip('[]')
        self.assertEqual(self.shot.sphereAngles[0][0], -90)
        self.assertEqual(self.shot.sphereAngles[0][1], 0)
        self.assertEqual(self.shot.sphereAngles[9][0], 0)
        self.assertEqual(self.shot.sphereAngles[9][1], 60)
        
        length = len(self.shot.sphereAngles)
        # make sure camera is reset
        self.assertEqual(length, 10)
        self.assertEqual(self.shot.camYaw, 0)
        self.assertEqual(self.shot.camPitch, 0)        

        for x in range(0, length):
            #print "howdy %d" %x
            tmp = self.shot.sphereAngles.pop()

        # Force us to exit shot
        self.shot.state = PANO_RUN
        self.shot.ticks = PANO_MOVE_DELAY
        self.shot.runSphere()
        self.assertEqual(self.shot.state, PANO_EXIT)
        
        
    def testVideo(self):
        self.shot.panoType = PANO_VIDEO
        # sticks
        throttle = 0.0
        roll = 0.0
        pitch = 0.0
        yaw = 1.0
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        self.shot.camYaw = 0
        for x in range(0, 25):
            self.shot.runVideo(self.channels)
        self.assertGreaterEqual(self.shot.camYaw, 9.7)
        
    
    def testPitch(self):
        # sticks
        throttle = -1.0
        roll = 0.0
        pitch = 0.0
        yaw = 0.0
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        self.shot.camPitch = 0
        
        for x in range(0, 40):
            self.shot.manualPitch(self.channels)
        self.assertEqual(self.shot.camPitch, -90)

        throttle = 1.0
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        for x in range(0, 40):
            self.shot.manualPitch(self.channels)
        self.assertEqual(self.shot.camPitch, 0)

        
        

