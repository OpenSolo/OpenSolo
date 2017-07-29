# Unit tests for modes
import mock
import os
from os import sys, path
import unittest

from dronekit import Vehicle

sys.path.append(os.path.realpath('..'))
import modes

class TestModeLookup(unittest.TestCase):
    def setUp(self):
        self.v = mock.create_autospec(Vehicle)
        self.v._mode_mapping = { "ALT_HOLD" : 2,
                                            "TEST_ME" : 317 }

    def testLookupAltHold(self):
        """ Look up 'ALT_HOLD' """
        i = modes.getAPMModeIndexFromName( 'ALT_HOLD', self.v )
        self.assertEqual( i, 2 )

    def testLookupTestMe(self):
        """ Look up 'TEST_ME' """
        i = modes.getAPMModeIndexFromName( 'TEST_ME', self.v )
        self.assertEqual( i, 317 )

    def testLookupModeParser(self):
        """ Look up 'Mode(10)' """
        i = modes.getAPMModeIndexFromName( 'Mode(10)', self.v )
        self.assertEqual( i, 10 )

    def testMalformedMode(self):
        """ Look up 'Mode(asta' """
        i = modes.getAPMModeIndexFromName( 'Mode(asta', self.v )
        self.assertEqual( i, -1 )

    def testLookupInvalidMode(self):
        """ Look up 'Invalid' """
        i = modes.getAPMModeIndexFromName( 'Invalid', self.v )
        self.assertEqual( i, -1 )
