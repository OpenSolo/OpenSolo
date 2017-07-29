# Unit tests for SelfieShot
import math
import mock
from mock import call
from mock import Mock
from mock import MagicMock
import os
from os import sys, path
from pymavlink import mavutil
import struct
import unittest

from dronekit import LocationGlobalRelative, Vehicle
sys.path.append(os.path.realpath('..'))
import location_helpers
import selfie
from selfie import SelfieShot
from shotManager import ShotManager
from rcManager import rcManager
from shotManagerConstants import *
import shots
import app_packet
# on host systems these files are located here
from sololink import btn_msg

ERROR = 0.1

class Attitude():
    yaw = 0.0


class TestSelfieHandleRCsNotStarted(unittest.TestCase):
    def setUp(self):
        mgr = mock.create_autospec(ShotManager)
        mgr.buttonManager = Mock()
        mgr.currentShot = shots.APP_SHOT_SELFIE

        mgr.rcMgr = Mock(specs = ['remapper'])
        v = mock.create_autospec(Vehicle)
        v.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.controller = SelfieShot(v, mgr)
        self.controller.altLimit = 0

    def testHandleRCsNotStarted(self):
        """ Without points, handleRCs shouldn't do anything """
        channels = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        self.controller.handleRCs(channels)


class TestSelfieHandleRCs(unittest.TestCase):
    def setUp(self):
        mgr = mock.create_autospec(ShotManager)
        mgr.buttonManager = Mock()
        mgr.currentShot = shots.APP_SHOT_SELFIE
        mgr.rcMgr = Mock(specs = ['remapper'])
        mgr.appMgr = Mock()
        v = mock.create_autospec(Vehicle)
        v.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.controller = SelfieShot(v, mgr)
        self.controller.altLimit = 0

        self.controller.addLocation( LocationGlobalRelative(-14.654861, 108.4645, 32.6545) )
        self.controller.addLocation( LocationGlobalRelative(23.654504, 40.4645, 17.6545) )
        self.controller.addLocation( LocationGlobalRelative(23.661, 10.4645, 2.6545) )

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

class TestSetButtonMappings(unittest.TestCase):
    def setUp(self):
        mgr = mock.create_autospec(ShotManager)
        mgr.buttonManager = Mock()
        mgr.currentShot = shots.APP_SHOT_SELFIE
        mgr.buttonManager = Mock()
        mgr.rcMgr = Mock(specs = ['remapper'])
        v = mock.create_autospec(Vehicle)
        v.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.controller = SelfieShot(v, mgr)
        self.controller.altLimit = 0

    def testSetButtonMappingsNoROI(self):
        """ Testing setting button mappings when we haven't locked on yet """
        self.controller.setButtonMappings()
        calls = [call(btn_msg.ButtonA, shots.APP_SHOT_SELFIE, 0, "\0"), call(btn_msg.ButtonB, shots.APP_SHOT_SELFIE, 0, "\0")]
        self.controller.shotmgr.buttonManager.setArtooButton.assert_has_calls(calls, any_order = False)


    def testSetButtonMappings(self):
        """ Testing setting button mappings when we have started """
        self.controller.addLocation( LocationGlobalRelative(-14.654861, 108.4645, 32.6545) )
        self.controller.addLocation( LocationGlobalRelative(23.654504, 40.4645, 17.6545) )
        self.controller.addLocation( LocationGlobalRelative(23.661, 10.4645, 2.6545) )

        self.controller.setButtonMappings()
        calls = [call(btn_msg.ButtonA, shots.APP_SHOT_SELFIE, 0, "\0"), call(btn_msg.ButtonB, shots.APP_SHOT_SELFIE, 0, "\0")]
        self.controller.shotmgr.buttonManager.setArtooButton.assert_has_calls(calls)


class TestHandlePacket(unittest.TestCase):
    def setUp(self):
        mgr = mock.create_autospec(ShotManager)
        mgr.buttonManager = Mock()
        mgr.currentShot = shots.APP_SHOT_SELFIE
        mgr.rcMgr = Mock(specs = ['remapper'])
        v = mock.create_autospec(Vehicle)
        v.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.controller = SelfieShot(v, mgr)
        self.controller.pathHandler = Mock(specs=['isPaused'])
        self.controller.altLimit = 0

    def testCruiseSpeedSet0(self):
        options = struct.pack('<f', 0.0)
        self.controller.handlePacket(app_packet.SOLO_SHOT_OPTIONS, 4, options)
        self.controller.pathHandler.setCruiseSpeed.assert_called_with(0.0)

    def testCruiseSpeedSet6(self):
        options = struct.pack('<f', 6.0)
        self.controller.handlePacket(app_packet.SOLO_SHOT_OPTIONS, 4, options)
        self.controller.pathHandler.setCruiseSpeed.assert_called_with(6.0)

    def testCruiseSpeedSet3(self):
        options = struct.pack('<f', 3.0)
        self.controller.handlePacket(app_packet.SOLO_SHOT_OPTIONS, 4, options)
        self.controller.pathHandler.setCruiseSpeed.assert_called_with(3.0)

    def testNoPathHandler(self):
        """ Shouldn't crash if we don't have a path handler """
        options = struct.pack('<f', 1.0)
        self.controller.pathHandler = None
        self.controller.handlePacket(app_packet.SOLO_SHOT_OPTIONS, 4, options)

class TestHandleButton(unittest.TestCase):
    def setUp(self):
        mgr = mock.create_autospec(ShotManager)
        mgr.buttonManager = Mock()
        mgr.currentShot = shots.APP_SHOT_SELFIE
        mgr.rcMgr = Mock(specs = ['remapper'])
        v = mock.create_autospec(Vehicle)
        v.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.controller = SelfieShot(v, mgr)
        self.controller.pathHandler = Mock(specs=['isPaused','togglePause'])
        self.controller.updateAppOptions = Mock()
        self.controller.altLimit = 0

    def TestPauseCruise(self):
        """ pause button pauses cruising """
        self.controller.pathHandler.isPaused = Mock(return_value=False)
        self.controller.handleButton( btn_msg.ButtonLoiter, btn_msg.Press )
        self.controller.pathHandler.togglePause.assert_called_with()
        self.controller.updateAppOptions.assert_called_with()

    def TestResumeCruise(self):
        """ pause button resumes cruising (if already paused) """
        self.controller.pathHandler.isPaused = Mock(return_value=True)
        self.controller.handleButton( btn_msg.ButtonLoiter, btn_msg.Press )
        self.controller.pathHandler.togglePause.assert_called_with()
        self.controller.updateAppOptions.assert_called_with()

    def TestNotifyPauseLoiter(self):
        self.controller.pathHandler = None
        self.controller.handleButton(btn_msg.ButtonLoiter, btn_msg.Press)
        self.controller.shotmgr.notifyPause.assert_called_with(False)

    def TestNotifyPauseGuided(self):
        self.controller.handleButton(btn_msg.ButtonLoiter, btn_msg.Press)
        self.controller.shotmgr.notifyPause.assert_called_with(True)

class TestAddLocation(unittest.TestCase):
    def setUp(self):
        mgr = mock.create_autospec(ShotManager)
        mgr.buttonManager = Mock()
        mgr.currentShot = shots.APP_SHOT_SELFIE
        mgr.rcMgr = Mock(specs = ['remapper'])
        v = mock.create_autospec(Vehicle)
        v.location.global_relative_frame = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.controller = SelfieShot(v, mgr)
        self.controller.altLimit = 0

    def testAltitudeLimit(self):
        '''Makes sure 2nd selfie point is capped at the user-defined altitude limit'''
        self.controller.altLimit = 25 # meters
        self.controller.addLocation( LocationGlobalRelative(23.654504, 40.4645, 17.6545) )
        self.controller.addLocation( LocationGlobalRelative(-14.654861, 108.4645, 32.6545) )
        self.assertAlmostEqual(self.controller.altLimit,self.controller.waypoints[1].alt,1)

    def testAltitudeLimitDisabled(self):
        '''Makes sure 2nd selfie point is NOT capped if altitude limit is disabled'''
        self.controller.altLimit = None
        x2 = -14.654861
        y2 = 108.4645
        z2 = 32.6545
        
        self.controller.addLocation( LocationGlobalRelative(23.654504, 40.4645, 17.6545) )
        self.controller.addLocation( LocationGlobalRelative(x2, y2, z2) )
        self.assertAlmostEqual(x2, self.controller.waypoints[1].lat,1)
        self.assertAlmostEqual(y2, self.controller.waypoints[1].lon,1)
        self.assertAlmostEqual(z2, self.controller.waypoints[1].alt,1)

    def testAddLocations(self):
        """ Test adding locations """

        loc = LocationGlobalRelative(37.242124, -122.12841, 15.3)
        self.controller.addLocation(loc)
        loc = LocationGlobalRelative(30.13241, 10.112135, 0.0)
        self.controller.addLocation(loc)
        loc = LocationGlobalRelative(-14.654861, 108.4645, 32.6545)
        self.controller.addLocation(loc)
