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

import orbit
from orbit import *

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

        '''Create a mock shotManager object'''
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds
        shotmgr.rcMgr = Mock(specs=['remapper'])

        '''Run the shot constructor'''
        self.shot = orbit.OrbitShot(vehicle, shotmgr)

    def testInit(self):
        '''Test that the shot initialized properly'''

        # vehicle object should be created (not None)
        self.assertNotEqual(self.shot.vehicle, None)

        # shotManager object should be created (not None)
        self.assertNotEqual(self.shot.shotmgr, None)

        # roi should be None
        self.assertEqual(self.shot.roi, None)

        # pathController should be None
        self.assertEqual(self.shot.pathController, None)

        # ticksPaddleCentered should be initialized to infinity
        self.assertEqual(self.shot.ticksPaddleCentered, float('inf'))

        # pathHandler should be None
        self.assertEqual(self.shot.pathHandler, None)

        # shotmgr.getParam should be called thrice
        # once for maxClimbRate and once for maxAlt and once for FENCE_ENABLE
        calls = [call("PILOT_VELZ_MAX", DEFAULT_PILOT_VELZ_MAX_VALUE), call("FENCE_ALT_MAX", DEFAULT_FENCE_ALT_MAX), call("FENCE_ENABLE", DEFAULT_FENCE_ENABLE)]
        self.shot.shotmgr.getParam.assert_has_calls(calls)

class TestHandleRCs(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = orbit.OrbitShot(vehicle, shotmgr)

        #set roi
        self.shot.roi = LocationGlobalRelative(37.873168,-122.302062, 0) #3DR

        #Mock the pathHandler object
        self.shot.pathHandler = mock.create_autospec(pathHandler.PathHandler)
        self.shot.pathHandler.cruiseSpeed = 0

        #Mock the pathController object
        self.shot.pathController = mock.create_autospec(OrbitController)
        self.shot.pathController.move.return_value = (LocationGlobalRelative(37.873168,-122.302062, 0),Vector3(0,0,0))

        #Neutral sticks
        throttle = 0.0
        roll = 0.0
        pitch = 0.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]

    def testNoROI(self):
        '''If not ROI is set then do NOT continue'''

        self.shot.roi = None
        self.shot.handleRCs(self.channels)
        assert not self.shot.pathController.called

    def testSetPositionMsg(self):
        '''Test that we're sending a lat,lon,alt/x,y,z vel to APM'''

        self.shot.handleRCs(self.channels)
        self.shot.vehicle.message_factory.set_position_target_global_int_encode.assert_called_with(
                     0,       # time_boot_ms (not used)
                     0, 1,    # target system, target component
                     mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, # frame
                     0b0000110111000000, # type_mask - enable pos/vel
                     37.873168*1E7, -122.302062*1E7, 0, # x, y, z positions
                     0, 0, 0, # x, y, z velocity in m/s
                     0, 0, 0, # x, y, z acceleration (not used)
                     0, 0)    # yaw, yaw_rate (not used)
        self.shot.vehicle.send_mavlink.assert_called_with(mock.ANY)

    def testCallsetROIAltitude(self):
        '''Tests that we're calling setROIAltitude() with correct channels'''

        self.channels[5] = 0.5
        self.channels[7] = 0.75
        self.shot.setROIAltitude = Mock()
        self.shot.handleRCs(self.channels)
        self.shot.setROIAltitude.assert_called_with(0.5,0.75)


    def testsetROIAltitudeMsg(self):
        '''Test that we're sending an roi lat,lon,alt to APM''' 

        self.shot.handleRCs(self.channels)
        self.shot.vehicle.message_factory.command_long_encode.assert_called_with(
                                                        0, 1,    # target system, target component
                                                        mavutil.mavlink.MAV_CMD_DO_SET_ROI, #command
                                                        0, #confirmation
                                                        0, 0, 0, 0, #params 1-4
                                                        self.shot.roi.lat,
                                                        self.shot.roi.lon,
                                                        self.shot.roi.alt
                                                        )
        self.shot.vehicle.send_mavlink.assert_called_with(mock.ANY)

class TestAddLocation(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.appMgr = Mock()
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = orbit.OrbitShot(vehicle, shotmgr)

        #Mock initOrbitShot
        self.shot.initOrbitShot = Mock()

    @mock.patch('location_helpers.getDistanceFromPoints', return_value = 10)
    @mock.patch('location_helpers.calcAzimuthFromPoints', return_value = 45)
    def testCallingLocationHelperFunctions(self, location_helpers_calcAzimuthFromPoints, location_helpers_getDistanceFromPoints):
        '''Make sure all location_helpers functions are called'''
        self.shot.addLocation(LocationGlobalRelative(37.873168,-122.302062, 0))
        location_helpers_getDistanceFromPoints.assert_called_with(self.shot.roi, self.shot.vehicle.location.global_relative_frame)
        location_helpers_calcAzimuthFromPoints.assert_called_with(self.shot.roi, self.shot.vehicle.location.global_relative_frame)
    
    @mock.patch('orbitController.OrbitController', return_value = mock.create_autospec(OrbitController))
    def testCreatingPathController(self, OrbitController):
        '''Test that the pathController object is instantiated'''
        self.shot.addLocation(LocationGlobalRelative(37.873168,-122.302062, 0))
        self.assertNotEqual(self.shot.pathController, None)
        self.shot.pathController.setOptions.assert_called_with(maxAlt = mock.ANY, maxClimbRate = mock.ANY)

    def testNoPreviouslysetROIAltitude(self):
        '''If no roi has been set previously, then call initOrbitShot()'''
        self.shot.roi = None
        self.shot.initOrbitShot = Mock()
        self.shot.addLocation(LocationGlobalRelative(37.873168,-122.302062, 0))
        self.assertEqual(self.shot.roi.lat, 37.873168)
        self.assertEqual(self.shot.roi.lon, -122.302062)
        self.assertEqual(self.shot.roi.alt, 0)
        self.shot.initOrbitShot.assert_called_with()

    def testOverwriteROI(self):
        '''If an ROI is already set, overwrite it & call initOrbitShot()'''
        self.shot.roi = LocationGlobalRelative(37.873168,-122.302062, 0)
        self.shot.initOrbitShot = Mock()
        self.shot.addLocation(LocationGlobalRelative(37.873169,-122.302063, 5))
        self.assertEqual(self.shot.roi.lat, 37.873169)
        self.assertEqual(self.shot.roi.lon, -122.302063)
        self.assertEqual(self.shot.roi.alt, 5)
        assert self.shot.initOrbitShot.called

    def testSendROIToApp(self):
        '''Send the added ROI to the app as confirmation'''
        self.shot.roi = LocationGlobalRelative(37.873168,-122.302062, 0)
        self.shot.addLocation(LocationGlobalRelative(37.873169,-122.302063, 5))
        expectedPacket = struct.pack('<IIddf', app_packet.SOLO_MESSAGE_LOCATION, 20, self.shot.roi.lat, self.shot.roi.lon, self.shot.roi.alt)
        self.shot.shotmgr.appMgr.sendPacket.assert_called_with(expectedPacket)

class TestSpotLock(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = orbit.OrbitShot(vehicle, shotmgr)

        #Mock addLocation()
        self.shot.addLocation = Mock()

    @mock.patch('location_helpers.getSpotLock', return_value = LocationGlobalRelative(37.873168,-122.302062, 0))
    @mock.patch('camera.getYaw', return_value = 0)
    @mock.patch('camera.getPitch', return_value = 0)
    def testIfPitchIsZero(self, camera_getPitch, camera_getYaw, location_helpers_getSpotLock):
        '''If camera pitch is zero then set an ROI at min angle'''
        self.shot.spotLock()
        location_helpers_getSpotLock.assert_called_with(self.shot.vehicle.location.global_relative_frame, orbit.SHALLOW_ANGLE_THRESHOLD,0)

    @mock.patch('location_helpers.getSpotLock', return_value = LocationGlobalRelative(37.873168,-122.302062, 0))
    @mock.patch('camera.getYaw', return_value = 0)
    @mock.patch('camera.getPitch', return_value = orbit.SHALLOW_ANGLE_THRESHOLD + 1)
    def testIfPitchGreaterThanShallowAngleThreshold(self, camera_getPitch, camera_getYaw, location_helpers_getSpotLock):
        '''If camera pitch is greater than SHALLOW_ANGLE_THRESHOLD'''
        self.shot.spotLock()
        location_helpers_getSpotLock.assert_called_with(self.shot.vehicle.location.global_relative_frame, orbit.SHALLOW_ANGLE_THRESHOLD, camera_getYaw(self.shot.vehicle))


    @mock.patch('location_helpers.getSpotLock', return_value = LocationGlobalRelative(37.873168,-122.302062, 0))
    @mock.patch('camera.getYaw', return_value = 0)
    @mock.patch('camera.getPitch', return_value = orbit.SHALLOW_ANGLE_THRESHOLD - 1)
    def testIfPitchLessThanShallowAngleThreshold(self, camera_getPitch, camera_getYaw, location_helpers_getSpotLock):
        '''If camera pitch is greater than SHALLOW_ANGLE_THRESHOLD'''
        self.shot.spotLock()
        location_helpers_getSpotLock.assert_called_with(self.shot.vehicle.location.global_relative_frame, orbit.SHALLOW_ANGLE_THRESHOLD-1, camera_getYaw(self.shot.vehicle))

    def testCallAddLocation(self):
        '''Test if addLocation is called (value not checked in this test)'''
        self.shot.spotLock()
        self.shot.addLocation.assert_called_with(mock.ANY)

class TestinitOrbitShot(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = orbit.OrbitShot(vehicle, shotmgr)

        #Set ROI
        self.shot.roi =  LocationGlobalRelative(37.873168,-122.302062, 0)

        #Mock setButtonMappings()
        self.shot.setButtonMappings = Mock()

    def testEnterGUIDEDMode(self):
        '''Test that initOrbitShot() puts us into GUIDED mode'''
        self.shot.initOrbitShot()
        self.assertEqual(self.shot.vehicle.mode.name, "GUIDED")

    def testSettingGimbalROI(self):
        '''Test that we're setting the roi as the gimbal ROI'''
        self.shot.initOrbitShot()
        expectedMsg = self.shot.vehicle.message_factory.mount_configure_encode(
                    0, 1,    # target system, target component
                    mavutil.mavlink.MAV_MOUNT_MODE_GPS_POINT,  #mount_mode
                    1,  # stabilize roll
                    1,  # stabilize pitch
                    1,  # stabilize yaw
                    )
        self.shot.vehicle.send_mavlink.assert_called_with(expectedMsg)

    def testEnableRemapping(self):
        '''Test that remapping is enabled'''
        self.shot.initOrbitShot()
        self.shot.shotmgr.rcMgr.enableRemapping.assert_called_with(True)

    def testCreatePathHandlerObject(self):
        '''Test that we are creating the pathHandler object'''
        self.shot.initOrbitShot()
        self.assertNotEqual(self.shot.pathHandler, None)

    def testSetButtonMappings(self):
        '''Test that we call setButtonMappings'''
        self.shot.initOrbitShot()
        self.shot.setButtonMappings.assert_called_with()

class TestSetButtonMappings(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.buttonManager = Mock()
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = orbit.OrbitShot(vehicle, shotmgr)

    def testNoROI(self):
        '''Test setButtonMappings() before an ROI is set'''
        self.shot.setButtonMappings()
        calls = [call(btn_msg.ButtonA, shots.APP_SHOT_ORBIT, btn_msg.ARTOO_BITMASK_ENABLED, "Begin\0"), call(btn_msg.ButtonB, shots.APP_SHOT_ORBIT, 0, "\0")]
        self.shot.shotmgr.buttonManager.setArtooButton.assert_has_calls(calls)

    def testROISet(self):
        '''Test setButtonMappings() after an ROI is set'''
        self.shot.roi =  LocationGlobalRelative(37.873168,-122.302062, 0)        
        self.shot.setButtonMappings()
        calls = [call(btn_msg.ButtonA, shots.APP_SHOT_ORBIT, 0, "\0"), call(btn_msg.ButtonB, shots.APP_SHOT_ORBIT, 0, "\0")]
        self.shot.shotmgr.buttonManager.setArtooButton.assert_has_calls(calls)

class TestHandleButton(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = orbit.OrbitShot(vehicle, shotmgr)
        self.shot.spotLock = Mock()
        self.shot.updateAppOptions = Mock()

    def testAButtonNoROI(self):
        '''Test A button press without roi set'''
        self.shot.handleButton(btn_msg.ButtonA, btn_msg.Press)
        self.shot.spotLock.assert_called_with()

    def testAButtonROISet(self):
        '''Test A Button press with roi set'''
        self.shot.roi = LocationGlobalRelative(37.873168,-122.302062, 0)
        self.shot.handleButton(btn_msg.ButtonA, btn_msg.Press)
        assert not self.shot.spotLock.called

    def testPauseButtonNoPathHandler(self):
        '''Test B Button press without pathHandler set'''
        self.shot.handleButton(btn_msg.ButtonLoiter, btn_msg.Press)
        self.shot.shotmgr.notifyPause.assert_called_with(False)

    def testPauseButtonPathHandlerSet(self):
        '''Test B Button press with pathHandler set'''
        self.shot.pathHandler = mock.create_autospec(pathHandler.PathHandler)
        self.shot.handleButton(btn_msg.ButtonLoiter, btn_msg.Press)
        self.shot.pathHandler.togglePause.assert_called_with()
        self.shot.updateAppOptions.assert_called_with()
        self.shot.shotmgr.notifyPause.assert_called_with(True)


class TestHandlePacket(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = orbit.OrbitShot(vehicle, shotmgr)

        #Mock pathHandler object
        self.shot.pathHandler = mock.create_autospec(pathHandler.PathHandler)

    @mock.patch('struct.unpack')
    def testNoPathHandler(self, struct_unpack):
        '''Test if pathHandler isn't set yet'''
        self.shot.pathHandler = None
        options = struct.pack('<f', 0.0)
        self.shot.handlePacket(app_packet.SOLO_SHOT_OPTIONS, 4, options)
        assert not struct_unpack.called

    def testCruiseSpeedSet0(self):
        '''Test setting cruiseSpeed to zero'''
        options = struct.pack('<f', 0.0)
        self.shot.handlePacket(app_packet.SOLO_SHOT_OPTIONS, 4, options)
        self.shot.pathHandler.setCruiseSpeed.assert_called_with(0.0)

    def testCruiseSpeedSet6(self):
        '''Test setting cruiseSpeed to 6'''
        options = struct.pack('<f', 6.0)
        self.shot.handlePacket(app_packet.SOLO_SHOT_OPTIONS, 4, options)
        self.shot.pathHandler.setCruiseSpeed.assert_called_with(6.0)

class TestUpdateAppOptions(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.appMgr = Mock()
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = orbit.OrbitShot(vehicle, shotmgr)

        #Mock pathHandler object
        self.shot.pathHandler = mock.create_autospec(pathHandler.PathHandler)
        self.shot.pathHandler.cruiseSpeed = 6

    def testSendToApp(self):
        '''Test sending cruiseSpeed of 6 to the app'''
        self.shot.updateAppOptions()
        expectedPacket = struct.pack('<IIf', app_packet.SOLO_SHOT_OPTIONS, 4, 6)
        self.shot.shotmgr.appMgr.sendPacket.assert_called_with(expectedPacket)

class TestsetROIAltitude(unittest.TestCase):
    ARBITRARY_HEADING = 34.8
    DISTANCE = 97.5

    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = orbit.OrbitShot(vehicle, shotmgr)

        #Mock pathController
        self.shot.pathController = mock.create_autospec(OrbitController)
        self.shot.pathController.radius = self.DISTANCE

        #set vehicle location
        self.shot.vehicle.location.global_relative_frame = LocationGlobalRelative(-4.897465, 111.4894, 10.0)

        #set mount status
        self.shot.vehicle.mount_status = [-20.0, 40.0, 30.0]

        #set ROI
        self.shot.roi = location_helpers.newLocationFromAzimuthAndDistance(self.shot.vehicle.location.global_relative_frame, self.ARBITRARY_HEADING, self.DISTANCE)

    def testNoGimbalNoChange(self):
        """ Without a gimbal, there's no need to adjust the ROI """
        self.shot.vehicle.mount_status = [None, None, None]
        self.shot.roi.alt = 13.0
        self.shot.setROIAltitude(0.5, 0.2)
        self.assertEquals( self.shot.ROIAltitudeOffset, 0 )

    def testROI0Degrees(self):
        """ Passing in 1.0 to setROIAltitude should result in an ROI altitude equal to the vehicle's current altitude """
        self.shot.roi.alt = 0.0
        self.shot.setROIAltitude(1.0, 0.5)
        self.assertEquals( self.shot.ROIAltitudeOffset, self.shot.vehicle.location.global_relative_frame.alt )

    def testROI90Degrees(self):
        """ Passing in -1.0 to setROIAltitude should result in an ROI altitude that is MAX_ALT_DIFF below our altitude (we basically want to point straight down) """
        self.shot.roi.alt = 0.0
        self.shot.setROIAltitude(-1.0, -1.0)
        self.assertEquals( self.shot.ROIAltitudeOffset, self.shot.vehicle.location.global_relative_frame.alt - orbit.MAX_ALT_DIFF )

    def testROI45Degrees(self):
        """ Passing in 0.0 to setROIAltitude should result in an ROI altitude that is DISTANCE lower than our altitude (45 degree angle) """
        self.shot.roi.alt = -50.0
        self.shot.setROIAltitude(0.0, 1.0)
        self.assertAlmostEqual(self.shot.ROIAltitudeOffset, self.shot.vehicle.location.global_relative_frame.alt - self.DISTANCE,1)

    def testROIArbitraryDegrees(self):
        """ Try passing in an arbitrary number (0.213) to setROIAltitude """
        self.shot.ticksPaddleCentered = 0
        self.shot.roi.alt = -50.0
        arbNum = 0.213
        self.shot.setROIAltitude(arbNum, 1.0)
        # convert arbNum in stick value to degrees
        deg = 45.0 - ( arbNum * 45.0 )
        altDiff = self.DISTANCE * math.tan(math.radians(deg))
        self.assertAlmostEqual(self.shot.ROIAltitudeOffset, self.shot.vehicle.location.global_relative_frame.alt - altDiff,1)

    def testROIArbitraryDegrees2(self):
        """ Try passing in another number (-0.764) to setROIAltitude """
        self.shot.ticksPaddleCentered = 0
        self.shot.roi.alt = -50.0
        arbNum = -0.764
        self.shot.setROIAltitude(arbNum, 0.0)
        # convert arbNum in stick value to degrees
        deg = arbNum * -45.0 + 45.0
        altDiff = self.DISTANCE * math.tan(math.radians(deg))
        self.assertAlmostEqual(self.shot.ROIAltitudeOffset, self.shot.vehicle.location.global_relative_frame.alt - altDiff,1)

    def testNoUserInput(self):
        """ After the user has centered the gimbal paddle for enough time, we should no longer be setting the ROI """
        self.shot.roi.alt = -50.0
        self.shot.ticksPaddleCentered = orbit.TICKS_TO_IGNORE_PADDLE
        self.shot.setROIAltitude(0.5348, 0.0)
        self.assertEqual(self.shot.ROIAltitudeOffset, 0)

    def testCenterPaddleUpsTicks(self):
        """ Centering the paddle should increase ticksPaddleCentered """
        self.shot.ticksPaddleCentered = 13
        self.shot.setROIAltitude(0.222, 0.0)
        self.assertEqual(self.shot.ticksPaddleCentered, 14)

    def testMovingPaddleClearsTicks(self):
        """ Moving the paddle should reset ticksPaddleCentered """
        self.shot.ticksPaddleCentered = 13
        self.shot.setROIAltitude(0.222, 0.1)
        self.assertEqual(self.shot.ticksPaddleCentered, 0)    


