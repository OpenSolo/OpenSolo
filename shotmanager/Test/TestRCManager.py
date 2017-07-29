
import shotManager
import unittest
import mock
from mock import patch, Mock
import socket
from dronekit import Vehicle
import struct
import rcManager

class TestParse(unittest.TestCase):
    @patch.object(socket.socket, 'bind')
    def setUp(self, mock_bind):
        self.mgr = shotManager.ShotManager()
        v = mock.create_autospec(Vehicle)
        self.mgr.Start(v)
        self.sock = Mock()
        self.channels = [1500, 5, 9, 8, 7, 1, 1, 1]
        self.value = struct.pack('<dHHHHHHHHH', 2.3, 3, 1500, 5, 9, 8, 7, 1, 1, 1)
        self.mgr.rcMgr.server.recv = Mock(return_value = self.value)

    def testCacheSocketData(self):
        """ incoming RC data should be written to self.channels """
        # should feed return value of sock.recv into remap
        self.mgr.rcMgr.parse()
        self.assertEqual( self.mgr.rcMgr.channels, self.channels )

    def testResetTicks(self):
        """ handleRCSock should reset numTicksSinceRCUpdate """
        self.mgr.numTicksSinceRCUpdate = 17
        self.mgr.rcMgr.parse()
        self.assertEqual( self.mgr.rcMgr.numTicksSinceRCUpdate, 0 )

    def testDontCacheData(self):
        """ if incoming data is malformed, do not cache it """
        self.mgr.channels = 111
        self.sock.recv = Mock(return_value='333')
        self.mgr.rcMgr.parse()
        self.assertNotEqual( self.mgr.rcMgr.channels, '333' )
        
        
class TestNormalizeRC(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.rcManager = rcManager.rcManager(shotmgr)
        sock = Mock()

    def testOutOfBoundsHighDefaultMinMax(self):
        """ PWM values above max should return 0.0 """
        result = self.rcManager.normalizeRC(2050, rcManager.DEFAULT_RC_MIN, rcManager.DEFAULT_RC_MAX)
        self.assertEqual( result, 0.0 )

    def testOutOfBoundsLowDefaultMinMax(self):
        """ PWM values below min should return 0.0 """
        result = self.rcManager.normalizeRC(957, rcManager.DEFAULT_RC_MIN, rcManager.DEFAULT_RC_MAX)
        self.assertEqual( result, 0.0 )

    def test1DefaultMinMax(self):
        """ pwm of 2000 should result in 1.0 """
        result = self.rcManager.normalizeRC(2000, rcManager.DEFAULT_RC_MIN, rcManager.DEFAULT_RC_MAX)
        self.assertEqual( result, 1.0 )

    def testneg1DefaultMinMax(self):
        """ pwm of 1000 should result in -1.0 """
        result = self.rcManager.normalizeRC(1000, rcManager.DEFAULT_RC_MIN, rcManager.DEFAULT_RC_MAX)
        self.assertEqual( result, -1.0 )

    def testMidDefaultMinMax(self):
        """ pwm of 1500 should result in 0.0 """
        result = self.rcManager.normalizeRC(1500, rcManager.DEFAULT_RC_MIN, rcManager.DEFAULT_RC_MAX)
        self.assertEqual( result, 0.0 )

    def testOutOfBoundsHighCustomMinMax(self):
        """ Values above a custom max should return 0.0 """
        result = self.rcManager.normalizeRC(1521, 1000, 1520)
        self.assertEqual( result, 0.0 )

    def testOutOfBoundsLowCustomMinMax(self):
        """ Values below a custom min should return 0.0 """
        result = self.rcManager.normalizeRC(-1, 0, 1000)
        self.assertEqual( result, 0.0 )

    def test1CustomMinMax(self):
        """ Value matching max should result in 1.0 """
        result = self.rcManager.normalizeRC(1333, 650, 1333)
        self.assertEqual( result, 1.0 )

    def testneg1CustomMinMax(self):
        """ Value matching min should result in -1.0 """
        result = self.rcManager.normalizeRC(333, 333, 666)
        self.assertEqual( result, -1.0 )

    def testMidCustomMinMax(self):
        """ Mid value should result in 0.0 """
        result = self.rcManager.normalizeRC(1260, 1000, 1520)
        self.assertEqual( result, 0.0 )


class TestRemap(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.rcManager = rcManager.rcManager(shotmgr)
        sock = Mock()

    def testStickNormalization(self):
        """ Remap should call normalize for each channel """
        self.rcManager.channels = [1600, 1200, 1500, 1300, 2000, 1000, 1237, 1889]
        normChannels = self.rcManager.remap()

        self.assertEqual( normChannels[0], .2 )
        self.assertEqual( normChannels[1], -0.6 )
        self.assertEqual( normChannels[2], 0.0)
        self.assertEqual( normChannels[3], -0.4 )
        self.assertEqual( normChannels[5], -1.0 )

    def testChannel6Max(self):
        """ Channel 6 (index 5) is a special case and goes from 1000-1520. Input of 1520 should return 1.0"""
        self.rcManager.channels = [0, 0, 0, 0, 0, 1520, 0, 0]
        normChannels = self.rcManager.remap()
        self.assertEqual( normChannels[5], 1.0 )

    def testChannel6Mid(self):
        """ Channel 6 (index 5) is a special case and goes from 1000-1520.  Input of 1260 should return 0.0"""
        self.rcManager.channels = [0, 0, 0, 0, 0, 1260, 0, 0]
        normChannels = self.rcManager.remap()
        self.assertEqual( normChannels[5], 0.0 )

    def testChannel8(self):
        """ Channel 8 (index 7) is a special case and goes from 0-1000 """
        self.rcManager.channels = [0, 0, 0, 0, 0, 0, 0, 777]
        normChannels = self.rcManager.remap()
        result = (777 - 500) / 500.0
        self.assertEqual( normChannels[7], result )

    def testNoRemappingSticks(self):
        """ If self.remappingSticks is off, we should not forward sticks to pixRC """
        self.rcManager.channels = [1100, 1500, 1500, 1500, 0, 0, 0, 777]
        self.rcManager.remappingSticks = False
        with patch('sololink.rc_ipc.put') as mock_put:
            self.rcManager.remap()
            self.assertFalse( mock_put.called )

    def testRemappingSticks(self):
        """ If self.remappingSticks is on, we should forward sticks to pixRC, if passing in True for sendToPixRC """
        self.rcManager.channels = [1100, 0, 0, 1500,0, 0, 0, 777]
        self.rcManager.remappingSticks = True
        self.rcManager.timestamp = 140
        self.rcManager.sequence = 0
        with patch('sololink.rc_ipc.put') as mock_put:
            self.rcManager.remap()
            mock_put.assert_called_with((140, 0, [1100, 0, 0, 1500, 0, 0, 0, 777]))


    def testRemappingSticksFalse(self):
        """ If self.remappingSticks is off, we should enter into Failsafe, enable remapping and send RC to sendToPixRC """
        self.rcManager.channels = [1100, 1500, 1500, 1500, 0, 0, 0, 777]
        self.rcManager.remappingSticks = False
        with patch('sololink.rc_ipc.put') as mock_put:
            self.rcManager.remap()
            self.assertFalse( mock_put.called )


    def testRemap(self):
        defaultChannels = [0.0, 0.0, 0.0, 0.0, 0, 0.0, 0, 0.0]
        self.rcManager.channels = [rcManager.DEFAULT_RC_MID, 
                            rcManager.DEFAULT_RC_MID, 
                            rcManager.DEFAULT_RC_MID, 
                            rcManager.DEFAULT_RC_MID, 
                            rcManager.DEFAULT_RC_MIN, 
                            rcManager.CHANNEL6_MID, 
                            rcManager.DEFAULT_RC_MID, 
                            rcManager.CHANNEL8_MID]
                                    
        retVal = self.rcManager.remap()
        self.assertEqual(retVal,defaultChannels)


class TestRemapperInit(unittest.TestCase):
    def testInit(self):
        """ Test initialization of RC remapper """
        shotmgr = Mock()
        self.rcManager = rcManager.rcManager(shotmgr)
        sock = Mock()
        self.assertFalse(self.rcManager.remappingSticks)

