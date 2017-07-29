# Unit tests for CableCamShot
import math
import mock
from mock import call
from mock import Mock
from mock import patch
import os
from os import sys, path
from pymavlink import mavutil
import struct
import unittest

from dronekit import LocationGlobalRelative, Vehicle
sys.path.append(os.path.realpath('..'))
import location_helpers
import cable_cam
from cable_cam import CableCamShot
from shotManagerConstants import *
import shots
# on host systems these files are located here
from sololink import btn_msg
import app_packet

ERROR = 0.1

class TestRecordLocation(unittest.TestCase):
    def setUp(self):
        self.v = mock.create_autospec(Vehicle)
        mgr = Mock(spec = ["sendPacket", "remapper", "appMgr"])
        mgr.buttonManager = Mock()
        mgr.getParam = Mock(return_value=500.0)
        self.controller = CableCamShot(self.v, mgr)

    def testRecordingLocations(self):
        """ Test recording locations """
        self.v.location.global_relative_frame = LocationGlobalRelative(37.242124, -122.12841, 15.3)
        self.controller.recordLocation()
        self.v.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.controller.recordLocation()
        self.v.location.global_relative_frame = LocationGlobalRelative(-14.654861, 108.4645, 32.6545)
        self.controller.recordLocation()

        self.assertTrue( len(self.controller.waypoints) == 3 )

    def testRecordingSameLocations(self):
        """ Test recording the same locations """
        self.v.location.global_relative_frame = LocationGlobalRelative(37.242124, -122.12841, 15.3)
        self.controller.recordLocation()
        self.controller.recordLocation()
        self.controller.recordLocation()

        self.assertTrue( len(self.controller.waypoints) == 1 )

    def testCallSetButtonMappings(self):
        """ Make sure setButtonMappings is called when recording a location """
        self.controller.setButtonMappings = Mock()
        self.v.location.global_relative_frame = LocationGlobalRelative(37.242124, -122.12841, 15.3)
        self.controller.recordLocation()
        self.controller.setButtonMappings.assert_called_with()
        self.controller.setButtonMappings = Mock()
        self.v.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.controller.recordLocation()
        self.controller.setButtonMappings.assert_called_with()

class TestHandleRCsNoWaypoints(unittest.TestCase):
    def testRCsMax(self):
        """ Test HandleRCs no waypoints """
        mgr = Mock(spec = ["sendPacket", "remapper"])
        mgr.buttonManager = Mock()
        mgr.getParam = Mock(return_value=500.0)
        self.mock_vehicle = mock.create_autospec(Vehicle)
        self.controller = CableCamShot(self.mock_vehicle, mgr)
        channels = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        self.controller.handleRCs(channels)

class TestHandleRCs(unittest.TestCase):
    def setUp(self):
        mgr = Mock(spec = ["sendPacket", "remapper", "rcMgr", "appMgr"])
        mgr.currentShot = shots.APP_SHOT_CABLECAM
        mgr.buttonManager = Mock()
        mgr.getParam = Mock(return_value=500.0)
        self.mock_vehicle = mock.create_autospec(Vehicle)
        self.controller = CableCamShot(self.mock_vehicle, mgr)
        self.mock_vehicle.location.global_relative_frame = LocationGlobalRelative(37.242124, -122.12841, 15.3)
        self.controller.recordLocation()
        self.mock_vehicle.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.controller.recordLocation()
        self.controller.yawPitchOffsetter = Mock()
        self.controller.yawPitchOffsetter.yawOffset = 2.0

    def testRCsMax(self):
        """ Test RCs Max """
        channels = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        self.controller.handleRCs(channels)

    def testRCsMin(self):
        """ Test RCs Min """
        channels = [-1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0]
        self.controller.handleRCs(channels)

    def testRCsZero(self):
        """ Test RCs Max """
        channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.controller.handleRCs(channels)

    def testRCs2(self):
        """ Test RCs Max """
        channels = [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]
        self.controller.handleRCs(channels)

    def testIsNearTarget(self):
        ''' Test that pause is activated when we reach a target '''
        channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.controller.handleRCs(channels)
        self.controller.pathHandler.isNearTarget = Mock(return_value = True)
        self.controller.pathHandler.pause = Mock()
        self.controller.handleRCs(channels)
        self.controller.pathHandler.pause.assert_called_with()


class TestHandleRCsSetupTargeting(unittest.TestCase):
    def setUp(self):
        mgr = Mock(spec = ["sendPacket", "remapper", "appMgr"])
        mgr.currentShot = shots.APP_SHOT_CABLECAM
        mgr.buttonManager = Mock()
        mgr.getParam = Mock(return_value=500.0)
        self.mock_vehicle = mock.create_autospec(Vehicle)
        self.controller = CableCamShot(self.mock_vehicle, mgr)
        self.mock_vehicle.location.global_relative_frame = LocationGlobalRelative(37.242124, -122.12841, 15.3)
        self.controller.recordLocation()
        self.mock_vehicle.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.controller.recordLocation()
        self.controller.setupTargeting = Mock()

    def testSetupTargetingCalled(self):
        """ setupTargeting should be called when we get into guided """
        self.mock_vehicle.mode.name = "GUIDED"
        channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.controller.handleRCs(channels)
        self.controller.setupTargeting.assert_called_with()
        self.assertTrue( self.controller.haveSetupTargeting )

    def testSetupTargetingNotCalled(self):
        """ Don't call this if we're not yet in guided """
        self.mock_vehicle.mode.name = "LOITER"
        channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.controller.handleRCs(channels)
        self.assertFalse( self.controller.setupTargeting.called )
        self.assertFalse( self.controller.haveSetupTargeting )

    def testSetupTargetingAlready(self):
        """ Already set up targeting """
        self.mock_vehicle.mode.name = "GUIDED"
        channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.controller.haveSetupTargeting = True
        self.controller.handleRCs(channels)
        self.assertFalse( self.controller.setupTargeting.called )


class TestHandleRCsInterpolation(unittest.TestCase):
    def setUp(self):
        mgr = Mock(spec = ["sendPacket", "remapper"])
        mgr.buttonManager = Mock()
        mgr.getParam = Mock(return_value=500.0)
        self.mock_vehicle = mock.create_autospec(Vehicle)
        self.controller = CableCamShot(self.mock_vehicle, mgr)
        self.controller.pathHandler = Mock()
        self.controller.pathHandler.MoveTowardsEndpt = Mock(return_value = (0.0, True))
        self.controller.yawPitchOffsetter = Mock()
        self.controller.waypoints = [2, 2]
        self.controller.InterpolateCamera = Mock()
        self.controller.updateAppOptions = Mock()
        self.controller.handleFreePitchYaw = Mock()

    def testInterpolateCam(self):
        """ InterpolateCamera should be called if the option is on """
        channels = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        self.controller.handleRCs(channels)
        self.controller.yawPitchOffsetter.Update.assert_called_with(channels)
        self.controller.InterpolateCamera.assert_called_with(False)
        self.assertFalse( self.controller.handleFreePitchYaw.called )

    def testFreePitchYaw(self):
        """ If the option is off, should call HandleFreePitchYaw """
        channels = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        self.controller.camInterpolation = 0
        self.controller.haveSetupTargeting = True
        self.controller.handleRCs(channels)
        self.controller.yawPitchOffsetter.Update.assert_called_with(channels)
        self.controller.handleFreePitchYaw.assert_called_with()
        self.assertFalse( self.controller.InterpolateCamera.called )


class TestSetButtonMappings(unittest.TestCase):
    def setUp(self):
        self.v = mock.create_autospec(Vehicle)
        self.v.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.mockMgr = Mock()
        self.mockMgr.buttonManager = Mock()
        self.mockMgr.getParam = Mock(return_value=500.0)
        self.controller = CableCamShot(self.v, self.mockMgr)

    def testSetButtonMappingsNoWaypoints(self):
        """ Testing setting button mappings when we have no recorded points """
        self.controller.setButtonMappings()
        calls = [call(btn_msg.ButtonA, shots.APP_SHOT_CABLECAM, btn_msg.ARTOO_BITMASK_ENABLED, "Record Point\0"), call(btn_msg.ButtonB, shots.APP_SHOT_CABLECAM, 0, "\0")]
        self.mockMgr.buttonManager.setArtooButton.assert_has_calls(calls, any_order = False)

    def testSetButtonMappings1Waypoint(self):
        """ Testing setting button mappings when we have one recorded point """
        self.controller.recordLocation()
        self.controller.setButtonMappings()
        calls = [call(btn_msg.ButtonA, shots.APP_SHOT_CABLECAM, 0, "\0"), call(btn_msg.ButtonB, shots.APP_SHOT_CABLECAM, btn_msg.ARTOO_BITMASK_ENABLED, "Record Point\0")]
        self.mockMgr.buttonManager.setArtooButton.assert_has_calls(calls, any_order = False)

    def testSetButtonMappings(self):
        """ Testing setting button mappings when we have locked on """
        self.controller.recordLocation()
        self.v.location.global_relative_frame = LocationGlobalRelative(50.13241, 10.112135, 0.0)
        self.controller.recordLocation()
        self.controller.setButtonMappings()
        calls = [call(btn_msg.ButtonA, shots.APP_SHOT_CABLECAM, 0, "\0"), call(btn_msg.ButtonB, shots.APP_SHOT_CABLECAM, 0, "\0")]
        self.mockMgr.buttonManager.setArtooButton.assert_has_calls(calls, any_order = False)

class TestHandleButton(unittest.TestCase):
    def setUp(self):
        self.v = mock.create_autospec(Vehicle)
        self.v.location.global_relative_frame = LocationGlobalRelative(48.6548694, 10.0, 0.5)
        self.v.mount_status = [-80]
        self.mockMgr = Mock()
        self.mockMgr.getParam = Mock(return_value=500.0)
        self.mockMgr.buttonManager = Mock()
        self.controller = CableCamShot(self.v, self.mockMgr)
        self.controller.updateAppOptions = Mock()

    def TestHandleAButtonRecordPoint(self):
        """ This should record a cable endpoint """
        self.controller.waypoints = []
        self.controller.recordLocation = Mock()
        self.controller.handleButton( btn_msg.ButtonA, btn_msg.Press )
        self.controller.recordLocation.assert_called_with()

    def TestHandleBButtonRecordPoint(self):
        """ With one point, button B should record a point """
        self.controller.waypoints = [5]
        self.controller.recordLocation = Mock()
        self.controller.handleButton( btn_msg.ButtonB, btn_msg.Press )
        self.controller.recordLocation.assert_called_with()

    def TestHandleAButtonDontRecordPoint(self):
        """ Already have two points, don't record a point """
        self.controller.waypoints = [1, 2]
        self.controller.recordLocation = Mock()
        self.controller.handleButton( btn_msg.ButtonA, btn_msg.Press )
        self.assertFalse( self.controller.recordLocation.called )

    def TestPauseCruise(self):
        """ pause button pauses cruising """
        self.controller.pathHandler = Mock()
        self.controller.pathHandler.cruiseSpeed = 8.0
        self.controller.updateAppOptions = Mock()
        self.controller.pathHandler.isPaused = Mock(return_value = False)
        self.controller.handleButton( btn_msg.ButtonLoiter, btn_msg.Press )
        self.controller.pathHandler.togglePause.assert_called_with()
        self.controller.updateAppOptions.assert_called_with()

    def TestResumeCruise(self):
        '''pause button resume cruising if already in pause'''
        self.controller.pathHandler = Mock()
        self.controller.pathHandler.cruiseSpeed = 0.0
        self.controller.handleButton( btn_msg.ButtonLoiter, btn_msg.Press )
        self.controller.pathHandler.togglePause.assert_called_with()
        self.controller.updateAppOptions.assert_called_with()

    def TestNotifyPauseLoiter(self):
        self.controller.pathHandler = None
        self.controller.handleButton(btn_msg.ButtonLoiter, btn_msg.Press)
        self.controller.shotmgr.notifyPause.assert_called_with(False)

    def TestNotifyPauseGuided(self):
        self.controller.pathHandler = Mock()
        self.controller.handleButton(btn_msg.ButtonLoiter, btn_msg.Press)
        self.controller.shotmgr.notifyPause.assert_called_with(True)


class TestInterpolateCamera(unittest.TestCase):
    def setUp(self):
        self.v = mock.create_autospec(Vehicle)
        self.v.location.global_relative_frame = LocationGlobalRelative(-48.5468695, 5.68464, 10.5)
        self.v.mount_status = [-80]
        self.mockMgr = Mock()
        self.mockMgr.buttonManager = Mock()
        self.mockMgr.getParam = Mock(return_value=500.0)
        self.controller = CableCamShot(self.v, self.mockMgr)
        loc2 = location_helpers.newLocationFromAzimuthAndDistance(self.v.location.global_relative_frame, 23.4, 25.0)
        self.startYaw = 12.4
        self.startPitch = -16.7
        waypt1 = cable_cam.Waypoint( loc2, self.startYaw, self.startPitch )
        self.controller.waypoints.append( waypt1 )
        self.endYaw = 175.4
        self.endPitch = -83.4
        waypt2 = cable_cam.Waypoint( self.v.location.global_relative_frame, self.endYaw, self.endPitch )
        self.controller.waypoints.append( waypt2 )
        self.controller.deadReckoningTicks = 0
        self.controller.accel = 0.0
        self.controller.totalDistance = location_helpers.getDistanceFromPoints3d(
                self.v.location.global_relative_frame, loc2)
        self.v.message_factory = Mock()
        # turn off dead reckoning
        self.v.groundspeed = 0.0
        self.controller.desiredSpeed = 0.0

    def TestInterp0(self):
        """ Test when we're at 0 on the cable """
        self.controller.lastPerc = 0.0
        with patch('location_helpers.getDistanceFromPoints3d', return_value=0.0):
            self.controller.InterpolateCamera( True )

            self.v.message_factory.mount_control_encode.assert_called_with(
                                            0, 1,    # target system, target component
                                            self.startPitch * 100, # pitch
                                            0.0, # roll
                                            1239.9999999999977, # yaw
                                            0 # save position
                                            )


    def TestInterp100(self):
        """ Test when we're at 100 on the cable """
        self.controller.lastPerc = 1.0
        with patch('location_helpers.getDistanceFromPoints3d', return_value=self.controller.totalDistance):
            self.controller.InterpolateCamera( True )

            self.v.message_factory.mount_control_encode.assert_called_with(
                                            0, 1,    # target system, target component
                                            self.endPitch * 100, # pitch
                                            0.0, # roll
                                            self.endYaw * 100, # yaw
                                            0 # save position
                                            )


    def TestInterp44(self):
        """ Test when we're at 44 on the cable """
        self.controller.lastPerc = 0.44
        self.controller.yawDirection = 1
        with patch('location_helpers.getDistanceFromPoints3d', return_value=self.controller.totalDistance * 0.44):
            self.controller.InterpolateCamera( True )

            pitch = ( ( self.startPitch * 0.56 ) + ( self.endPitch * 0.44) ) * 100
            yaw = ( ( self.startYaw * 0.56 ) + ( self.endYaw * 0.44) ) * 100

            self.v.message_factory.mount_control_encode.assert_called_with(
                                            0, 1,    # target system, target component
                                            pitch, # pitch
                                            0.0, # roll
                                            yaw, # yaw
                                            0 # save position
                                            )

    def TestInterp23NoGimbal(self):
        """ Test when we're at 23\% on the cable, no gimbal """
        self.controller.lastPerc = 0.23
        self.controller.yawDirection = 1
        self.v.mount_status = [None]
        with patch('location_helpers.getDistanceFromPoints3d', return_value=self.controller.totalDistance * 0.23):
            self.controller.InterpolateCamera( True )

            yaw = ( ( self.startYaw * 0.77 ) + ( self.endYaw * 0.23) )

            self.assertFalse( self.v.message_factory.mount_control_encode.called )
            self.v.message_factory.command_long_encode.assert_called_with(
                                            0, 0,    # target system, target component
                                            mavutil.mavlink.MAV_CMD_CONDITION_YAW, #command
                                            0, #confirmation
                                            yaw, # param 1 - target angle
                                            cable_cam.YAW_SPEED, # param 2 - yaw speed
                                            1, # param 3 - direction
                                            0.0, # relative offset
                                            0, 0, 0 # params 5-7 (unused)
                                            )


class TestHandlePacket(unittest.TestCase):
    def setUp(self):
        self.v = mock.create_autospec(Vehicle)
        self.v.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.mockMgr = Mock()
        self.mockMgr.buttonManager = Mock()
        self.mockMgr.getParam = Mock(return_value=500.0)
        self.controller = CableCamShot(self.v, self.mockMgr)
        self.controller.pathHandler = Mock()
        self.controller.setupTargeting = Mock()

    def testHandleCamInterpolationOn(self):
        """ Should call setup targeting """
        self.controller.camInterpolation = 0
        options = struct.pack('<HHf', 1, 1, 2.3)
        self.controller.handlePacket(app_packet.SOLO_CABLE_CAM_OPTIONS, 8, options)
        self.controller.setupTargeting.assert_called_with()

    def testHandleCamInterpolationSame(self):
        """ Don't call setup targeting if we have that value already """
        self.controller.camInterpolation = 1
        options = struct.pack('<HHf', 1, 1, 2.3)
        self.controller.handlePacket(app_packet.SOLO_CABLE_CAM_OPTIONS, 8, options)
        self.assertFalse( self.controller.setupTargeting.called )

    def testSetYawDir(self):
        """ Should set our yaw direction """
        options = struct.pack('<HHf', 1, 1, 2.3)
        self.controller.handlePacket(app_packet.SOLO_CABLE_CAM_OPTIONS, 8, options)
        self.assertEqual( self.controller.yawDirection, 1 )

    def testSetCruiseSpeed(self):
        """ Should set our cruise speed """
        options = struct.pack('<HHf', 1, 1, 2.299999952316284)
        self.controller.handlePacket(app_packet.SOLO_CABLE_CAM_OPTIONS, 8, options)
        self.controller.pathHandler.setCruiseSpeed.assert_called_with( 2.299999952316284 )

    def testNoPathHandler(self):
        """ Should early out """
        self.controller.camInterpolation = 0
        options = struct.pack('<HHf', 1, 1, 2.3)
        self.controller.pathHandler = None
        self.controller.handlePacket(app_packet.SOLO_CABLE_CAM_OPTIONS, 8, options)
        self.assertFalse( self.controller.setupTargeting.called )

class TestSetupTargeting(unittest.TestCase):
    def setUp(self):
        self.v = mock.create_autospec(Vehicle)
        self.v.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.mockMgr = Mock()
        self.mockMgr.currentShot = shots.APP_SHOT_CABLECAM
        self.mockMgr.getParam = Mock(return_value=500.0)
        self.mockMgr.buttonManager = Mock()
        self.controller = CableCamShot(self.v, self.mockMgr)
        self.mockMgr.remapper = Mock()
        self.controller.yawPitchOffsetter = Mock()
        self.controller.yawPitchOffsetter.enableNudge = Mock()
        self.controller.yawPitchOffsetter.disableNudge = Mock()

    def testInterpolationOn(self):
        """ If we turn on camera interpolation """
        self.controller.camInterpolation = 1
        self.controller.setupTargeting()
        self.v.message_factory.mount_configure_encode.assert_called_with(
                                        0, 1,    # target system, target component
                                        mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,  #mount_mode
                                        1,  # stabilize roll
                                        1,  # stabilize pitch
                                        1,  # stabilize yaw
                                        )
        self.mockMgr.rcMgr.enableRemapping.assert_called_with( True )
        self.controller.yawPitchOffsetter.enableNudge.assert_called_with()

    def testInterpolationOff(self):
        """ If we turn off camera interpolation """
        self.controller.camInterpolation = 0
        self.v.mount_status = [ -15.6, 27.8, 0.0 ]
        self.v.attitude.yaw = math.radians(27.8)
        self.controller.setupTargeting()
        self.v.message_factory.mount_configure_encode.assert_called_with(
                                        0, 1,    # target system, target component
                                        mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,  #mount_mode
                                        1,  # stabilize roll
                                        1,  # stabilize pitch
                                        1,  # stabilize yaw
                                        )
        self.mockMgr.rcMgr.enableRemapping.assert_called_with( True )
        self.controller.yawPitchOffsetter.disableNudge.assert_called_with(-15.6, 27.8)

    def testInterpolationOffNoGimbal(self):
        """ If we turn off camera interpolation without a gimbal """
        self.controller.camInterpolation = 0
        self.v.mount_status = [ None, None, 0.0 ]
        self.v.attitude.yaw = 1.3337
        self.controller.setupTargeting()

        self.v.message_factory.mount_configure_encode.assert_called_with(
                                        0, 1,    # target system, target component
                                        mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,  #mount_mode
                                        1,  # stabilize roll
                                        1,  # stabilize pitch
                                        1,  # stabilize yaw
                                        )
        self.mockMgr.rcMgr.enableRemapping.assert_called_with( True )
        self.controller.yawPitchOffsetter.disableNudge.assert_called_with(0.0, math.degrees(1.3337))


class TestHandleFreePitchYaw(unittest.TestCase):
    def setUp(self):
        mgr = Mock(spec = ["sendPacket", "remapper"])
        mgr.buttonManager = Mock()
        mgr.getParam = Mock(return_value=500.0)
        self.v = mock.create_autospec(Vehicle)
        self.controller = CableCamShot(self.v, mgr)

    def testWithGimbal(self):
        """ With a gimbal, use mount_control to control pitch/yaw """
        self.v.mount_status = [20.0, 0.0, 1.3]
        self.controller.yawPitchOffsetter = Mock()
        yaw = float( 1.111333 )
        pitch = float (2.55556666 )
        self.controller.yawPitchOffsetter.yawOffset = yaw
        self.controller.yawPitchOffsetter.pitchOffset = pitch
        self.controller.handleFreePitchYaw()
        self.v.message_factory.mount_control_encode.assert_called_with(
                                            0, 1,    # target system, target component
                                            pitch * 100, # pitch
                                            0.0, # roll
                                            yaw * 100, # yaw
                                            0 # save position
                                            )

    def testNoGimbal(self):
        """ Without a gimbal, we only use condition_yaw to control """
        # no gimbal
        self.v.mount_status = [None, None, None]
        self.controller.yawPitchOffsetter = Mock()
        yaw = float( -27.283475 )
        pitch = float ( 14.4444 )
        self.controller.yawPitchOffsetter.yawOffset = yaw
        self.controller.yawPitchOffsetter.pitchOffset = pitch
        self.controller.yawPitchOffsetter.yawDir = 1
        self.controller.handleFreePitchYaw()
        self.v.message_factory.command_long_encode.assert_called_with(
                                            0, 0,    # target system, target component
                                            mavutil.mavlink.MAV_CMD_CONDITION_YAW, #command
                                            0, #confirmation
                                            yaw, # param 1 - target angle
                                            cable_cam.YAW_SPEED, # param 2 - yaw speed
                                            self.controller.yawPitchOffsetter.yawDir, # param 3 - direction
                                            0.0, # relative offset
                                            0, 0, 0 # params 5-7 (unused)
                                            )
