# Unit tests for ShotManager
import mock
from mock import call
from mock import Mock
from mock import patch
import os
from os import sys, path
from pymavlink import mavutil
import socket
import struct
import unittest

from dronekit import Vehicle, LocationGlobalRelative, VehicleMode
sys.path.append(os.path.realpath('..'))
import app_packet
from orbit import OrbitShot
from selfie import SelfieShot
from follow import FollowShot
from multipoint import MultipointShot
from cable_cam import CableCamShot
import shotManager
from shotManagerConstants import *
import shots
# on host systems these files are located here
sys.path.append(os.path.realpath('../../../flightcode/stm32'))
from sololink import btn_msg
import __builtin__

ERROR = 0.1

class TestEKFCallback(unittest.TestCase):
    @patch.object(socket.socket, 'bind')
    def setUp(self, mock_bind):
        self.mgr = shotManager.ShotManager()
        vehicle = mock.create_autospec(Vehicle)
        # Make sure EKF is not reported as ok on Startup
        vehicle.ekf_ok = False
        self.mgr.Start(vehicle)

    def testEKFStartup(self):
        """ EKF on startup should be not ok """
        self.assertFalse( self.mgr.last_ekf_ok )

    def testEKFUnarmedToLoiter(self):
        """ Shot manager starts in loiter """
        self.mgr.vehicle.ekf_ok = True
        self.mgr.buttonManager = Mock()
        self.mgr.ekf_callback( self.mgr.vehicle, "ekf_ok", True )
        self.assertTrue( self.mgr.last_ekf_ok )
        self.assertEqual( self.mgr.vehicle.mode.name, "LOITER" )
        self.mgr.buttonManager.setButtonMappings.assert_called_with()

class TestArmedCallback(unittest.TestCase):
    @patch.object(socket.socket, 'bind')
    def setUp(self, mock_bind):
        self.mgr = shotManager.ShotManager()
        vehicle = mock.create_autospec(Vehicle)
        self.mgr.Start(vehicle)
        self.mgr.buttonManager = Mock()
        self.mgr.goproManager = Mock()
        self.mgr.rewindManager = Mock()

    def testArmedStartup(self):
        """ armed on startup should be not ok """
        self.assertFalse( self.mgr.last_armed )

    def testArmedCallback(self):
        """ change button mappings if our armed state changes """
        self.mgr.vehicle.armed = True
        self.mgr.armed_callback( self.mgr.vehicle, "armed", True)
        self.assertTrue( self.mgr.last_armed )
        self.mgr.buttonManager.setButtonMappings.assert_called_with()

    def testArmedCallbackNoChange(self):
        """ Don't change button mappings if our armed state doesn't change """
        self.mgr.vehicle.armed = False
        self.mgr.armed_callback( self.mgr.vehicle, "armed", False )
        self.assertFalse( self.mgr.last_armed )
        self.assertFalse( self.mgr.buttonManager.setButtonMappings.called )

    def testDisarmExitShot(self):
        """ Disarming should exit a shot """
        self.mgr.currentShot = shots.APP_SHOT_SELFIE
        self.mgr.last_armed = True
        self.mgr.armed_callback( self.mgr.vehicle, "armed", False )
        self.assertTrue(self.mgr.currentShot == shots.APP_SHOT_NONE)

    def testDisarmStopGoProRecording(self):
        """ Disarming should stop recording on GoPro """
        self.mgr.currentShot = shots.APP_SHOT_NONE
        self.mgr.last_armed = True
        self.mgr.armed_callback( self.mgr.vehicle, "armed", False )
        self.assertTrue( self.mgr.goproManager.handleRecordCommand.called )

class TestEnterShot(unittest.TestCase):
    @patch.object(socket.socket, 'bind')
    def setUp(self, mock_bind):
        self.mgr = shotManager.ShotManager()
        vehicle = mock.create_autospec(Vehicle)
        vehicle.system_status = 'ACTIVE'
        self.mgr.Start(vehicle)
        self.mgr.buttonManager = Mock()
        self.mgr.appMgr.sendPacket = Mock()
        self.mgr.rcMgr = Mock()
        self.mgr.last_ekf_ok = True
        self.mgr.appMgr = Mock()
        self.mgr.appMgr.isAppConnected = Mock(return_value=True)

    def testShouldNotenterShotOnTheGround(self):
        """ Won't enter a shot from the ground """
        self.mgr.vehicle.system_status = 'STANDBY'
        self.mgr.currentShot = shots.APP_SHOT_NONE
        self.mgr.enterShot( shots.APP_SHOT_CABLECAM )
        packet = struct.pack('<III', app_packet.SOLO_SHOT_ERROR, 4, app_packet.SHOT_ERROR_UNARMED)
        self.mgr.appMgr.sendPacket.assert_any_call( packet )
        self.assertEqual( self.mgr.currentShot, shots.APP_SHOT_NONE )

    def testShouldNotEnterShotinCritical(self):
        '''Won't enter a shot when system is in critical state'''
        self.mgr.vehicle.system_status = 'CRITICAL'
        self.mgr.currentShot = shots.APP_SHOT_NONE
        self.mgr.enterShot( shots.APP_SHOT_CABLECAM )
        packet = struct.pack('<III', app_packet.SOLO_SHOT_ERROR, 4, app_packet.SHOT_ERROR_RTL)
        self.mgr.appMgr.sendPacket.assert_any_call( packet )
        self.assertEqual( self.mgr.currentShot, shots.APP_SHOT_NONE )

    def testShouldNotEnterShotinEmergency(self):
        '''Won't enter a shot when system is in emergency state'''
        self.mgr.vehicle.system_status = 'EMERGENCY'
        self.mgr.currentShot = shots.APP_SHOT_NONE
        self.mgr.enterShot( shots.APP_SHOT_CABLECAM )
        packet = struct.pack('<III', app_packet.SOLO_SHOT_ERROR, 4, app_packet.SHOT_ERROR_RTL)
        self.mgr.appMgr.sendPacket.assert_any_call( packet )
        self.assertEqual( self.mgr.currentShot, shots.APP_SHOT_NONE )

    def testEnterShotNoChange(self):
        """ Entering a shot we're already in.  No change """
        self.mgr.currentShot = shots.APP_SHOT_SELFIE
        self.mgr.enterShot( shots.APP_SHOT_SELFIE )
        self.assertEqual( self.mgr.currentShot, shots.APP_SHOT_SELFIE )
        self.assertEqual( self.mgr.curController, None )

    def testEnterShotChange(self):
        """ Go from no shot to selfie """
        self.mgr.currentShot = shots.APP_SHOT_NONE
        self.mgr.enterShot( shots.APP_SHOT_SELFIE )
        self.assertEqual( self.mgr.currentShot, shots.APP_SHOT_SELFIE )
        self.mgr.buttonManager.setButtonMappings.assert_called_with()
        self.mgr.buttonManager.setArtooShot.assert_called_with( shots.APP_SHOT_SELFIE )
        self.mgr.appMgr.broadcastShotToApp(shots.APP_SHOT_SELFIE)
        self.assertTrue( isinstance(self.mgr.curController, SelfieShot) )

    def testOrbit(self):
        """ No shot to Orbit """
        self.mgr.enterShot( shots.APP_SHOT_ORBIT )
        self.assertTrue( isinstance(self.mgr.curController, OrbitShot) )

    def testFollow(self):
        """ No shot to Follow """
        self.mgr.enterShot( shots.APP_SHOT_FOLLOW )
        self.assertTrue( isinstance(self.mgr.curController, FollowShot) )

    def testNoShot(self):
        """ Entering no shot """
        self.mgr.vehicle.message_factory = Mock()
        self.mgr.getParam = Mock(return_value=500.0)
        self.mgr.vehicle.mode = VehicleMode("GUIDED")
        self.mgr.currentShot = shots.APP_SHOT_SELFIE
        self.mgr.enterShot( shots.APP_SHOT_NONE )
        self.mgr.vehicle.gimbal.release.assert_called_with()
        self.mgr.rcMgr.enableRemapping.assert_called_with( False )
        self.assertEqual( self.mgr.vehicle.mode.name, "LOITER" )

    def testBadEKF(self):
        """ We have bad EKF, should disallow entry into shot """
        self.mgr.last_ekf_ok = False
        self.mgr.curController = "yeah"
        self.mgr.currentShot = shots.APP_SHOT_SELFIE
        self.mgr.enterShot( shots.APP_SHOT_FOLLOW )
        self.assertEqual( self.mgr.curController, None )
        packetDisallow = struct.pack('<III', app_packet.SOLO_SHOT_ERROR, 4, app_packet.SHOT_ERROR_BAD_EKF)
        calls = [call(packetDisallow)]
        self.mgr.appMgr.sendPacket.assert_has_calls(calls)

class TestModeCallback(unittest.TestCase):
    @patch.object(socket.socket, 'bind')
    def setUp(self, mock_bind):
        self.mgr = shotManager.ShotManager()
        self.v = mock.create_autospec(Vehicle)
        self.v.system_status = 'ACTIVE'
        self.mgr.Start(self.v)
        self.mgr.buttonManager = Mock()

    def testModeStartup(self):
        """ Shot manager mode on startup should be loiter """
        self.assertEqual( self.mgr.vehicle.mode.name, "LOITER" )
        self.assertEqual( self.mgr.lastMode, "LOITER" )

    def testLoiterToAltHold(self):
        """ Loiter to alt hold """
        self.v.mode = VehicleMode("ALT_HOLD")
        self.v._mode_mapping = { "ALT_HOLD" : 2 }
        self.mgr.mode_callback( self.v, "mode", self.v.mode )
        self.mgr.buttonManager.setArtooShot.assert_called_with( -1, 2 )

    def testExitShot(self):
        """ If we're in a guided shot and we enter any other mode, kick us out of our shot """
        self.v.mode = VehicleMode("GUIDED")
        self.mgr.mode_callback( self.v, "mode", self.v.mode )
        # don't send guided to setArtooShot
        self.assertFalse( self.mgr.buttonManager.setArtooShot.called )
        self.mgr.currentShot = shots.APP_SHOT_CABLECAM
        self.v.mode = VehicleMode("LOITER")
        self.mgr.mode_callback( self.v, "mode", self.v.mode )
        self.assertTrue( self.mgr.currentShot == shots.APP_SHOT_NONE )

    def testRTLExitsShot(self):
        """ Even if we're not in guided, RTL should exit shots """
        self.mgr.currentShot = shots.APP_SHOT_SELFIE
        self.v.mode = VehicleMode("RTL")
        self.mgr.getParam = Mock(return_value=500.0)
        self.mgr.mode_callback( self.v, "mode", self.v.mode )
        #self.assertTrue( self.mgr.currentShot == shots.APP_SHOT_RTL )


class TestGetParam(unittest.TestCase):
    @patch.object(socket.socket, 'bind')
    def setUp(self, mock_bind):
        self.mgr = shotManager.ShotManager()
        self.v = mock.create_autospec(Vehicle)
        self.mgr.Start(self.v)

    def testGetParamValid(self):
        """ Test retrieval of a valid parameter """
        base = {
            "WPNAV_SPEED" : 33.4
        }

        self.v.parameters = Mock(base)
        self.v.parameters.get = lambda x, wait_ready=False: base.get(x)

        self.assertEqual( self.mgr.getParam( "WPNAV_SPEED", 100.0), 33.4 )

    def testGetParamInvalid(self):
        """ If a parameter is invalid, use the default value """
        base = {
            "WPNAV_SPEED" : 33.4
        }

        self.v.parameters = Mock(base)
        self.v.parameters.get = lambda x, wait_ready=False: base.get(x)

        self.assertEqual( self.mgr.getParam( "INVALID", 12.0), 12.0 )

class TestTick(unittest.TestCase):
    @patch.object(socket.socket, 'bind')
    def setUp(self, mock_bind):
        self.mgr = shotManager.ShotManager()
        self.v = mock.create_autospec(Vehicle)
        self.mgr.Start(self.v)

    def testTickSetsTime(self):
        """ Test that Tick updates the time of when it was last called """
        self.mgr.rcMgr.numTicksSinceRCUpdate = 0
        lastTime = self.mgr.timeOfLastTick
        self.mgr.Tick()
        self.assertFalse( lastTime == self.mgr.timeOfLastTick )
        self.assertEqual( self.mgr.rcMgr.numTicksSinceRCUpdate, 1 )

    def testTickNoRemapping(self):
        """ If we stop getting new RC packets, don't tell the RCmanager to send old packets to pixRC """
        self.mgr.curController = Mock()
        self.mgr.currentShot = shots.APP_SHOT_CABLECAM
        self.mgr.rcMgr.channels = [13, 14, 15]
        self.mgr.rcMgr = Mock()
        self.mgr.rcMgr.remap = Mock(return_value=888)
        self.mgr.rcMgr.numTicksSinceRCUpdate = 5
        self.mgr.Tick()
        self.mgr.rcMgr.remap.assert_called_with()
        self.mgr.curController.handleRCs.assert_called_with(888)


class TestCameraCallback(unittest.TestCase):
    @patch.object(socket.socket, 'bind')
    def setUp(self, mock_bind):
        self.mgr = shotManager.ShotManager()
        vehicle = mock.create_autospec(Vehicle)
        vehicle.camera_trigger_msg = Mock();
        self.mgr.Start(vehicle)
        self.mgr.cameraTLogFile = Mock()

    def testCameraTriggerCallbackIsAutoMission(self):
        self.mgr.vehicle.mode.name = 'AUTO'
        self.mgr.goproManager = Mock()
        self.mgr.camera_feedback_callback( self.mgr.vehicle, "camera_feedback", Mock() )
        self.assertTrue(self.mgr.goproManager.handleRecordCommand.called)

    def testCameraTriggerCallbackIsNotAutoMission(self):
        self.mgr.vehicle.mode.name = 'GUIDED'
        self.mgr.goproManager = Mock()
        self.mgr.camera_feedback_callback( self.mgr.vehicle, "camera_feedback", None )
        self.assertFalse(self.mgr.goproManager.handleRecordCommand.called)

    def testCameraTriggerCallbackIsNotSiteScanShot(self):
        self.mgr.currentShot = shots.APP_SHOT_MULTIPOINT
        self.mgr.goproManager = Mock()
        self.mgr.camera_feedback_callback( self.mgr.vehicle, "camera_feedback", None )
        self.assertFalse(self.mgr.goproManager.handleRecordCommand.called)
