#  TestMultipoint.py
#  shotmanager
#
#  Unit tests for the multipoint smart shot.
#
#  Created by Will Silva 1/22/2015.
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

import multipoint
from multipoint import *

import shotManager
from shotManager import ShotManager

import unittest

import mock
from mock import call
from mock import Mock
from mock import MagicMock
from mock import patch


class TestHandleRCs(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        #Mock checkToNotifyApp()
        self.shot.checkToNotifyApp = Mock()

        #Mock listenForAttach()
        self.shot.listenForAttach = Mock()

        #attaching
        self.shot.attaching = False

        #Cable cam playing
        self.shot.cableCamPlaying = True

        #Cruise speed
        self.shot.cruiseSpeed = 0.

        #Mock cableController
        self.shot.cable = mock.create_autospec(CableController)
        self.shot.cable.position = Vector3()
        self.shot.cable.velocity = Vector3()
        self.shot.splineOrigin = LocationGlobalRelative(37.873168,-122.302062, 0)

        #Mock interpolateCamera()
        self.shot.interpolateCamera = Mock(return_value=(0,0))

        #Mock yawPitchOffsetter
        self.shot.yawPitchOffsetter.Update = Mock()

        #channels
        throttle = 0.0
        roll = 0.0
        pitch = 0.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]

    def testCableCamNotReady(self):
        ''' Test that HandleRCs returns if cable cam isn't ready yet '''

        self.shot.cableCamPlaying = False
        self.shot.handleRCs(self.channels)
        assert not self.shot.checkToNotifyApp.called

    def testCableCamAttaching(self):
        '''Test that listenForAttach() is called when attaching'''

        self.shot.attaching = True
        self.shot.handleRCs(self.channels)
        self.shot.listenForAttach.assert_called_with()

    def testCallCheckToNotifyApp(self):
        '''Test that checkToNotifyApp() is called'''

        self.shot.handleRCs(self.channels)
        self.shot.checkToNotifyApp.assert_called_with()

    def testRollGreaterThanPitch(self):
        '''Test that Roll value is used if greater than Pitch value'''
        
        #channels
        throttle = 0.0
        roll = 1.0
        pitch = 0.5
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        self.shot.handleRCs(self.channels)
        self.assertEqual(self.shot.desiredSpeed,MAX_SPEED)

    def testPitchGreaterThanRoll(self):
        '''Test that Pitch value is used if greater than Roll value'''
        
        #channels
        throttle = 0.0
        roll = 0.5
        pitch = 1.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        self.shot.handleRCs(self.channels)
        self.assertEqual(self.shot.desiredSpeed,-MAX_SPEED)

    def testZeroCruiseSpeed(self):
        '''Test that if cruiseSpeed is zero, stick value scales MAX_SPEED'''

        #channels
        throttle = 0.0
        roll = 0.7
        pitch = 0.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        self.shot.handleRCs(self.channels)
        self.assertEqual(self.shot.desiredSpeed, 0.7 * MAX_SPEED)

    def testStickWithCruiseSpeed(self):
        '''Test that if cruiseSpeed is non-zero, stick in same direction increases speed'''

        #channels
        throttle = 0.0
        roll = 0.7
        pitch = 0.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        self.shot.cruiseSpeed = 4 #m/s
        self.shot.handleRCs(self.channels)
        self.assertEqual(self.shot.desiredSpeed, 4 + (MAX_SPEED - 4) * 0.7)

    def testStickAgainstCruiseSpeed(self):
        '''Test that if cruiseSpeed is non-zero, stick in opposite direction decreases speed'''

        #channels
        throttle = 0.0
        roll = -0.7
        pitch = 0.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        self.shot.cruiseSpeed = 4 #m/s
        self.shot.handleRCs(self.channels)
        self.assertEqual(self.shot.desiredSpeed, 4 * (1. - 0.7))

    def testLimitSpeedDemandToMAX_SPEED(self):
        '''Test that the speed demand is limited to MAX_SPEED'''

        #channels
        throttle = 0.0
        roll = 1.0
        pitch = 0.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]
        self.shot.cruiseSpeed = MAX_SPEED #m/s
        self.shot.handleRCs(self.channels)
        self.assertEqual(self.shot.desiredSpeed, MAX_SPEED)

    def testCarryOverCruiseSpeedSign(self):
        '''If cruiseSpeed < 0, carry its sign over'''

        self.shot.cruiseSpeed = -4
        self.shot.handleRCs(self.channels)
        self.assertEqual(self.shot.desiredSpeed, -4)

    def testSetTargetPositiveDesiredSpeed(self):
        '''Test that targetP is set to 1.0 if desiredSpeed is > 0'''

        self.shot.cruiseSpeed = 4
        self.shot.handleRCs(self.channels)
        self.assertEqual(self.shot.targetP, 1.0)

    def testSetTargetZeroDesiredSpeed(self):
        '''Test that targetP is set to 1.0 if desiredSpeed is = 0'''

        self.shot.handleRCs(self.channels)
        self.assertEqual(self.shot.targetP, 0.0)

    def testSetTargetNegativeDesiredSpeed(self):
        '''Test that targetP is set to 0.0 if desiredSpeed is < 0'''

        self.shot.cruiseSpeed = -4
        self.shot.handleRCs(self.channels)
        self.assertEqual(self.shot.targetP, 0.0)

    def testUpdatingCableController(self):
        '''Tests that the cableController update functions are called'''

        self.shot.handleRCs(self.channels)
        self.shot.cable.setTargetP.assert_called_with(0.0)
        self.shot.cable.trackSpeed.assert_called_with(0.0)
        self.shot.cable.update.assert_called_with(UPDATE_TIME)

    def testPosVelMessage(self):
        '''Test that pos-vel message is formed correctly'''

        self.shot.handleRCs(self.channels)
        self.shot.vehicle.message_factory.set_position_target_global_int_encode.assert_called_with(
            0,       # time_boot_ms (not used)
            0, 1,    # target system, target component
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,  # frame
            0b0000110111000000,  # type_mask - enable pos/vel
            int(37.873168 * 10000000),  # latitude (degrees*1.0e7)
            int(-122.302062 * 10000000),  # longitude (degrees*1.0e7)
            0,  # altitude (meters)
            0.0, 0.0, 0.0,  # North, East, Down velocity (m/s)
            0, 0, 0,  # x, y, z acceleration (not used)
            0, 0)    # yaw, yaw_rate (not used)
        self.shot.vehicle.send_mavlink.assert_called_with(mock.ANY)

    def testInterpolateCamON(self):
        ''' InterpolateCamera should be called if the option is on '''

        self.shot.camInterpolation = 0
        self.shot.handleRCs(self.channels)
        self.shot.interpolateCamera.assert_called_with()

    def testInterpolateCamOFF(self):
        ''' InterpolateCamera should NOT be called if the option is off '''

        self.shot.camInterpolation = 1
        self.shot.handleRCs(self.channels)
        assert not self.shot.interpolateCamera.called

    def testCallingYawPitchOffsetterUpdate(self):
        '''yawPitchOffsetter.Update() should always be called'''

        self.shot.handleRCs(self.channels)
        self.shot.yawPitchOffsetter.Update.assert_called_with(self.channels)

    def testWithGimbal(self):
        ''' Test message packaging if we have a gimbal'''

        self.shot.vehicle.mount_status = [0.0, ]
        self.shot.handleRCs(self.channels)
        self.shot.vehicle.message_factory.mount_control_encode.assert_called_with(
            0, 1,    # target system, target component
            mock.ANY,  # pitch is in centidegrees
            0.0,  # roll
            mock.ANY,  # yaw is in centidegrees
            0  # save position
        )

    def testWithNoGimbal(self):
        ''' Test message packaging if we don't have a gimbal'''

        self.shot.vehicle.mount_status = [None, ]
        self.shot.handleRCs(self.channels)
        self.shot.vehicle.message_factory.command_long_encode.assert_called_with(
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_CMD_CONDITION_YAW,  # command
            0,  # confirmation
            mock.ANY,  # param 1 - target angle
            mock.ANY,  # param 2 - yaw speed
            0,  # param 3 - direction, always shortest route for now...
            0.0,  # relative offset
            0, 0, 0  # params 5-7 (unused)
        )


class TestInterpolateCamera(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        #Mock cableController
        self.shot.cable = mock.create_autospec(CableController)
        self.shot.cable.currentU = 0.5  # half-way through spline
        self.shot.cable.currentSeg = 0

        # create two waypoints
        loc = LocationGlobalRelative(37.873168,-122.302062, 0)
        self.shot.waypoints.append(Waypoint(loc,-90,0))
        self.shot.waypoints.append(Waypoint(loc,0,90))

        self.shot.camSpline = CatmullRom([Vector2(-180, -90), Vector2(-90, 0), Vector2(0, 90), Vector2(90, 180)])

    def testNewPitchYaw(self):
        '''Make sure newYaw is linearly interpolating between two target yaws'''

        newPitch, newYaw = self.shot.interpolateCamera()
        self.assertEqual(newYaw, 45)
        self.assertEqual(newPitch, -45)

    @mock.patch('location_helpers.wrapTo360')
    def testCurrentUGreaterThanOne(self, location_helpers_wrapTo360):
        '''Test that if cable.currentU is greater than 1, then it is set to 1'''

        self.shot.cable.currentU = 1.2
        self.shot.camSpline.position = Mock()
        self.shot.interpolateCamera()
        self.shot.camSpline.position.assert_called_with(0,1.0)

    @mock.patch('location_helpers.wrapTo360')
    def testCurrentULessThanZero(self, location_helpers_wrapTo360):
        '''Test that if cable.currentU is less than zero, then it is set to 0'''

        self.shot.cable.currentU = -0.1
        self.shot.camSpline.position = Mock()
        self.shot.interpolateCamera()
        self.shot.camSpline.position.assert_called_with(0,0.0)

class TestRecordLocation(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds
        shotmgr.appMgr = Mock()

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        #Mock setButtonMappings()
        self.shot.setButtonMappings = Mock()

        self.shot.duplicateCheck = Mock(return_value=False)

    def testRecordInPlayMode(self):
        '''Try recording a location when in PLAY mode'''
        self.shot.vehicle.location.global_relative_frame = LocationGlobalRelative(37.242124, -122.12841, 15.3)
        self.shot.cableCamPlaying = True
        self.shot.recordLocation()
        assert not self.shot.duplicateCheck.called

    def testRecordingLocations(self):
        ''' Test if recording locations '''
        self.shot.vehicle.location.global_relative_frame = LocationGlobalRelative(37.242124, -122.12841, 15.3)
        self.shot.recordLocation()
        self.shot.vehicle.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.shot.recordLocation()
        self.shot.vehicle.location.global_relative_frame = LocationGlobalRelative(37.873115, -122.303307, 25.0)
        self.shot.recordLocation()
        self.assertTrue(len(self.shot.waypoints) == 3)

    @patch('camera.getPitch')
    @patch('camera.getYaw')
    def testRecordingSameLocations(self, mock_getPitch, mock_getYaw):
        ''' Test if recording the same locations '''
        mock_getPitch.return_value = 0
        mock_getYaw.return_value = 0
        self.shot.vehicle.location.global_relative_frame = LocationGlobalRelative(37.242124, -122.12841, 15.3)
        self.shot.vehicle.location.global_frame.alt = 0
        self.shot.recordLocation()
        mock_getPitch.return_value = 45
        mock_getYaw.return_value = 45
        self.shot.duplicateCheck.return_value = True
        self.shot.recordLocation()
        self.assertTrue(len(self.shot.waypoints) == 1)
        packet = struct.pack('<IIhfIddffffh', app_packet.SOLO_SPLINE_POINT, 44, 0, -15.3,
                             len(self.shot.waypoints) - 1, 37.242124, -122.12841, 15.3, 45, 45, 0, app_packet.SPLINE_ERROR_NONE)
        self.shot.shotmgr.appMgr.sendPacket.assert_called_with(packet)

    def testCallSetButtonMappings(self):
        ''' Test if setButtonMappings is called when recording a location '''
        self.shot.setButtonMappings = Mock()
        self.shot.vehicle.location.global_relative_frame = LocationGlobalRelative(37.242124, -122.12841, 15.3)
        self.shot.recordLocation()
        self.shot.setButtonMappings.assert_called_with()

    @patch('camera.getPitch')
    @patch('camera.getYaw')
    def testCallSendPacket(self, mock_getPitch, mock_getYaw):
        ''' Test if sendPacket is called when recording a location '''
        self.shot.vehicle.location.global_relative_frame = LocationGlobalRelative(37.242124, -122.12841, 15.3)
        self.shot.vehicle.location.global_frame.alt = 0
        mock_getPitch.return_value = 45
        mock_getYaw.return_value = 45
        packet = struct.pack('<IIhfIddffffh', app_packet.SOLO_SPLINE_POINT, 44, 0, -15.3,
                             0, self.shot.vehicle.location.global_relative_frame.lat, self.shot.vehicle.location.global_relative_frame.lon,
                             self.shot.vehicle.location.global_relative_frame.alt, 45, 45, 0, app_packet.SPLINE_ERROR_NONE)
        self.shot.recordLocation()
        self.shot.shotmgr.appMgr.sendPacket.assert_called_with(packet)


class TestLoadSplinePoint(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds
        shotmgr.appMgr = Mock()

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        #cableCamPlaying
        self.cableCamPlaying = False

        # Mock setButtonMappings
        self.shot.setButtonMappings = Mock()

        #Mock duplicate check
        self.shot.duplicateCheck = Mock(return_value=False)

        # default packet
        self.point = (0, -15.3, 0, 37.330674, -122.028759, 15, 0, 90, 0, 0)

    def testInPlayMode(self):
        '''Test loading a point while in play mode'''

        self.shot.cableCamPlaying = True
        self.shot.loadSplinePoint(self.point)
        # expected packet with status bit set to -1 (mode error)
        expectedPacket = struct.pack('<IIhfIddffffh', app_packet.SOLO_SPLINE_POINT, 44, 0, -15.3,
                                     0, 37.330674, -122.028759, 15, 0, 90, 0, app_packet.SPLINE_ERROR_MODE)
        self.shot.shotmgr.appMgr.sendPacket.assert_called_with(expectedPacket)

    def testDuplicate(self):
        '''Test loading a duplicate point'''

        self.shot.duplicateCheck.return_value = True
        self.shot.loadSplinePoint(self.point)
        # expected packet with status bit set to -2 (dup error)
        expectedPacket = struct.pack('<IIhfIddffffh', app_packet.SOLO_SPLINE_POINT, 44, 0, -15.3,
                                     0, 37.330674, -122.028759, 15, 0, 90, 0, app_packet.SPLINE_ERROR_DUPLICATE)
        self.shot.shotmgr.appMgr.sendPacket.assert_called_with(expectedPacket)

    def testSuccessfulLoad(self):
        '''Test loading a point '''

        self.shot.loadSplinePoint(self.point)
        # expected packet with status bit set to 0 (no error)
        expectedPacket = struct.pack('<IIhfIddffffh', app_packet.SOLO_SPLINE_POINT, 44, 0, -15.3,
                                     0, 37.330674, -122.028759, 15, 0, 90, 0, app_packet.SPLINE_ERROR_NONE)
        self.shot.shotmgr.appMgr.sendPacket.assert_called_with(expectedPacket)
        self.shot.setButtonMappings.assert_called_with()


class TestDuplicateCheck(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        self.loc1 = LocationGlobalRelative(37.873309, -122.302562, 10)
        self.pitch1 = 45
        self.yaw1 = 300

        self.loc2 = LocationGlobalRelative(38.873309, -123.302562, 10)
        self.pitch2 = 0
        self.yaw2 = 10

        self.loc3 = LocationGlobalRelative(39.873309, -124.302562, 10)
        self.pitch3 = 0
        self.yaw3 = 50

        self.loc4 = LocationGlobalRelative(40.873309, -125.302562, 10)
        self.pitch4 = 0
        self.yaw4 = 30

    def testNotEnoughWaypoints(self):
        '''Should return False because there's no other point to compare against'''

        self.shot.waypoints = []
        retVal = self.shot.duplicateCheck(self.loc1, 0)
        self.assertEqual(retVal, False)

    def testDuplicateNextIndex(self):
        '''Should return True because this matches our previously stored waypoint'''

        self.shot.waypoints = [
            Waypoint(self.loc1, self.pitch1, self.yaw1)]
        retVal = self.shot.duplicateCheck(self.loc1, 1)
        self.assertEqual(retVal, True)

    def testDuplicateOnLeft(self):
        '''Should return True because index 0 conflicts'''

        self.shot.waypoints = [Waypoint(self.loc1, self.pitch1, self.yaw1), Waypoint(
            self.loc2, self.pitch2, self.yaw2), Waypoint(self.loc3, self.pitch3, self.yaw3)]
        retVal = self.shot.duplicateCheck(self.loc1, 1)
        self.assertEqual(retVal, True)

    def testDuplicateOnRight(self):
        '''Should return True because index 2 conflicts'''

        self.shot.waypoints = [Waypoint(self.loc1, self.pitch1, self.yaw1), Waypoint(
            self.loc2, self.pitch2, self.yaw2), Waypoint(self.loc3, self.pitch3, self.yaw3)]
        retVal = self.shot.duplicateCheck(self.loc3, 1)
        self.assertEqual(retVal, True)

    def testDuplicateZeroIndex(self):
        '''Should return True because index 1 conflicts'''

        self.shot.waypoints = [Waypoint(
            self.loc1, self.pitch1, self.yaw1), Waypoint(self.loc2, self.pitch2, self.yaw2)]
        retVal = self.shot.duplicateCheck(self.loc2, 0)
        self.assertEqual(retVal, True)

    def testDuplicateLastIndex(self):
        '''Should return True because index end-1 conflicts'''

        self.shot.waypoints = [Waypoint(
            self.loc1, self.pitch1, self.yaw1), Waypoint(self.loc2, self.pitch2, self.yaw2)]
        retVal = self.shot.duplicateCheck(self.loc1, 1)
        self.assertEqual(retVal, True)

    def testDuplicateNoIndicies(self):
        '''Should return False because there aren't any indices to compare against'''

        self.shot.waypoints = [
            Waypoint(self.loc1, self.pitch1, self.yaw1)]
        retVal = self.shot.duplicateCheck(self.loc1, 0)
        self.assertEqual(retVal, False)


class TestSetButtonMappings(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.buttonManager = Mock()

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        # 1 waypoint
        self.shot.waypoints = [1]

        # Play mode
        self.shot.cableCamPlaying = True

    def testNoWaypointsYet(self):
        '''Test that if there are no waypoints stored yet, then only A button (record point) should be active'''

        self.shot.waypoints = []
        self.shot.setButtonMappings()
        calls = [call(btn_msg.ButtonA, shots.APP_SHOT_MULTIPOINT, btn_msg.ARTOO_BITMASK_ENABLED, "Record Point\0"), call(btn_msg.ButtonB, shots.APP_SHOT_MULTIPOINT, 0, "\0")]
        self.shot.shotmgr.buttonManager.setArtooButton.assert_has_calls(calls)

    def testInRecordMode(self):
        '''Test that if we are in record mode with at least one waypoint, then A and B buttons are active'''

        self.shot.cableCamPlaying = False
        self.shot.setButtonMappings()
        calls = [call(btn_msg.ButtonA, shots.APP_SHOT_MULTIPOINT, btn_msg.ARTOO_BITMASK_ENABLED, "Record Point\0"), call(btn_msg.ButtonB, shots.APP_SHOT_MULTIPOINT, btn_msg.ARTOO_BITMASK_ENABLED, "Finish Point\0")]
        self.shot.shotmgr.buttonManager.setArtooButton.assert_has_calls(calls)

    def testInPlayMode(self):
        '''Test that if we are in record mode with at least one waypoint, then A and B buttons are active'''

        self.shot.setButtonMappings()
        calls = [call(btn_msg.ButtonA, shots.APP_SHOT_MULTIPOINT, 0, "\0"), call(btn_msg.ButtonB, shots.APP_SHOT_MULTIPOINT, 0, "\0")]
        self.shot.shotmgr.buttonManager.setArtooButton.assert_has_calls(calls)


class TestHandleButton(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        # recordLocation will add +1 length to waypoints list
        self.shot.waypoints = []
        self.shot.recordLocation = Mock(side_effect=self.shot.waypoints.append(1))
        self.shot.enterPlayMode = Mock()

    def testHandleAButtonRecordPoint(self):
        ''' This should record a cable endpoint '''

        self.shot.handleButton(btn_msg.ButtonA, btn_msg.Press)
        self.shot.recordLocation.assert_called_with()

    def testHandleBButtonRecordPoint(self):
        ''' This should record a cable point and start cable cam'''

        self.shot.waypoints.append(1)
        self.shot.handleButton(btn_msg.ButtonB, btn_msg.Press)
        self.shot.recordLocation.assert_called_with()
        self.shot.enterPlayMode.assert_called_with()

    def testHandleBButtonDontBeginCableCam(self):
        ''' Don't enter cable if we only have 0 or 1 waypoint stored after recording a point '''

        self.shot.handleButton(btn_msg.ButtonB, btn_msg.Press)
        self.shot.recordLocation.assert_called_with()
        assert not self.shot.enterPlayMode.called


class TestHandlePathSettings(unittest.TestCase):
    
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        self.shot.estimateCruiseSpeed = Mock()     
        self.shot.setCruiseSpeed = Mock() 

        self.cableCamPlaying = True

    def testRejectIfNotInPlayMode(self):
        '''Will reject a path settings packet if we're not in play mode'''

        self.shot.cableCamPlaying = False
        self.shot.updatePathTimes = Mock()
        pathSettings = (0, .01) #packet to enter interpolate mode
        self.shot.handlePathSettings(pathSettings)
        assert not self.shot.updatePathTimes.called

    def testTryToEnterSameCameraModeInterpolateCam(self):
        '''Will not change camera modes if we're already in the requested mode'''

        self.shot.cableCamPlaying = True
        self.shot.camInterpolation = 0 # set cam to interpolate
        self.shot.yawPitchOffsetter.enableNudge = Mock()
        pathSettings = (0, .01) #packet to enter interpolate mode
        self.shot.handlePathSettings(pathSettings)
        assert not self.shot.yawPitchOffsetter.enableNudge.called

    def testTryToEnterSameCameraModeFreeCam(self):
        '''Will not change camera modes if we're already in the requested mode'''

        self.shot.cableCamPlaying = True
        self.shot.camInterpolation = 1 # set cam to free
        self.shot.yawPitchOffsetter.disableNudge = Mock()
        pathSettings = (1, .01) #packet to enter interpolate mode
        self.shot.handlePathSettings(pathSettings)
        assert not self.shot.yawPitchOffsetter.disableNudge.called

    def testEnterFreeCamFromInterpolateCam(self):
        '''Will change from interpolate cam to free cam'''

        self.shot.cableCamPlaying = True
        self.shot.camInterpolation = 0 # set cam to interpolate
        self.shot.yawPitchOffsetter.disableNudge = Mock()
        pathSettings = (1, .01) #packet to enter interpolate mode
        self.shot.handlePathSettings(pathSettings)
        self.shot.yawPitchOffsetter.disableNudge.assert_called_with(mock.ANY,mock.ANY)

    def testEnterInterpolateCamFromFreeCam(self):
        '''Will change from interpolate cam to free cam'''

        self.shot.cableCamPlaying = True
        self.shot.camInterpolation = 1 # set cam to free
        self.shot.yawPitchOffsetter.enableNudge = Mock()
        pathSettings = (0, .01) #packet to enter interpolate mode
        self.shot.handlePathSettings(pathSettings)
        self.shot.yawPitchOffsetter.enableNudge.assert_called_with()


class TestSetCruiseSpeed(unittest.TestCase):

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

    def testSetNewPosSpeed(self):
        '''Test setting a new positive speed'''

        self.shot.storedCruiseSpeed = 4
        self.shot.setCruiseSpeed(speed = 5)
        self.assertEqual(5,self.shot.storedCruiseSpeed)

    def testSetNewNegSpeed(self):
        '''Test setting a new negative speed'''

        self.shot.storedCruiseSpeed = 4
        self.shot.setCruiseSpeed(speed = -5)
        self.assertEqual(-5,self.shot.storedCruiseSpeed)

    def testSetNewZeroSpeed(self):
        '''Test setting a new zero speed'''

        self.shot.storedCruiseSpeed = 4
        self.shot.setCruiseSpeed(speed = 0)
        self.assertEqual(0,self.shot.storedCruiseSpeed)

    def testSetNewCruiseState(self):
        '''Test setting a new cruise state'''

        self.shot.cruiseState = 1
        self.shot.setCruiseSpeed(state = 0)
        self.assertEqual(0,self.shot.cruiseState)


class TestUpdatePathTimes(unittest.TestCase):

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.appMgr = Mock()

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

    def testNoSpline(self):
        '''if a spline has not been defined yet, then return immediately'''

        self.shot.cable = None
        self.shot.updatePathTimes()
        assert not self.shot.shotmgr.appMgr.sendPacket.called

    @mock.patch('struct.pack')
    def testUpdate(self, struct_pack):
        '''Test normal update operation'''
        self.shot.cable = [1]
        self.shot.minTime = 10
        self.shot.maxTime = 60
        self.shot.updatePathTimes()
        struct_pack.assert_called_with('<IIff', app_packet.SOLO_SPLINE_DURATIONS, 8, 10, 60)


class TestUpdatePlaybackStatus(unittest.TestCase):

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.appMgr = Mock()

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        #Mock cable
        self.shot.cable = mock.create_autospec(CableController)
        self.shot.cable.currentP = 0.5
        self.shot.cable.currentSeg = 0
        self.shot.cable.speed = 0

        #cruiseState
        self.shot.cruiseState = 0

    def testNoCableYetForPlayback(self):
        '''Don't send anything to app if spline doesn't exist yet'''

        self.shot.cable = None
        self.shot.updatePlaybackStatus()
        assert not self.shot.shotmgr.appMgr.sendPacket.called


class TestHandleSeek(unittest.TestCase):

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.appMgr = Mock()

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        #value 
        self.seek = (.3, 0)

        #cable
        self.shot.cable = [1]

        #mock setCruiseSpeed
        self.shot.setCruiseSpeed = Mock()

        #mock checkToNotifyApp
        self.shot.checkToNotifyApp = Mock()

        #attaching
        self.shot.attaching = False

    def testNoCableYetForTarget(self):
        '''Don't send anything to app if app spline doesn't exist yet'''

        self.shot.cable = None
        self.shot.handleSeek(self.seek)
        assert not self.shot.shotmgr.appMgr.sendPacket.called

    def testStillAttaching(self):
        '''Test that we don't handle a seek packet if we're still attaching'''

        self.shot.attaching = True
        self.shot.handleSeek(self.seek)
        assert not self.shot.shotmgr.appMgr.sendPacket.called

    def testNominal(self):
        '''Test that the function calls checkToNotifyApp and setCruiseSpeed'''

        self.shot.handleSeek(self.seek)
        self.shot.setCruiseSpeed.assert_called_with(state = 0)
        self.shot.checkToNotifyApp.assert_called_with(notify=True)


class TestEnterRecordMode(unittest.TestCase):

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.appMgr = Mock()

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

    def testSettingValues(self):
        '''Test setting values in enterRecordMode()'''

        self.shot.enterRecordMode()
        self.assertEqual(self.shot.cableCamPlaying, False)
        self.assertEqual(self.shot.waypoints, [])


class TestEnterPlayMode(unittest.TestCase):

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.appMgr = Mock()
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        #Mock setButtonMappings
        self.shot.setButtonMappings = Mock()

        #Mock generateSplines()
        self.shot.generateSplines = Mock(return_value = True)

        #Mock cable
        self.shot.cable = mock.create_autospec(CableController)
        self.shot.cable.spline = mock.create_autospec(CatmullRom)

        #Mock sendSoloSplinePoint
        self.shot.sendSoloSplinePoint = Mock()

        #Mock enterRecordMode()
        self.shot.enterRecordMode = Mock()

        # Mock updatePathTimes()
        self.shot.updatePathTimes = Mock()

        self.loc1 = LocationGlobalRelative(37.873309, -122.302562, 10)
        self.pitch1 = 45
        self.yaw1 = 300

        self.loc2 = LocationGlobalRelative(38.873309, -123.302562, 10)
        self.pitch2 = 0
        self.yaw2 = 10

        self.loc3 = LocationGlobalRelative(39.873309, -124.302562, 10)
        self.pitch3 = 0
        self.yaw3 = 50

        self.loc4 = LocationGlobalRelative(40.873309, -125.302562, 10)
        self.pitch4 = 0
        self.yaw4 = 30

    def testAlreadyInPlayMode(self):
        '''Test that we don't initialize the cable if we're already in PLAY mode'''
        self.shot.cableCamPlaying = True
        self.shot.enterPlayMode()
        assert not self.shot.generateSplines.called

    def testMissingWaypoint(self):
        '''If waypoint list is incomplete'''
        self.shot.waypoints = [Waypoint(
            self.loc1, self.pitch1, self.yaw1), None, Waypoint(self.loc3, self.pitch3, self.yaw3)]
        self.shot.enterPlayMode()
        self.shot.enterRecordMode.assert_called_with()

    def testNotEnoughWaypoints(self):
        '''Test that we don't initialize the cable if we don't have at least 2 waypoints'''
        self.shot.waypoints = []
        self.shot.enterPlayMode()
        self.shot.enterRecordMode.assert_called_with()

    def testGenerateSplinesFails(self):
        '''If generateSplines fails, then go back to RECORD mode'''
        self.shot.generateSplines.return_value = False
        self.shot.enterPlayMode()
        self.shot.enterRecordMode.assert_called_with()

    def testSendingAppPackets(self):
        '''Make sure we're sending the correct # of packets to the app'''
        self.shot.waypoints = [Waypoint(self.loc1, self.pitch1, self.yaw1), Waypoint(
            self.loc2, self.pitch2, self.yaw2), Waypoint(self.loc3, self.pitch3, self.yaw3)]
        self.shot.cable.spline.nonDimensionalToArclength = Mock(return_value = (0, 0))
        self.shot.enterPlayMode()
        # +1 because of the SPLINE PLAY packet sent earlier
        self.assertEqual(self.shot.shotmgr.appMgr.sendPacket.call_count, 1)
        self.assertEqual(self.shot.sendSoloSplinePoint.call_count, len(self.shot.waypoints))
        self.shot.updatePathTimes.assert_called_with()

    def testSetGimbalMode(self):
        '''Test if gimbal mode is set'''
        self.shot.waypoints = [Waypoint(self.loc1, self.pitch1, self.yaw1), Waypoint(
            self.loc2, self.pitch2, self.yaw2), Waypoint(self.loc3, self.pitch3, self.yaw3)]
        self.shot.cable.spline.nonDimensionalToArclength.return_value = (0, 0)
        self.shot.enterPlayMode()  # initialize CableCam
        self.shot.vehicle.message_factory.mount_configure_encode.assert_called_with(
            0, 1,    # target system, target component
            mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,  # mount_mode
            1,  # stabilize roll
            1,  # stabilize pitch
            1,  # stabilize yaw
        )

    def testEnableRemapping(self):
        '''Test if enableRemapping is called'''
        self.shot.waypoints = [Waypoint(self.loc1, self.pitch1, self.yaw1), Waypoint(
            self.loc2, self.pitch2, self.yaw2), Waypoint(self.loc3, self.pitch3, self.yaw3)]
        self.shot.cable.spline.nonDimensionalToArclength.return_value = (
            0, 0)
        self.shot.enterPlayMode()  # initialize CableCam
        self.shot.shotmgr.rcMgr.enableRemapping.assert_called_with(True)

    def testCableCamPlaying(self):
        '''Test if cableCamPlaying flag is set to True'''
        self.shot.waypoints = [Waypoint(self.loc1, self.pitch1, self.yaw1), Waypoint(
            self.loc2, self.pitch2, self.yaw2), Waypoint(self.loc3, self.pitch3, self.yaw3)]
        self.shot.cable.spline.nonDimensionalToArclength.return_value = (
            0, 0)
        self.shot.enterPlayMode()  # initialize CableCam
        self.assertTrue(self.shot.cableCamPlaying)

class TestGenerateSplines(unittest.TestCase):

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

    # need to patch this, otherwise the object goes nuts by spawning a thread
    # and building the curvature map which stalls the unit tests
    # and the thread sometimes never exits
    @mock.patch('cableController.CableController')
    def testCWYaw(self, cableController):
        '''Test a CW move'''
        loc1 = LocationGlobalRelative(37.873309, -122.302562, 10)
        pitch1 = 45
        yaw1 = 20

        loc2 = LocationGlobalRelative(38.873309, -122.302562, 10)
        pitch2 = 0
        yaw2 = 60

        expected = [Vector2(pitch1 - (pitch2 - pitch1), yaw1 - (yaw2 - yaw1)), Vector2(
            pitch1, yaw1), Vector2(pitch2, yaw2), Vector2(pitch2 + (pitch2 - pitch1), yaw2 + (yaw2 - yaw1))]

        self.shot.waypoints.append(Waypoint(loc1, pitch1, yaw1))
        self.shot.waypoints.append(Waypoint(loc2, pitch2, yaw2))

        self.shot.generateSplines(self.shot.waypoints)

        for i in range(0, len(expected)):
            self.assertAlmostEqual(
                self.shot.camSpline.points[i].x, expected[i].x)
            self.assertAlmostEqual(
                self.shot.camSpline.points[i].y, expected[i].y)

    @mock.patch('cableController.CableController')
    def testCCWYaw(self, cableController):
        '''Test a CCW move'''
        loc1 = LocationGlobalRelative(37.873309, -122.302562, 10)
        pitch1 = 45
        yaw1 = 60

        loc2 = LocationGlobalRelative(38.873309, -122.302562, 10)
        pitch2 = 0
        yaw2 = 20

        expected = [Vector2(pitch1 - (pitch2 - pitch1), yaw1 - (yaw2 - yaw1)), Vector2(
            pitch1, yaw1), Vector2(pitch2, yaw2), Vector2(pitch2 + (pitch2 - pitch1), yaw2 + (yaw2 - yaw1))]

        self.shot.waypoints.append(Waypoint(loc1, pitch1, yaw1))
        self.shot.waypoints.append(Waypoint(loc2, pitch2, yaw2))

        self.shot.generateSplines(self.shot.waypoints)

        for i in range(0, len(expected)):
            self.assertAlmostEqual(
                self.shot.camSpline.points[i].x, expected[i].x)
            self.assertAlmostEqual(
                self.shot.camSpline.points[i].y, expected[i].y)

    @mock.patch('cableController.CableController')
    def testCWYaw360Threshold(self, cableController):
        '''Test a CW move across the 0-360 threshold'''
        loc1 = LocationGlobalRelative(37.873309, -122.302562, 10)
        pitch1 = 45
        yaw1 = 300

        loc2 = LocationGlobalRelative(38.873309, -122.302562, 10)
        pitch2 = 0
        yaw2 = 10

        expected = [Vector2(90, 230), Vector2(
            45, 300), Vector2(0, 370), Vector2(-45, 440)]

        self.shot.waypoints.append(Waypoint(loc1, pitch1, yaw1))
        self.shot.waypoints.append(Waypoint(loc2, pitch2, yaw2))

        self.shot.generateSplines(self.shot.waypoints)

        for i in range(0, len(expected)):
            self.assertAlmostEqual(
                self.shot.camSpline.points[i].x, expected[i].x)
            self.assertAlmostEqual(
                self.shot.camSpline.points[i].y, expected[i].y)

    @mock.patch('cableController.CableController')
    def testCCWYaw360Threshold(self, cableController):
        '''Test a CCW move across the 0-360 threshold'''
        loc1 = LocationGlobalRelative(37.873309, -122.302562, 10)
        pitch1 = 45
        yaw1 = 10

        loc2 = LocationGlobalRelative(38.873309, -122.302562, 10)
        pitch2 = 0
        yaw2 = 300

        expected = [Vector2(90, 80), Vector2(
            45, 10), Vector2(0, -60), Vector2(-45, -130)]

        self.shot.waypoints.append(Waypoint(loc1, pitch1, yaw1))
        self.shot.waypoints.append(Waypoint(loc2, pitch2, yaw2))

        self.shot.generateSplines(self.shot.waypoints)

        for i in range(0, len(expected)):
            self.assertAlmostEqual(
                self.shot.camSpline.points[i].x, expected[i].x)
            self.assertAlmostEqual(
                self.shot.camSpline.points[i].y, expected[i].y)

    @mock.patch('cableController.CableController')
    def testCWYaw360Threshold6PtCable(self, cableController):
        '''Test a CCW move across the 0-360 threshold with more than 2 cable points'''
        loc1 = LocationGlobalRelative(37.873309, -122.302562, 10)
        pitch1 = 45
        yaw1 = 300

        loc2 = LocationGlobalRelative(38.873309, -123.302562, 10)
        pitch2 = 0
        yaw2 = 10

        loc3 = LocationGlobalRelative(39.873309, -124.302562, 10)
        pitch3 = 0
        yaw3 = 50

        loc4 = LocationGlobalRelative(40.873309, -125.302562, 10)
        pitch4 = 0
        yaw4 = 30

        loc5 = LocationGlobalRelative(42.873309, -127.302562, 10)
        pitch5 = 0
        yaw5 = 10

        loc6 = LocationGlobalRelative(43.873309, -128.302562, 10)
        pitch6 = 0
        yaw6 = 350

        expected = [Vector2(90, 230), Vector2(45, 300), Vector2(0, 370), Vector2(
            0, 410), Vector2(0, 390), Vector2(0, 370), Vector2(0, 350), Vector2(0, 330)]

        self.shot.waypoints.append(Waypoint(loc1, pitch1, yaw1))
        self.shot.waypoints.append(Waypoint(loc2, pitch2, yaw2))
        self.shot.waypoints.append(Waypoint(loc3, pitch3, yaw3))
        self.shot.waypoints.append(Waypoint(loc4, pitch4, yaw4))
        self.shot.waypoints.append(Waypoint(loc5, pitch5, yaw5))
        self.shot.waypoints.append(Waypoint(loc6, pitch6, yaw6))

        self.shot.generateSplines(self.shot.waypoints)

        for i in range(0, len(expected)):
            self.assertAlmostEqual(
                self.shot.camSpline.points[i].x, expected[i].x)
            self.assertAlmostEqual(
                self.shot.camSpline.points[i].y, expected[i].y)


class TestEstimateTime(unittest.TestCase):

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        #Mock cable
        self.shot.cable = mock.create_autospec(CableController)
        self.shot.cable.spline = mock.create_autospec(CatmullRom)
        self.shot.cable.spline.totalArcLength = 10 #meters

    def testEstimate(self):
        '''Makes a quick estimate of time for cable'''
        retVal = self.shot.estimateTime(2) # 2 m/s
        self.assertEqual(retVal, 6.835325870964494)


#class TestEstimateCruiseSpeed TODO


class TestHandleAttach(unittest.TestCase):

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        #Mock cable
        self.shot.cable = mock.create_autospec(CableController)
        self.shot.cable.spline = mock.create_autospec(CatmullRom)

        self.loc1 = LocationGlobalRelative(37.873309, -122.302562, 10)
        self.pitch1 = 45
        self.yaw1 = 300
        self.waypt1 = Waypoint(self.loc1,self.pitch1,self.yaw1)

        self.loc2 = LocationGlobalRelative(38.873309, -123.302562, 10)
        self.pitch2 = 0
        self.yaw2 = 10
        self.waypt2 = Waypoint(self.loc2,self.pitch2,self.yaw2)

        self.loc3 = LocationGlobalRelative(39.873309, -124.302562, 10)
        self.pitch3 = 0
        self.yaw3 = 50
        self.waypt3 = Waypoint(self.loc3,self.pitch3,self.yaw3)

    def testCableCamNotPlaying(self):
        '''Do not try to attach to cable if play flag is false'''
        self.shot.vehicle.commands.goto = Mock()
        self.shot.cableCamPlaying = False # not playing
        attach = (0,)
        self.shot.handleAttach(attach)
        assert not self.shot.vehicle.commands.goto.called

    def testInvalidRangeTooHigh(self):
        '''Do not try to attach to cable if requested index is out of range'''
        self.shot.vehicle.commands.goto = Mock()
        self.shot.cableCamPlaying = True
        self.shot.waypoints = [self.waypt1,self.waypt2] #2 waypoints
        attach = (2,) # out of range index
        self.shot.handleAttach(attach)
        assert not self.shot.vehicle.commands.goto.called

    def testGoToFirstIndex(self):
        '''When attaching to first index, currentSegment is 0 and currentU is 0'''
        self.shot.vehicle.commands.goto = Mock()
        self.shot.cableCamPlaying = True
        self.shot.waypoints = [self.waypt1,self.waypt2,self.waypt3] #3 waypoints, 2 segments (0&1)
        attach = (0,) # first index
        self.shot.handleAttach(attach)
        self.shot.cable.spline.nonDimensionalToArclength.assert_called_with(0,0)

    def testGoToMiddleIndex(self):
        '''When attaching to middle index, currentSegment is lastindex-1 and currentU is 0'''
        self.shot.vehicle.commands.goto = Mock()
        self.shot.cableCamPlaying = True
        self.shot.waypoints = [self.waypt1,self.waypt2,self.waypt3] #3 waypoints, 2 segments (0&1)
        attach = (1,) # middle index
        self.shot.handleAttach(attach)
        self.shot.cable.spline.nonDimensionalToArclength.assert_called_with(1,0)

    def testGoToLastIndex(self):
        '''When attaching to last index, currentSegment is lastindex-1 and currentU is 1'''
        self.shot.vehicle.commands.goto = Mock()
        self.shot.cableCamPlaying = True
        self.shot.waypoints = [self.waypt1,self.waypt2,self.waypt3] #3 waypoints, 2 segments (0&1)
        attach = (2,) # last index
        self.shot.handleAttach(attach)
        self.shot.cable.spline.nonDimensionalToArclength.assert_called_with(1,1)



class TestListenForAttach(unittest.TestCase):

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

    @patch('location_helpers.getDistanceFromPoints3d')
    def testAttachIndexNotSet(self,mock_getDistanceFromPoints3d):
        '''Do not try to listen for attachment if attachIndex is -1'''
        self.shot.attachIndex = -1
        self.shot.listenForAttach()
        assert not mock_getDistanceFromPoints3d.called

class TestCheckToNotifyApp(unittest.TestCase):

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

        #Mock updatePlaybackStatus
        self.shot.updatePlaybackStatus = Mock()

        #Mock cable
        self.shot.cable = mock.create_autospec(CableController)
        self.shot.cable.reachedTarget = Mock(return_value = False)
        self.shot.cable.currentSeg = 1
        self.shot.cable.speed = 1

        #Mock setCruiseSpeed
        self.shot.setCruiseSpeed = Mock()
        self.shot.targetP = 1

    def testEverySecond(self):
        '''Notify app every second regardless'''
        self.shot.ticksToNotify = 0
        for i in range(int(UPDATE_RATE)+1):
            self.shot.checkToNotifyApp()
        self.shot.updatePlaybackStatus.assert_called_with()

    def testDoNotNotify(self):
        '''Don't notify if there's no reason to'''
        self.shot.checkToNotifyApp()
        assert not self.shot.updatePlaybackStatus.called

    def testDoNotify(self):
        '''Do notify if there's a reason to'''
        self.shot.checkToNotifyApp(True)
        assert self.shot.updatePlaybackStatus.called


class TestHandlePacket(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = Mock()

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.goproManager = Mock()
        shotmgr.appMgr = Mock(specs=['recv'])
        shotmgr.appMgr.client = Mock(specs=['recv'])

        #Run the shot constructor
        self.shot = multipoint.MultipointShot(vehicle, shotmgr)

    def testSoloSplineRecord(self):
        ''' Test parsing a solo spline record '''
        self.shot.shotmgr.currentShot = shots.APP_SHOT_MULTIPOINT
        value = ''
        self.shot.enterRecordMode = Mock()
        self.shot.handlePacket(app_packet.SOLO_SPLINE_RECORD, 0, value)
        self.shot.enterRecordMode.assert_called_with()

    def testSoloSplinePlay(self):
        ''' Test parsing a solo spline play '''
        self.shot.shotmgr.currentShot = shots.APP_SHOT_MULTIPOINT
        value = ''
        self.shot.enterPlayMode = Mock()
        self.shot.handlePacket(app_packet.SOLO_SPLINE_PLAY, 0, value)
        self.shot.enterPlayMode.assert_called_with()

    def testSoloSplinePoint(self):
        ''' Test parsing a solo spline point '''

        self.shot.shotmgr.currentShot = shots.APP_SHOT_MULTIPOINT
        value = struct.pack('<hfIddffffh',0,1,1,1,1,1,1,1,1,1)
        self.shot.loadSplinePoint = Mock()
        self.shot.handlePacket(app_packet.SOLO_SPLINE_POINT, 44, value)
        self.shot.loadSplinePoint.assert_called_with((0,1,1,1,1,1,1,1,1,1))

    def testSoloSplineSeek(self):
        ''' Test parsing a solo spline seek '''

        self.shot.shotmgr.currentShot = shots.APP_SHOT_MULTIPOINT
        value = struct.pack('<fi',1,1)
        self.shot.handleSeek = Mock()
        self.shot.handlePacket(app_packet.SOLO_SPLINE_SEEK, 8, value)
        self.shot.handleSeek.assert_called_with((1,1))

    def testSoloSplinePathSettings(self):
        ''' Test parsing a solo spline path settings '''

        self.shot.shotmgr.currentShot = shots.APP_SHOT_MULTIPOINT
        value = struct.pack('<If',1,1)
        self.shot.handlePathSettings = Mock()
        self.shot.handlePacket(app_packet.SOLO_SPLINE_PATH_SETTINGS, 8, value)
        self.shot.handlePathSettings.assert_called_with((1,1))

    def testSoloSplineAttach(self):
        ''' Test parsing a solo spline attach '''

        self.shot.shotmgr.currentShot = shots.APP_SHOT_MULTIPOINT
        value = struct.pack('<I',1)
        self.shot.handleAttach = Mock()
        self.shot.handlePacket(app_packet.SOLO_SPLINE_ATTACH, 4, value)
        self.shot.handleAttach.assert_called_with((1,))

