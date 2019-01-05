import unittest
import shotManager
import appManager
from dronekit import Vehicle
import app_packet
import mock
from mock import patch, Mock
import socket
import struct
import shots
from sololink import btn_msg

class TestParse(unittest.TestCase):
    @patch.object(socket.socket, 'bind')
    def setUp(self, mock_bind):
        self.mgr = shotManager.ShotManager()
        self.v = mock.create_autospec(Vehicle)
        self.mgr.Start(self.v)
        self.mgr.appMgr.client = Mock(specs=['recv'])

    def tearDown(self):
        self.mgr.appMgr.server.close()

    def testEnterShot(self):
        """ Test parsing entering orbit """
        self.mgr.enterShot = Mock()
        value = struct.pack('<IIi', app_packet.SOLO_MESSAGE_SET_CURRENT_SHOT, 4, shots.APP_SHOT_ORBIT)
        self.mgr.appMgr.client.recv.return_value = value
        handled = self.mgr.appMgr.parse()
        self.mgr.enterShot.assert_called_with(shots.APP_SHOT_ORBIT)

    def testEnterUnknownShot(self):
        """ Test parsing an unknown shot """
        self.mgr.enterShot = Mock()
        value = struct.pack('<IIi', app_packet.SOLO_MESSAGE_SET_CURRENT_SHOT, 99, shots.APP_SHOT_ORBIT)
        self.mgr.appMgr.client.recv.return_value = value
        handled = self.mgr.appMgr.parse()
        assert not self.mgr.enterShot.called

    def testGetButtonSettings(self):
        """ Test parsing the request for button settings """
        self.mgr.sendPacket = Mock()
        self.mgr.appMgr.sendPacket = Mock()
        self.mgr.buttonManager = Mock()
        self.mgr.buttonManager.getFreeButtonMapping = Mock()
        self.mgr.buttonManager.getFreeButtonMapping.return_value = (1, 2)
        value = struct.pack('<IIiiii', app_packet.SOLO_MESSAGE_GET_BUTTON_SETTING, 16, btn_msg.ButtonA, btn_msg.Press, 4, 12)
        self.mgr.appMgr.client.recv.return_value = value
        handled = self.mgr.appMgr.parse()
        packet = struct.pack('<IIiiii', app_packet.SOLO_MESSAGE_GET_BUTTON_SETTING, 16, btn_msg.ButtonA, btn_msg.Press, 1, 2)
        self.mgr.appMgr.sendPacket.assert_called_with(packet)

    def testSetButtonSettings(self):
        """ Test parsing the setting button settings """
        self.mgr.buttonManager = Mock()
        value = struct.pack('<IIiiii', app_packet.SOLO_MESSAGE_SET_BUTTON_SETTING, 16, btn_msg.ButtonA, btn_msg.Press, 13, 14)
        self.mgr.appMgr.client.recv.return_value = value
        handled = self.mgr.appMgr.parse()
        self.mgr.buttonManager.setFreeButtonMapping.assert_called_with(btn_msg.ButtonA, 13, 14)

    def testSetButtonSettingsNonPress(self):
        """ Don't allow setting of non-Press events """
        self.mgr.buttonManager = Mock()
        value = struct.pack('<IIiiii', app_packet.SOLO_MESSAGE_SET_BUTTON_SETTING, 16, btn_msg.ButtonA, btn_msg.Hold, 13, 14)
        self.mgr.appMgr.client.recv.return_value = value
        handled = self.mgr.appMgr.parse()
        self.assertFalse( self.mgr.buttonManager.setFreeButtonMapping.called )

    def testGoProSetRequest(self):
        """ Test parsing gopro set request """
        self.mgr.goproManager = Mock()
        value = struct.pack('<IIHH', app_packet.GOPRO_SET_REQUEST, 4, 12, 2)
        trimValue = struct.pack('<HH', 12, 2)
        self.mgr.appMgr.client.recv.return_value = value
        handled = self.mgr.appMgr.parse()
        self.mgr.goproManager.handlePacket.assert_called_with(app_packet.GOPRO_SET_REQUEST, trimValue)

    def testGoProRecord(self):
        """ Test parsing gopro record """
        self.mgr.goproManager = Mock()
        value = struct.pack('<III', app_packet.GOPRO_RECORD, 4, 27)
        trimValue = struct.pack('<I', 27)
        self.mgr.appMgr.client.recv.return_value = value
        handled = self.mgr.appMgr.parse()
        self.mgr.goproManager.handlePacket.assert_called_with(app_packet.GOPRO_RECORD, trimValue)

    def testGoProRequestState(self):
        """ Test parsing gopro request state """
        self.mgr.goproManager = Mock()
        value = struct.pack('<II', app_packet.GOPRO_REQUEST_STATE, 0)
        trimValue = ''
        self.mgr.appMgr.client.recv.return_value = value
        handled = self.mgr.appMgr.parse()
        self.mgr.goproManager.handlePacket.assert_called_with(app_packet.GOPRO_REQUEST_STATE, trimValue)

    def testGoProSetExtendedRequest(self):
        """ Test parsing gopro set request with extended payload """
        self.mgr.goproManager = Mock()
        value = struct.pack('<IIHBBBB', app_packet.GOPRO_SET_EXTENDED_REQUEST, 6, 5, 0, 3, 7, 1)
        trimValue = struct.pack('<HBBBB', 5, 0, 3, 7, 1)
        self.mgr.appMgr.client.recv.return_value = value
        handled = self.mgr.appMgr.parse()
        self.mgr.goproManager.handlePacket.assert_called_with(app_packet.GOPRO_SET_EXTENDED_REQUEST, trimValue)

    def testUnknownType(self):
        """ Test parsing an incoming unknown packet """
        appManager.logger = Mock()
        value = struct.pack('<III', 3333, 4, 4444)
        self.mgr.appMgr.client = Mock(specs=['recv'])
        self.mgr.appMgr.client.recv.return_value = value
        handled = self.mgr.appMgr.parse()
        appManager.logger.log.assert_called_with("[app]: Got an unknown packet type: %d."%(3333))

class TestConnectClient(unittest.TestCase):
    @patch.object(socket.socket, 'bind')
    def setUp(self, mock_bind):
        self.mgr = shotManager.ShotManager()
        self.v = mock.create_autospec(Vehicle)
        self.mgr.Start(self.v)
        self.mgr.buttonManager = Mock()
        self.mgr.appMgr.server = Mock()
        self.client = Mock()
        address = (3333,)
        self.mgr.appMgr.server.accept = Mock(return_value=(self.client, address))

    def testConnect(self):
        """ Connect should set things up """
        self.mgr.goproManager = Mock()
        self.mgr.appMgr.connectClient()
        self.assertEqual(self.mgr.appMgr.client, self.client)
        self.client.setblocking.assert_called_with(0)
        self.assertTrue( self.client in self.mgr.inputs )
        self.assertTrue( self.mgr.appMgr.clientQueue != None )
        self.mgr.buttonManager.setButtonMappings.assert_called_with()
        self.mgr.goproManager.sendState.assert_called_with()

    def testAlreadyHaveDifferentClient(self):
        """ If we're already connected to a client, we should accept and then close it """
        self.mgr.appMgr.disconnectClient = Mock()
        self.mgr.appMgr.isAppConnected = Mock(return_value=True)
        self.mgr.appMgr.client_address = (4444,)
        self.mgr.appMgr.connectClient()
        # we need to accept this new connection and then close it
        self.client.close.assert_called_with()

    def testAlreadyHaveSameClient(self):
        """ If we're already connected to a client, we should accept and then close it """
        self.mgr.appMgr.disconnectClient = Mock()
        self.mgr.appMgr.isAppConnected = Mock(return_value=True)
        self.mgr.appMgr.client_address = (3333,)
        self.mgr.appMgr.connectClient()
        # we need to accept this new connection and then close it
        self.mgr.appMgr.disconnectClient.assert_called_with()

class TestDisconnectClient(unittest.TestCase):
    @patch.object(socket.socket, 'bind')
    def setUp(self, mock_bind):
        self.mgr = shotManager.ShotManager()
        self.v = mock.create_autospec(Vehicle)
        self.mgr.Start(self.v)
        self.mgr.buttonManager = Mock()
        self.mgr.enterShot = Mock()
        self.mgr.appMgr.client = Mock()
        self.mgr.inputs = [self.mgr.appMgr.client]

    def testDisconnectRemovesOutput(self):
        """ Make sure disconnecting a client removes it from outputs """
        client = self.mgr.appMgr.client
        self.mgr.outputs = [self.mgr.appMgr.client]
        self.mgr.appMgr.isAppConnected = Mock(return_value=True)
        self.mgr.appMgr.disconnectClient()
        self.assertFalse( client in self.mgr.outputs )

    def testDisconnectRemovesInput(self):
        """ Make sure disconnecting a client removes it from inputs """
        client = self.mgr.appMgr.client
        self.mgr.appMgr.isAppConnected = Mock(return_value=True)
        self.mgr.appMgr.disconnectClient()
        self.assertFalse( client in self.mgr.inputs )

    def testDisconnectClosesClientSocket(self):
        """ Make sure disconnecting a client closes the client socket """
        client = self.mgr.appMgr.client
        self.mgr.appMgr.isAppConnected = Mock(return_value=True)
        self.mgr.appMgr.disconnectClient()
        client.close.assert_called_with()

    def testDisconnectClearsOutClient(self):
        """ Make sure disconnecting a client sets client and clientQueue to None """
        client = self.mgr.appMgr.client
        self.mgr.appMgr.isAppConnected = Mock(return_value=True)
        self.mgr.appMgr.disconnectClient()
        self.assertEqual( self.mgr.appMgr.client, None )
        self.assertEqual( self.mgr.appMgr.clientQueue, None )

    def testDisconnectRemapsButtons(self):
        """ Make sure disconnecting a client remaps buttons """
        client = self.mgr.appMgr.client
        self.mgr.appMgr.isAppConnected = Mock(return_value=True)
        self.mgr.appMgr.disconnectClient()
        self.mgr.buttonManager.setButtonMappings.assert_called_with()

    def testDisconnectTurnsOffShots(self):
        """ Make sure disconnecting turns off shots """
        self.mgr.currentShot = shots.APP_SHOT_ORBIT
        client = self.mgr.appMgr.client
        self.mgr.appMgr.isAppConnected = Mock(return_value=True)
        self.mgr.appMgr.disconnectClient()
        self.mgr.enterShot.assert_called_with(shots.APP_SHOT_NONE)

    def testDisconnectTwice(self):
        """ Make sure we can call disconnect twice in a row without error """
        client = self.mgr.appMgr.client
        self.mgr.appMgr.isAppConnected = Mock(side_effect=[True,False])
        self.mgr.appMgr.disconnectClient()
        self.mgr.appMgr.disconnectClient()