# Unit tests for buttonManager
import mock
from mock import call
from mock import Mock
from mock import patch
import os
from os import sys, path

import unittest

sys.path.append(os.path.realpath('..'))
import buttonManager
import GeoFenceManager
import shots
from dronekit import Vehicle

# on host systems these files are located here
from sololink import btn_msg
import shotManager
import struct
import app_packet


class TestHandleButtons(unittest.TestCase):
    def setUp(self):
        self.mgr = shotManager.ShotManager()
        self.mgr.rcMgr = Mock()
        self.mgr.buttonManager = buttonManager.buttonManager(self.mgr)
        self.mgr.lastMode = "LOITER"
        self.mgr.appMgr = Mock()
        self.mgr.vehicle = mock.create_autospec(Vehicle)
        self.mgr.vehicle.system_status = 'ACTIVE'
        self.mgr.sendPacket = Mock()
        self.mgr.goproManager = Mock()
        self.mgr.geoFenceManager = GeoFenceManager.GeoFenceManager(self.mgr)

    def tearDown(self):
        del self.mgr

    def testHandleButtonsNoEvent(self):
        """ Testing handle Buttons with no event """
        self.mgr.buttonManager.handleButtons(None)

    def testHandleButtonsStartShot(self):
        """ Test starting a shot via button press """
        whichShots = [shots.APP_SHOT_ORBIT, shots.APP_SHOT_CABLECAM]

        self.mgr.client = 5
        self.mgr.vehicle.armed = True
        self.mgr.last_ekf_ok = True

        for i in whichShots:
            self.mgr.buttonManager.getFreeButtonMapping = Mock(return_value = (i, -1))
            self.mgr.currentShot = shots.APP_SHOT_NONE
            self.mgr.buttonManager.handleButtons((btn_msg.ButtonA, btn_msg.Press))
            self.assertEqual(self.mgr.currentShot, i)

    def testDisarmedStartShot(self):
        """ if we're not armed, we should not be able to start the shot """
        whichShots = [shots.APP_SHOT_ORBIT, shots.APP_SHOT_CABLECAM]

        self.mgr.client = 5
        self.mgr.vehicle.armed = False
        self.mgr.last_ekf_ok = True

        for i in whichShots:
            self.mgr.buttonManager.getFreeButtonMapping = Mock(return_value = (i, -1))
            self.mgr.currentShot = shots.APP_SHOT_NONE
            self.mgr.buttonManager.handleButtons((btn_msg.ButtonA, btn_msg.Press))
            self.assertEqual(self.mgr.currentShot, shots.APP_SHOT_NONE)
            packetDisallow = struct.pack('<III', app_packet.SOLO_SHOT_ERROR, 4, app_packet.SHOT_ERROR_UNARMED)
            self.mgr.appMgr.sendPacket.assert_any_call(packetDisallow)

    def testNotActiveStartShot(self):
        """ if we're not active, we should not be able to start the shot """
        whichShots = [shots.APP_SHOT_ORBIT, shots.APP_SHOT_CABLECAM, shots.APP_SHOT_MULTIPOINT]

        self.mgr.client = 5
        self.mgr.vehicle.armed = True
        self.mgr.vehicle.system_status = 'STANDBY'
        self.mgr.last_ekf_ok = True

        for i in whichShots:
            self.mgr.buttonManager.getFreeButtonMapping = Mock(return_value=(i, -1))
            self.mgr.currentShot = shots.APP_SHOT_NONE
            self.mgr.buttonManager.handleButtons((btn_msg.ButtonA, btn_msg.Press))
            self.assertEqual(self.mgr.currentShot, shots.APP_SHOT_NONE)
            packetDisallow = struct.pack('<III', app_packet.SOLO_SHOT_ERROR, 4, app_packet.SHOT_ERROR_UNARMED)
            self.mgr.appMgr.sendPacket.assert_any_call(packetDisallow)

    def testHandleButtonsStartMode(self):
        """ Test starting a mode via button press """

        self.mgr.buttonManager.getFreeButtonMapping = Mock(return_value = (-1, 3))
        self.mgr.currentShot = shots.APP_SHOT_NONE
        self.mgr.buttonManager.handleButtons((btn_msg.ButtonA, btn_msg.Press))
        self.assertEqual(self.mgr.vehicle.mode.name, 'AUTO')

    def testHandleButtonsExitShot(self):
        """ Test exiting a shot by pressing Fly """

        self.mgr.currentShot = shots.APP_SHOT_CABLECAM
        self.mgr.last_ekf_ok = True
        self.mgr.buttonManager.handleButtons((btn_msg.ButtonFly, btn_msg.Press))
        self.assertEqual( self.mgr.currentShot, shots.APP_SHOT_NONE )

    def testHandleButtonsPassToShot(self):
        """ Test passing a button press to a shot """

        self.mgr.currentShot = shots.APP_SHOT_CABLECAM
        self.mgr.curController = Mock()
        self.mgr.buttonManager.handleButtons((btn_msg.ButtonA, btn_msg.Press))
        self.mgr.curController.handleButton.assert_called_with(btn_msg.ButtonA, btn_msg.Press)


class TestButtonMappingSettings(unittest.TestCase):
    def setUp(self):
        with patch('buttonManager.buttonManager.connect') as mock:
            mock.read = Mock()
            mock.get = Mock()
            shotmgr = Mock()
            self.v = Mock()
            shotmgr.vehicle = self.v
            self.mgr = buttonManager.buttonManager(shotmgr)
            self.mgr.setArtooButton = Mock()
            buttonManager.connected = True

    def testSetButtonMappingsAppConnectedNoShotGoodEKF(self):
        """ Set Artoo's button mappings with app connected and no shot set and good EKF """
        self.mgr.shotMgr.appMgr.isAppConnected.return_value = True
        self.mgr.isButtonConnected = Mock(return_value=True)
        self.mgr.shotMgr.currentShot = shots.APP_SHOT_NONE
        self.v.ekf_ok = True
        self.mgr.freeButtonMappings = [(shots.APP_SHOT_SELFIE, -1), (shots.APP_SHOT_CABLECAM, -1)]
        self.mgr.setButtonMappings()
        call1 = call(btn_msg.ButtonA, shots.APP_SHOT_SELFIE, btn_msg.ARTOO_BITMASK_ENABLED, "Selfie\0")
        call2 = call(btn_msg.ButtonB, shots.APP_SHOT_CABLECAM, btn_msg.ARTOO_BITMASK_ENABLED, "Cable Cam\0")
        self.mgr.setArtooButton.assert_has_calls( [call1, call2] )

    def testSetButtonMappingsAppConnectedNoShotBadEKF(self):
        """ Bad EKF should gray out shots """
        self.mgr.shotMgr.appMgr.isAppConnected.return_value = True
        self.mgr.isButtonConnected = Mock(return_value=True)
        self.mgr.shotMgr.currentShot = shots.APP_SHOT_NONE
        self.v.ekf_ok = False
        self.mgr.freeButtonMappings = [(shots.APP_SHOT_SELFIE, -1), (shots.APP_SHOT_CABLECAM, -1)]
        self.mgr.setButtonMappings()
        call1 = call(btn_msg.ButtonA, shots.APP_SHOT_SELFIE, 0, "Selfie\0")
        call2 = call(btn_msg.ButtonB, shots.APP_SHOT_CABLECAM, 0, "Cable Cam\0")
        self.mgr.setArtooButton.assert_has_calls( [call1, call2] )

    def testSetButtonMappingsAppConnectedNoShotBadEKF(self):
        """ Modes are still enabled with bad ekf """
        self.mgr.shotMgr.appMgr.isAppConnected.return_value = True
        self.mgr.isButtonConnected = Mock(return_value=True)
        self.mgr.shotMgr.currentShot = shots.APP_SHOT_NONE
        self.v.ekf_ok = False
        self.mgr.freeButtonMappings = [(shots.APP_SHOT_NONE, 1), (shots.APP_SHOT_NONE, 13)]
        self.mgr.setButtonMappings()
        call1 = call(btn_msg.ButtonA, shots.APP_SHOT_NONE, btn_msg.ARTOO_BITMASK_ENABLED, "Acro\0")
        call2 = call(btn_msg.ButtonB, shots.APP_SHOT_NONE, btn_msg.ARTOO_BITMASK_ENABLED, "Sport\0")
        self.mgr.setArtooButton.assert_has_calls( [call1, call2] )

    def testSetButtonMappingsAppConnectedNoShotSetModes(self):
        """ Set Artoo's button mappings with APM modes with app connected and no shot set """
        self.mgr.shotMgr.appMgr.isAppConnected.return_value = True
        self.mgr.isButtonConnected = Mock(return_value=True)
        self.mgr.shotMgr.currentShot = shots.APP_SHOT_NONE
        self.mgr.freeButtonMappings = [(shots.APP_SHOT_NONE, 0), (shots.APP_SHOT_NONE, 11)]
        self.mgr.setButtonMappings()
        call1 = call(btn_msg.ButtonA, shots.APP_SHOT_NONE, btn_msg.ARTOO_BITMASK_ENABLED, "Stabilize\0")
        call2 = call(btn_msg.ButtonB, shots.APP_SHOT_NONE, btn_msg.ARTOO_BITMASK_ENABLED, "Drift\0")
        self.mgr.setArtooButton.assert_has_calls( [call1, call2] )

    def testHasCurrentShot(self):
        """ Have the shot controller set buttons """
        self.mgr.shotMgr.appMgr.isAppConnected.return_value = True
        self.mgr.isButtonConnected = Mock(return_value=True)
        self.mgr.shotMgr.currentShot = shots.APP_SHOT_SELFIE
        self.mgr.shotMgr.curController = Mock()
        self.mgr.setButtonMappings()
        self.mgr.shotMgr.curController.setButtonMappings.assert_called_with()

    def testNoAppConnected(self):
        """ If there's no app connected, we shouldn't set a shot """
        self.mgr.shotMgr.appMgr.isAppConnected.return_value = False
        self.mgr.isButtonConnected = Mock(return_value=True)
        self.mgr.shotMgr.currentShot = shots.APP_SHOT_NONE
        self.mgr.freeButtonMappings = [(shots.APP_SHOT_ORBIT, -1), (shots.APP_SHOT_NONE, 2)]
        self.mgr.setButtonMappings()
        call1 = call(btn_msg.ButtonA, shots.APP_SHOT_ORBIT, 0, "Orbit\0")
        call2 = call(btn_msg.ButtonB, shots.APP_SHOT_NONE, btn_msg.ARTOO_BITMASK_ENABLED, "FLY: Manual\0")
        self.mgr.setArtooButton.assert_has_calls( [call1, call2] )


class TestButtonMappingSettingsBrakeButton(unittest.TestCase):
    def setUp(self):
        with patch('buttonManager.buttonManager.connect') as mock:
            mock.read = Mock()
            mock.get = Mock()
            shotmgr = Mock()
            self.v = Mock()
            shotmgr.vehicle = self.v
            self.mgr = buttonManager.buttonManager(shotmgr)
            self.mgr.setArtooButton = Mock()
            buttonManager.connected = True
            self.mgr.freeButtonMappings = [(shots.APP_SHOT_NONE, 1), (shots.APP_SHOT_NONE, 13)]

    def testAppDisarmedVehicleNoEKFNoBrake(self):
        """ Brake button is disabled if vehicle is disarmed """
        self.mgr.shotMgr.appMgr.isAppConnected.return_value = True
        self.mgr.isButtonConnected = Mock(return_value=True)
        self.mgr.shotMgr.currentShot = shots.APP_SHOT_NONE
        self.v.armed = False
        self.mgr.setButtonMappings()
        call1 = call(btn_msg.ButtonLoiter, shots.APP_SHOT_NONE, 0, "\0")
        self.mgr.setArtooButton.assert_has_calls( [call1] )

    def testAppDisarmedVehicleEKFNoBrake(self):
        """ Brake button is disabled if vehicle is disarmed """
        self.mgr.shotMgr.appMgr.isAppConnected.return_value = True
        self.mgr.isButtonConnected = Mock(return_value=True)
        self.mgr.shotMgr.currentShot = shots.APP_SHOT_NONE
        self.v.armed = False
        self.v.ekf_ok = True
        self.mgr.setButtonMappings()
        call1 = call(btn_msg.ButtonLoiter, shots.APP_SHOT_NONE, 0, "\0")
        self.mgr.setArtooButton.assert_has_calls( [call1] )

    def testAppArmedVehicleEKFBrake(self):
        """ Brake button is enabled if vehicle is armed and we have EKF """
        self.mgr.shotMgr.isAppConnected.return_value = True
        self.mgr.isButtonConnected = Mock(return_value=True)
        self.mgr.shotMgr.currentShot = shots.APP_SHOT_NONE
        self.v.armed = True
        self.v.ekf_ok = True
        self.mgr.setButtonMappings()
        call1 = call(btn_msg.ButtonLoiter, shots.APP_SHOT_NONE, btn_msg.ARTOO_BITMASK_ENABLED, "\0")
        self.mgr.setArtooButton.assert_has_calls( [call1] )


@patch('threading.Thread')
class TestSetFreeButtonMappings(unittest.TestCase):
    def setUp(self):
        with patch('buttonManager.buttonManager.connect') as mock:
            mock.read = Mock()
            mock.get = Mock()
            shotmgr = Mock()
            self.v = Mock()
            shotmgr.vehicle = self.v
            self.mgr = buttonManager.buttonManager(shotmgr)
            self.mgr.setArtooButton = Mock()
            buttonManager.connected = True
            self.mgr.freeButtonMappings = [(-1, -1), (-1, -1)]
            self.mgr.setButtonMappings = Mock()


    def testSetACableCam(self, mockThread):
        """ Set A to cable cam """
        self.mgr.setFreeButtonMapping( btn_msg.ButtonA, shots.APP_SHOT_CABLECAM, -1)
        self.mgr.setButtonMappings.assert_called_with()
        self.assertEqual( self.mgr.freeButtonMappings, [(shots.APP_SHOT_CABLECAM, -1), (-1, -1)])

    def testSetBManual(self, mockThread):
        """ Set B to manual """
        self.mgr.setFreeButtonMapping( btn_msg.ButtonB, -1, 2)
        self.mgr.setButtonMappings.assert_called_with()
        self.assertEqual( self.mgr.freeButtonMappings, [(-1, -1), (-1, 2)])

    def testSetFlyManual(self, mockThread):
        """ Shouldn't allow setting of Fly button """
        self.mgr.setFreeButtonMapping( btn_msg.ButtonFly, -1, 2)
        self.assertFalse( self.mgr.setButtonMappings.called )
        self.assertEqual( self.mgr.freeButtonMappings, [(-1, -1), (-1, -1)])

    def testSetInvalidShot(self, mockThread):
        """ Shouldn't allow setting an invalid shot """
        self.mgr.setFreeButtonMapping( btn_msg.ButtonA, 100, -1)
        self.assertFalse( self.mgr.setButtonMappings.called )
        self.assertEqual( self.mgr.freeButtonMappings, [(-1, -1), (-1, -1)])

    def testSetInvalidMode(self, mockThread):
        """ Shouldn't allow setting an invalid mode """
        self.mgr.setFreeButtonMapping( btn_msg.ButtonB, -1, 20)
        self.assertFalse( self.mgr.setButtonMappings.called )
        self.assertEqual( self.mgr.freeButtonMappings, [(-1, -1), (-1, -1)])

