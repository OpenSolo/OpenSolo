# Unit tests for ROI
import mock
from mock import Mock
import os
from os import sys, path
from pymavlink import mavutil
from shotManagerConstants import *
import unittest
import random
import math

from dronekit import Vehicle, LocationGlobalRelative

sys.path.append(os.path.realpath('..'))
import pathHandler
from shotManager import ShotManager
import shots
import vectorPathHandler

#Random number generator seed
SEED = 94739473

#Number of tests to run
REPEAT = 10

class TestMove(unittest.TestCase):
    def setUp(self):
        mgr = mock.create_autospec(ShotManager)
        #mgr.currentShot = shots.APP_SHOT_ZIPLINE
        v = mock.create_autospec(Vehicle)
        v.message_factory = Mock()
        v.commands = Mock()
        self.handler = vectorPathHandler.VectorPathHandler(v, mgr, 0, 0)
        random.seed(SEED)

    def testTogglePauseShouldPause(self):
        '''If cruiseSpeed != 0 then pause() should be executed'''
        self.handler.pause = Mock()
        self.handler.cruiseSpeed = 4.0
        self.handler.togglePause()
        self.handler.pause.assert_called_with()

    def testTogglePauseShouldResume(self):
        '''If cruiseSpeed == 0 then resume() should be executed'''
        self.handler.resume = Mock()
        self.handler.cruiseSpeed = 0.0
        self.handler.togglePause()
        self.handler.resume.assert_called_with()

    def testSpotLock(self):
        ''' test accurcy of spot lock'''
        vect = self.handler.getUnitVectorFromHeadingAndTilt(0, -45)
        self.assertEqual(int(vect.y*1000), 0)
        self.assertEqual(int(vect.x*1000), 707)
        self.assertEqual(int(vect.z*1000), -707)
        vect = self.handler.getUnitVectorFromHeadingAndTilt(90, -15)
        self.assertEqual(int(vect.y*1000), 965)
        self.assertEqual(int(vect.x*1000), 0)
        self.assertEqual(int(vect.z*1000), -258)
        vect = self.handler.getUnitVectorFromHeadingAndTilt(180, 0)
        self.assertEqual(int(vect.y*1000), 0)
        self.assertEqual(int(vect.x*1000), -1000)
        self.assertEqual(int(vect.z*1000), 0)

    def testNoCruiseForwardsFullStick(self):
        """ Command should reach (and not exceed) MAX_SPEED [Flying in forwards (+) direction, full stick in positive direction] """
        for test in range(REPEAT): #test REPEAT times with random values based on SEED 
            self.handler.cruiseSpeed = 0.0 #No cruise
            initialSpeed = random.uniform(0.0,vectorPathHandler.MAX_PATH_SPEED) #Start at a random positive speed within acceptable limits
            self.handler.accel = 0.136000
            self.handler.currentSpeed = initialSpeed #set currentSpeed to initial
            channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] #Full positive stick
            channels[ROLL] = 1.0
            #calculate number of ticks required to reach MAX_SPEED
            deltaSpeed = vectorPathHandler.MAX_PATH_SPEED - self.handler.currentSpeed
            ticksRequired = int(math.ceil(deltaSpeed/self.handler.accel))

            for ticks in range(1,ticksRequired+1):
                #run controller tick
                returnSpeed = self.handler.move( channels )
                #make sure we are targeted to the right loc
            self.assertEqual(returnSpeed, vectorPathHandler.MAX_PATH_SPEED)

    def testNoCruiseBackwardsFullNegStick(self):
        """ Command should reach (and not exceed) MAX_SPEED [Flying in rewards (-) direction, full stick in negative direction] """
        for test in range(REPEAT): #test REPEAT times with random values based on SEED 
            self.handler.cruiseSpeed = 0.0 #No cruise
            self.handler.accel = 0.136000
            initialSpeed = 0 
            self.handler.currentSpeed = initialSpeed #set currentSpeed to initial
            channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] #Full negative stick
            channels[ROLL] = -1.0
            self.handler.accel = 1.0
            #calculate number of ticks required to reach MAX_SPEED
            deltaSpeed = -vectorPathHandler.MAX_PATH_SPEED - self.handler.currentSpeed
            ticksRequired = int(math.ceil(abs(deltaSpeed/self.handler.accel)))
            
            for ticks in range(1,ticksRequired+1):
                #run controller tick
                returnSpeed = self. handler.move( channels )
                #make sure we are targeted to the right loc
                self.assertGreaterEqual(returnSpeed, 0.0)
            self.assertEqual(returnSpeed, vectorPathHandler.MAX_PATH_SPEED)

# THROTTLE = 0
# ROLL = 1
# PITCH = 2
# YAW = 3
# FILTERED_PADDLE = 5
# RAW_PADDLE = 7

    def testCruiseSameDir(self):
        """ Cruising with full same stick towards loc 2- should accelerate """
        self.handler.cruiseSpeed = 4.0 #random positive cruise speed
        self.handler.accel = 0.136000
        self.handler.currentSpeed = self.handler.cruiseSpeed #start out at cruise
        channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] #Stick forward
        channels[PITCH] = -1.0
        
        returnSpeed = self.handler.move( channels )
        self.assertGreaterEqual(returnSpeed, self.handler.cruiseSpeed)


    def testCruiseOppositeDir(self):
        """ Cruising towards loc 2 with opposite stick - should decelerate to a steady state speed"""
        self.handler.cruiseSpeed = 4.0 #random positive cruise speed
        self.handler.accel = 0.136000
        self.handler.currentSpeed = self.handler.cruiseSpeed #start out at cruise
        channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] #Stick backward
        channels[PITCH] = 1.0
        returnSpeed = self.handler.move( channels )
        self.assertLessEqual(returnSpeed, self.handler.cruiseSpeed)

