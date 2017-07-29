# Unit tests for buttonManager
import mock
from mock import call
from mock import Mock
from mock import patch
import os
from os import sys, path

import unittest

sys.path.append(os.path.realpath('..'))
import settings


class TestWriteSettingsThread(unittest.TestCase):
    def setUp(self):
        settings.CONFIG_FILE = "Test/shotmanager.conf"
        settings.CONFIG_FILE_BACKUP = "Test/shotmanager.back"
        self.lock = Mock()
        settings.settingsLock = self.lock

    def testLocks(self):
        """ Make sure we lock/unlock """
        settings.writeSettingsThread("a", "b")
        self.lock.acquire.assert_called_with()
        self.lock.release.assert_called_with()

    def testValueSet(self):
        """ Make sure we are setting the correct value """
        with patch('ConfigParser.SafeConfigParser') as patchedParser:
            parser = Mock()
            patchedParser.return_value = parser
            settings.writeSettingsThread("aaa", "bbb")
            parser.read.assert_called_with("Test/shotmanager.conf")
            parser.set.assert_called_with("shotManager", "aaa", "bbb")


class TestReadSetting(unittest.TestCase):
    def setUp(self):
        mockParser = patch('ConfigParser.SafeConfigParser')
        self.addCleanup(mockParser.stop)
        mock = mockParser.start()
        self.parser = Mock()
        settings.CONFIG_FILE = "Test/shotmanager.conf"
        mock.return_value = self.parser

    def testReadSetting(self):
        """ Test that we attempt to read the correct thing """
        self.parser.get = Mock(return_value = "foo")
        value = settings.readSetting("bleh")
        self.parser.get.assert_called_with("shotManager", "bleh")
        self.assertEqual(value, "foo")

    def testReadBadSetting(self):
        """ Test that we get an exception from a failed get """
        self.parser.get = Mock(return_value = "foo", side_effect=KeyError("Boo"))
        try:
            value = settings.readSetting("bleh")
        except:
            pass
        else:
            self.assertFalse(True)
