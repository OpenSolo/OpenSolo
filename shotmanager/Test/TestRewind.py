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
import rewind
from rewind import RewindShot
import rewindManager
from rewindManager import RewindManager

from shotManagerConstants import *
import shots
# on host systems these files are located here
from sololink import btn_msg
import app_packet


class TestRewind(unittest.TestCase):
    def setUp(self):
        mgr = Mock(spec = ["sendPacket", "remapper", "rcMgr", "appMgr", "rewindManager"])
        mgr.currentShot = shots.APP_SHOT_ZIPLINE
        mgr.buttonManager = Mock()

        self.mock_vehicle = mock.create_autospec(Vehicle)
        
        #self.controller = RewindShot(self.mock_vehicle, mgr)
        #self.controller.rewindManager = RewindManager(self.mock_vehicle)
        #test = RewindManager(self.mock_vehicle)
        
        #self.mock_vehicle.location.global_relative_frame = LocationGlobalRelative(37.0, -122.0, 15.0)

    def testInit(self):
        ''' verify init '''
        #self.assertTrue( self.controller.rewindManager )
        
        
#    def testHandleRCs(self):
#        self.rewind = RewindManager(self.mock_vehicle)
#
#        # store first location
#        self.mock_vehicle.location.global_relative_frame = LocationGlobalRelative(37.0, -122.0, 15.0)
#
#        # We only record locations while in air
#        self.mock_vehicle.armed = True
#        self.mock_vehicle.system_status = 'ACTIVE'
#        
#        self.controller.rewindManager = self.rewind
#        # Pushes vehicle loc to buffer index 0
#        self.controller.rewindManager.reset()
#        
#        self.mock_vehicle.location.global_relative_frame = LocationGlobalRelative(37.00001, -122.00002, 10.0)
#        # force past load limiter
#        self.rewind.counter = rewindManager.LOOP_LIMITER
#        # store next location
#        self.rewind.updateLocation()
#
#        channels = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
#
#        # Force state machine ot load next waypoint from rewind manager
#        self.controller.state = rewind.LOAD_NEXT
#        self.controller.handleRCs(channels)
#        
#        # make sure the index decrements
#        self.assertEqual(self.rewind.currentIndex, 0)
#
#        # make sure returned value matches
#        self.assertEqual(self.controller.currentTarget.lat, 37.00001)
#        self.assertEqual(self.controller.currentTarget.lon, -122.00002)
#        self.assertEqual(self.controller.currentTarget.alt, 10.0)
#
#        # read in the original and last location
#        self.controller.state = rewind.LOAD_NEXT
#        self.controller.handleRCs(channels)
#        
#        # Watch call to switch modes to RTL
#        self.controller.shotmgr.enterMode = Mock()
#
#        # make sure we trigger the exit to RTL
#        self.controller.state = rewind.LOAD_NEXT
#        self.controller.handleRCs(channels)
#
#        # handleRCs shuold call RTL (mode 6)
#        #self.controller.shotmgr.enterMode.assert_called_with(6)
#        
#