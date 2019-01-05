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
#Random number generator seed
SEED = 94739473

#Number of tests to run
REPEAT = 10

class TestMoveTowardsEndpt(unittest.TestCase):
    def setUp(self):
        mgr = mock.create_autospec(ShotManager)
        mgr.currentShot = shots.APP_SHOT_CABLECAM
        self.loc1 = LocationGlobalRelative(45.68464156, 58.68464, 5.54684)
        self.loc2 = LocationGlobalRelative(45.684641555, 58.684655, 5.54684)
        v = mock.create_autospec(Vehicle)
        v.message_factory = Mock()
        v.commands = Mock()
        self.handler = pathHandler.TwoPointPathHandler( self.loc1, self.loc2, v, mgr )
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

    def testNoCruiseForwardsFullStick(self):
        """ Command should reach (and not exceed) MAX_SPEED [Flying in forwards (+) direction, full stick in positive direction] """
        for test in range(REPEAT): #test REPEAT times with random values based on SEED 
            self.handler.cruiseSpeed = 0.0 #No cruise
            initialSpeed = random.uniform(0.0,MAX_SPEED) #Start at a random positive speed within acceptable limits
            self.handler.currentSpeed = initialSpeed #set currentSpeed to initial
            channels = [1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0] #Full positive stick
            #calculate number of ticks required to reach MAX_SPEED
            deltaSpeed = MAX_SPEED-self.handler.currentSpeed
            ticksRequired = int(math.ceil(deltaSpeed/pathHandler.ACCEL_PER_TICK))
            for ticks in range(1,ticksRequired+1):
                #run controller tick
                [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
                #assert but handle floating point errors (limit speed to MAX_SPEED)
                self.assertAlmostEqual(self.handler.currentSpeed, min(initialSpeed + ticks*pathHandler.ACCEL_PER_TICK,MAX_SPEED), places=7, msg=None, delta=None)
                #make sure the command is called
                self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                         mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                         0,       # confirmation
                                                                                         1, abs(self.handler.currentSpeed), -1, # params 1-3
                                                                                         0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
                #make sure we are targeted to the right loc
                self.handler.vehicle.simple_goto.assert_called_with( self.loc2 )
                self.assertGreaterEqual(returnSpeed, 0.0)

    def testNoCruiseBackwardsFullNegStick(self):
        """ Command should reach (and not exceed) -MAX_SPEED [Flying in backwards (-) direction, full stick in negative direction] """
        for test in range(REPEAT):
            self.handler.cruiseSpeed = 0.0 #No cruise
            initialSpeed = random.uniform(-MAX_SPEED,0.0) #Start at a random speed within acceptable limits
            self.handler.currentSpeed = initialSpeed #set currentSpeed to initial
            channels = [1.0, -1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0] #Full negative stick
            #calculate number of ticks required to reach -MAX_SPEED
            deltaSpeed = -MAX_SPEED-self.handler.currentSpeed
            ticksRequired = int(math.ceil(abs(deltaSpeed/pathHandler.ACCEL_PER_TICK)))
            for ticks in range(1,ticksRequired+1):
                #run controller tick
                [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
                #assert but handle floating point errors (limit speed to -MAX_SPEED)
                self.assertAlmostEqual(self.handler.currentSpeed, max(initialSpeed - ticks*pathHandler.ACCEL_PER_TICK,-MAX_SPEED), places=7, msg=None, delta=None)
                #make sure the command is called
                self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                         mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                         0,       # confirmation
                                                                                         1, abs(self.handler.currentSpeed), -1, # params 1-3
                                                                                         0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
                #make sure we are targeted to the right loc
                self.handler.vehicle.simple_goto.assert_called_with( self.loc1 )
                self.assertGreaterEqual(returnSpeed, 0.0)

    def testNoCruiseSwitchDirections(self):
        ''' Command should decelerate to zero and accelerate in new direction [Flying in forwards (+) direction, full stick in negative direction] '''
        for test in range(REPEAT):
            self.handler.cruiseSpeed = 0.0 #No cruise
            initialSpeed = random.uniform(0.0, MAX_SPEED) #Start at a random speed within acceptable limits
            self.handler.currentSpeed = initialSpeed #set currentSpeed to initial
            channels = [1.0, -1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0] #Full negative stick
            #calculate number of decel ticks required to reach 0.0
            deltaSpeed = 0.0-self.handler.currentSpeed
            ticksRequired = int(math.ceil(abs(deltaSpeed/pathHandler.ACCEL_PER_TICK)))
            for ticks in range(1,ticksRequired+1):
                #run controller tick
                [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
                #assert but handle floating point errors (limit speed to -MAX_SPEED)
                self.assertAlmostEqual(self.handler.currentSpeed, initialSpeed - ticks*pathHandler.ACCEL_PER_TICK, places=7, msg=None, delta=None)
                #make sure the command is called
                self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                         mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                         0,       # confirmation
                                                                                         1, abs(self.handler.currentSpeed), -1, # params 1-3
                                                                                         0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
            #should be heading in reverse now
            self.handler.vehicle.simple_goto.assert_called_with( self.loc1 )

            #resync initial speed to current
            initialSpeed = self.handler.currentSpeed

            #redo math to reach full neg speed
            deltaSpeed = -MAX_SPEED-self.handler.currentSpeed
            ticksRequired = int(math.ceil(abs(deltaSpeed/pathHandler.ACCEL_PER_TICK)))
            for ticks in range(1,ticksRequired+1):
                #run controller tick
                [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
                #assert but handle floating point errors (limit speed to -MAX_SPEED)
                self.assertAlmostEqual(self.handler.currentSpeed, max(initialSpeed - ticks*pathHandler.ACCEL_PER_TICK,-MAX_SPEED), places=7, msg=None, delta=None)
                #make sure the command is called
                self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                         mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                         0,       # confirmation
                                                                                         1, abs(self.handler.currentSpeed), -1, # params 1-3
                                                                                         0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
            self.assertEqual(-MAX_SPEED,self.handler.currentSpeed)
            self.assertGreaterEqual(returnSpeed, 0.0)
            
    def testNoCruisePitchBigger(self):
        """ Pitch beats roll """
        channels = [1.0, 0.4, -0.8, 1.0, 1.0, 1.0, 1.0, 1.0]
        self.handler.cruiseSpeed = 0.0 #No cruise
        self.handler.currentSpeed = 0.0 #Start at a standstill
        [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
        self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                     mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                     0,       # confirmation
                                                                                     1, pathHandler.ACCEL_PER_TICK, -1, # params 1-3
                                                                                     0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
        self.handler.vehicle.simple_goto.assert_called_with( self.loc2 )
        self.assertGreaterEqual(returnSpeed, 0.0)


    def testNoCruiseRollBigger(self):
        """ Roll beats pitch """
        channels = [1.0, -0.72, 0.33, 1.0, 1.0, 1.0, 1.0, 1.0]
        self.handler.cruiseSpeed = 0.0 #No cruise
        self.handler.currentSpeed = 0.0 #Start at a standstill
        [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
        self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                     mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                     0,       # confirmation
                                                                                     1, pathHandler.ACCEL_PER_TICK, -1, # params 1-3
                                                                                     0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
        self.handler.vehicle.simple_goto.assert_called_with( self.loc1 )
        self.assertGreaterEqual(returnSpeed, 0.0)

    def testNoCruisePositiveAccelerate(self):
        ''' Vehicle flying in positive direction, increase stick in positive direction - should accelerate to steady state speed'''
        for test in range(REPEAT):
            initialSpeed = random.uniform(0.0,MAX_SPEED) #Start at a random speed within acceptable limits
            self.handler.currentSpeed = initialSpeed #set currentSpeed to initial
            stickSpeed = random.uniform(initialSpeed,MAX_SPEED) #set a random stick speed above the randomly chosen initial speed
            stickVal = stickSpeed/MAX_SPEED #calculate corresponding stick value
            channels = [1.0, stickVal, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
            #calculate number of accel ticks required to reach stickSpeed
            deltaSpeed = stickSpeed-self.handler.currentSpeed
            ticksRequired = int(math.ceil(abs(deltaSpeed/pathHandler.ACCEL_PER_TICK)))
            for ticks in range(1,ticksRequired+1):
                #run controller tick
                [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
                #assert but handle floating point errors (limit to stickSpeed)
                self.assertAlmostEqual(self.handler.currentSpeed, min(initialSpeed + ticks*pathHandler.ACCEL_PER_TICK,stickSpeed), places=7, msg=None, delta=None)
                #make sure the command is called
                self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                         mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                         0,       # confirmation
                                                                                         1, abs(self.handler.currentSpeed), -1, # params 1-3
                                                                                         0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
            self.assertEqual(stickSpeed,self.handler.currentSpeed)
            self.handler.vehicle.simple_goto.assert_called_with( self.loc2 )
            self.assertGreaterEqual(returnSpeed, 0.0)

    def testNoCruisePositiveDecelerate(self):
        ''' Vehicle flying in positive direction, decrease stick in positive direction - should decelerate '''
        for test in range(REPEAT):
            initialSpeed = random.uniform(0.0,MAX_SPEED) #Start at a random speed within acceptable limits
            self.handler.currentSpeed = initialSpeed #set currentSpeed to initial
            stickSpeed = random.uniform(0.0,initialSpeed) #set a random stick speed above the randomly chosen initial speed
            stickVal = stickSpeed/MAX_SPEED #calculate corresponding stick value
            channels = [1.0, stickVal, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
            #calculate number of accel ticks required to reach stickSpeed
            deltaSpeed = stickSpeed-self.handler.currentSpeed
            ticksRequired = int(math.ceil(abs(deltaSpeed/pathHandler.ACCEL_PER_TICK)))
            for ticks in range(1,ticksRequired+1):
                #run controller tick
                [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
                #assert but handle floating point errors (limit to stickSpeed)
                self.assertAlmostEqual(self.handler.currentSpeed, max(initialSpeed - ticks*pathHandler.ACCEL_PER_TICK,stickSpeed), places=7, msg=None, delta=None)
                #make sure the command is called
                self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                         mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                         0,       # confirmation
                                                                                         1, abs(self.handler.currentSpeed), -1, # params 1-3
                                                                                         0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
            self.assertEqual(stickSpeed,self.handler.currentSpeed)
            self.handler.vehicle.simple_goto.assert_called_with( self.loc2 )
            self.assertGreaterEqual(returnSpeed, 0.0)

    def testNoCruiseNegativeAccelerate(self):
        ''' Vehicle flying in negative direction, increase stick in negative direction - should accelerate '''
        for test in range(REPEAT):
            initialSpeed = random.uniform(-MAX_SPEED,0.0) #Start at a random speed within acceptable limits
            self.handler.currentSpeed = initialSpeed #set currentSpeed to initial
            stickSpeed = random.uniform(-MAX_SPEED,initialSpeed) #set a random stick speed above the randomly chosen initial speed
            stickVal = stickSpeed/MAX_SPEED #calculate corresponding stick value
            channels = [1.0, stickVal, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
            #calculate number of accel ticks required to reach stickSpeed
            deltaSpeed = stickSpeed-self.handler.currentSpeed
            ticksRequired = int(math.ceil(abs(deltaSpeed/pathHandler.ACCEL_PER_TICK)))
            for ticks in range(1,ticksRequired+1):
                #run controller tick
                [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
                #assert but handle floating point errors (limit to stickSpeed)
                self.assertAlmostEqual(self.handler.currentSpeed, max(initialSpeed - ticks*pathHandler.ACCEL_PER_TICK,stickSpeed), places=7, msg=None, delta=None)
                #make sure the command is called
                self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                         mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                         0,       # confirmation
                                                                                         1, abs(self.handler.currentSpeed), -1, # params 1-3
                                                                                         0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
            self.assertEqual(stickSpeed,self.handler.currentSpeed)
            self.handler.vehicle.simple_goto.assert_called_with( self.loc1 )
            self.assertGreaterEqual(returnSpeed, 0.0)

    def testNoCruiseNegativeDecelerate(self):
        ''' Vehicle flying in negative direction, decrease stick in negative direction - should decelerate '''
        for test in range(REPEAT):
            initialSpeed = random.uniform(-MAX_SPEED,0.0) #Start at a random speed within acceptable limits
            self.handler.currentSpeed = initialSpeed #set currentSpeed to initial
            stickSpeed = random.uniform(initialSpeed,0.0) #set a random stick speed above the randomly chosen initial speed
            stickVal = stickSpeed/MAX_SPEED #calculate corresponding stick value
            channels = [1.0, stickVal, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0]
            #calculate number of accel ticks required to reach stickSpeed
            deltaSpeed = stickSpeed-self.handler.currentSpeed
            ticksRequired = int(math.ceil(abs(deltaSpeed/pathHandler.ACCEL_PER_TICK)))
            for ticks in range(1,ticksRequired+1):
                #run controller tick
                [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
                #assert but handle floating point errors (limit to stickSpeed)
                self.assertAlmostEqual(self.handler.currentSpeed, min(initialSpeed + ticks*pathHandler.ACCEL_PER_TICK,stickSpeed), places=7, msg=None, delta=None)
                #make sure the command is called
                self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                         mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                         0,       # confirmation
                                                                                         1, abs(self.handler.currentSpeed), -1, # params 1-3
                                                                                         0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
            self.assertEqual(stickSpeed,self.handler.currentSpeed)
            self.handler.vehicle.simple_goto.assert_called_with( self.loc1 )
            self.assertGreaterEqual(returnSpeed, 0.0)   

    ###CRUISE TESTS###

    def testCruiseSameDir(self):
        """ Cruising with full same stick towards loc 2- should accelerate """
        self.handler.cruiseSpeed = 4.0 #random positive cruise speed
        self.handler.currentSpeed = self.handler.cruiseSpeed #start out at cruise
        channels = [1.0, 0.5, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0] #Stick forward

        [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
        #make sure the command is called
        self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                 mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                 0,       # confirmation
                                                                                 1, self.handler.cruiseSpeed + pathHandler.ACCEL_PER_TICK, -1, # params 1-3
                                                                                 0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
        self.handler.vehicle.simple_goto.assert_called_with( self.loc2 )
        self.assertGreaterEqual(returnSpeed, 0.0)

    def testCruiseOppositeDir(self):
        """ Cruising towards loc 2 with opposite stick - should decelerate to a steady state speed"""
        self.handler.cruiseSpeed = 4.0 #random positive cruise speed
        self.handler.currentSpeed = self.handler.cruiseSpeed #start out at cruise
        channels = [1.0, -0.5, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0] #Stick backward

        [returnSpeed, returnDirection] = self.handler.MoveTowardsEndpt( channels )
        #make sure the command is called
        self.handler.vehicle.message_factory.command_long_encode.assert_called_with(0, 1,    # target system, target component
                                                                                 mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                 0,       # confirmation
                                                                                 1, self.handler.cruiseSpeed - pathHandler.ACCEL_PER_TICK, -1, # params 1-3
                                                                                 0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
        self.handler.vehicle.simple_goto.assert_called_with( self.loc2 )
        self.assertGreaterEqual(returnSpeed, 0.0)
