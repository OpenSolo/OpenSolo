# Unit tests for ZiplineShot
import math
import mock
from mock import call
from mock import Mock
from mock import patch
import os
from os import sys, path
import unittest

from dronekit import LocationGlobalRelative, Vehicle
import location_helpers
import rewindManager
from rewindManager import RewindManager
from shotManager import ShotManager


class TestRedind(unittest.TestCase):
    def setUp(self):
        mgr = mock.create_autospec(ShotManager)
        mgr.buttonManager = Mock()
        self.mock_vehicle = mock.create_autospec(Vehicle)
        self.rewind = RewindManager(self.mock_vehicle, mgr)
        self.mock_vehicle.location.global_relative_frame = LocationGlobalRelative(37.0, -122.0, 10.0)

    def testInit(self):
        """ Test init """
        self.assertEqual(self.rewind.bufferSize, int(math.floor(self.rewind.rewindDistance / rewindManager.RTL_STEP_DIST)))
        

    def testReset(self):
        """ Test reset """
        self.rewind.resetSpline()
        for num in range(1,self.rewind.bufferSize):
            self.assertEqual(self.rewind.buffer[num], None)

        self.assertEqual(self.rewind.bufferSize, len(self.rewind.buffer))
        self.assertEqual(self.rewind.buffer[0].lat, 37.0)
        self.assertEqual(self.rewind.buffer[0].lon, -122.0)
        self.assertEqual(self.rewind.buffer[0].alt, 10.0)
        self.assertEqual(self.rewind.buffer[1], None)
        self.assertEqual(self.rewind.did_init, True)
        
        
    def testUpdateLocation(self):
        """ Test loc queue """
        self.mock_vehicle.location.global_relative_frame = LocationGlobalRelative(37.0, -122.0, 10.0)
        self.rewind.did_init = False
        
        self.mock_vehicle.armed = True
        self.mock_vehicle.system_status = 'ACTIVE'
        
        self.rewind.resetSpline()
        self.mock_vehicle.location.global_relative_frame = LocationGlobalRelative(37.00001, -122.00002, 10.0)
        self.rewind.counter = 4
        self.rewind.updateLocation()
        self.assertEqual(self.rewind.currentIndex, 1)
        self.assertEqual(self.rewind.buffer[1].lat, 37.00001)
        self.assertEqual(self.rewind.buffer[1].lon, -122.00002)
        self.assertEqual(self.rewind.buffer[1].alt, 10.0)


