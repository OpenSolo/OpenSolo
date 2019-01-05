# Unit tests for ZiplineShot
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
import zipline
from zipline import ZiplineShot
from shotManagerConstants import *
import shots
# on host systems these files are located here
from sololink import btn_msg
import app_packet

ERROR = 0.1

class TestNewZipline(unittest.TestCase):
    def setUp(self):
        mgr = Mock(spec = ["sendPacket", "remapper", "rcMgr", "appMgr", "getParam"])
        mgr.currentShot = shots.APP_SHOT_ZIPLINE
        mgr.buttonManager = Mock()
        mgr.getParam.return_value = 0 # so mock doesn't do lazy binds

        self.mock_vehicle = mock.create_autospec(Vehicle)
        self.controller = ZiplineShot(self.mock_vehicle, mgr)
        
        self.mock_vehicle.location.global_relative_frame = LocationGlobalRelative(37.242124, -122.12841, 15.3)

    def test3DZipline(self):
        """ Test 3D """
        self.controller.is2D = False
        self.controller.setupZipline()

    def testRCsZero(self):
        """ Test RCs Max """
        channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.controller.handleRCs(channels)


    def testRCsMax(self):
        """ Test RCs Max """
        channels = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        self.controller.handleRCs(channels)

    def testRCsMin(self):
        """ Test RCs Min """
        channels = [-1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0]
        self.controller.handleRCs(channels)

    def TestHandleAButtonNewZipline(self):
        """ This should record a new Zipline """
        self.controller.setupZipline = Mock()
        self.controller.handleButton( btn_msg.ButtonA, btn_msg.Press )
        self.controller.setupZipline.assert_called_with()

    def TestHandleBButtonSpotLock(self):
        """ This should Trigger Spot Lock """
        self.controller.spotLock = Mock()
        self.controller.camPointing = zipline.FREE_LOOK
        self.controller.handleButton( btn_msg.ButtonB, btn_msg.Press )
        self.controller.spotLock.assert_called_with()
        self.assertEqual(self.controller.camPointing, zipline.SPOT_LOCK)

    def TestHandleBButtonFreeCam(self):
        """ This should Revert to Free Look """
        self.controller.manualGimbalTargeting = Mock()
        self.controller.camPointing = zipline.SPOT_LOCK
        self.controller.handleButton( btn_msg.ButtonB, btn_msg.Press )
        self.controller.manualGimbalTargeting.assert_called_with()
        self.assertEqual(self.controller.camPointing, zipline.FREE_LOOK)

	
    def TestMoveSpotLock(self):
        """ Move Spot Lock """
        self.controller.handleSpotLock = Mock()
        self.controller.state = zipline.ZIPLINE_RUN
        self.controller.camPointing = zipline.FREE_LOOK
        self.controller.handleButton( btn_msg.ButtonB, btn_msg.Press )
        self.assertEqual(self.controller.camPointing, zipline.SPOT_LOCK)
        channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        channels[YAW] = 1.0
        channels[RAW_PADDLE] = 1.0
        self.controller.handleRCs(channels)
        self.controller.handleSpotLock.assert_called_with(channels)

    def TestRaiseSpotLock(self):
        """ Raise Spot Lock """
        #self.controller.updateROIAlt = Mock()
        self.controller.camPointing = zipline.FREE_LOOK
        self.controller.state = zipline.ZIPLINE_RUN
        self.controller.handleButton( btn_msg.ButtonB, btn_msg.Press )
        self.controller.camPointing = zipline.SPOT_LOCK
        channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        channels[RAW_PADDLE] = 1.0
        self.controller.handleRCs(channels)
        self.assertGreaterEqual(self.controller.roi.alt, .24)
        channels[RAW_PADDLE] = -1.0
        self.controller.handleRCs(channels)
        self.assertEqual(self.controller.roi.alt, 0)
        
        
        
