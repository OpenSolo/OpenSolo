# Unit tests for GoProManager
import mock
from mock import call
from mock import Mock
from mock import patch
import os
from os import sys, path
import struct
import monotonic
import unittest

from pymavlink import mavutil

sys.path.append(os.path.realpath('..'))
import app_packet
import GoProManager
from GoProConstants import *

class TestStatusCallback(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.v = Mock()
        self.v.message_factory = Mock()
        shotmgr.vehicle = self.v
        self.mgr = GoProManager.GoProManager(shotmgr)
        self.mgr.sendGoProRequest = Mock()
        self.mgr.sendState = Mock()

    def testStartup(self):
        """ GoPro status on startup should be GOPRO_HEARTBEAT_STATUS_DISCONNECTED """
        self.assertEqual( self.mgr.status, mavutil.mavlink.GOPRO_HEARTBEAT_STATUS_DISCONNECTED)
        self.assertFalse( self.mgr.sendState.called )

    def testConnected(self):
        """ Test connected status """
        message = Mock(spec=["status", "capture_mode", "flags"])
        message.status = mavutil.mavlink.GOPRO_HEARTBEAT_STATUS_CONNECTED
        message.capture_mode = mavutil.mavlink.GOPRO_CAPTURE_MODE_VIDEO
        message.flags = 0
        #message = (mavutil.mavlink.GOPRO_HEARTBEAT_STATUS_CONNECTED, mavutil.mavlink.GOPRO_CAPTURE_MODE_VIDEO, 0)
        self.mgr.state_callback('vehicle','name', message)
        self.assertEqual( self.mgr.status, mavutil.mavlink.GOPRO_HEARTBEAT_STATUS_CONNECTED)
        self.mgr.sendState.assert_called_with()
        # when we connect, we should fetch status info (check last request called)
        self.mgr.sendGoProRequest.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_PROTUNE_EXPOSURE)

class TestGetResponseCallback(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.v = Mock()
        shotmgr.vehicle = self.v
        self.mgr = GoProManager.GoProManager(shotmgr)
        self.mgr.processMsgQueue = Mock()
        self.mgr.sendState = Mock()

    def testCaptureResponse(self):
        """ Test that capture response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_CAPTURE_MODE, mavutil.mavlink.GOPRO_REQUEST_SUCCESS, (CAPTURE_MODE_BURST, 0, 0, 0))
        self.mgr.get_response_callback('vehicle','name', message)
        self.assertEqual( self.mgr.captureMode, CAPTURE_MODE_BURST)
        self.mgr.processMsgQueue.assert_called_with()
        self.mgr.sendState.assert_called_with()

    def testBatteryResponse(self):
        """ Test that battery response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_BATTERY, mavutil.mavlink.GOPRO_REQUEST_SUCCESS, (72, 0, 0, 0))
        self.mgr.get_response_callback('vehicle','name', message)
        self.assertEqual( self.mgr.battery, 72)
        self.mgr.processMsgQueue.assert_called_with()

    def testModelResponse(self):
        """ Test that model response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_MODEL, mavutil.mavlink.GOPRO_REQUEST_SUCCESS, (MODEL_HERO3PLUS_BLACK, 0, 0, 0))
        self.mgr.get_response_callback('vehicle','name', message)
        self.assertEqual( self.mgr.model, MODEL_HERO3PLUS_BLACK)
        self.mgr.processMsgQueue.assert_called_with()
        self.mgr.sendState.assert_called_with()

    def testVideoSettingsResponse(self):
        """ Test that the video settings response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_VIDEO_SETTINGS, mavutil.mavlink.GOPRO_REQUEST_SUCCESS, (mavutil.mavlink.GOPRO_RESOLUTION_1080p, mavutil.mavlink.GOPRO_FRAME_RATE_60, mavutil.mavlink.GOPRO_FIELD_OF_VIEW_WIDE, VIDEO_FORMAT_NTSC))
        self.mgr.get_response_callback('vehicle','name', message)
        self.assertEqual(self.mgr.videoResolution, mavutil.mavlink.GOPRO_RESOLUTION_1080p)
        self.assertEqual(self.mgr.videoFrameRate, mavutil.mavlink.GOPRO_FRAME_RATE_60)
        self.assertEqual(self.mgr.videoFieldOfView, mavutil.mavlink.GOPRO_FIELD_OF_VIEW_WIDE)
        self.assertEqual(self.mgr.videoFormat, VIDEO_FORMAT_NTSC)
        self.mgr.processMsgQueue.assert_called_with()
        self.mgr.sendState.assert_called_with()

class TestSetResponseCallback(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.v = Mock()
        shotmgr.vehicle = self.v
        self.mgr = GoProManager.GoProManager(shotmgr)
        self.mgr.processMsgQueue = Mock()

    def testPowerOnResponse(self):
        """ Test that power on response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_POWER, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testCaptureModeResponse(self):
        """ Test that capture mode response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_CAPTURE_MODE, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testShutterResponse(self):
        """ Test that shutter response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_SHUTTER, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testVideoSettingsResponse(self):
        """ Test that video settings response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_VIDEO_SETTINGS, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testVideoLowLightResponse(self):
        """ Test that video protune response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_LOW_LIGHT, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testPhotoResolutionResponse(self):
        """ Test that photo resolution response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_PHOTO_RESOLUTION, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testPhotoBurstRateResponse(self):
        """ Test that photo burst rate response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_PHOTO_BURST_RATE, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testVideoProtuneResponse(self):
        """ Test that video protune response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_PROTUNE, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testVideoProtuneWhiteBalanceResponse(self):
        """ Test that video protune white balance response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_PROTUNE_WHITE_BALANCE, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testVideoProtuneColorResponse(self):
        """ Test that video protune color response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_PROTUNE_COLOUR, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testVideoProtuneGainResponse(self):
        """ Test that video protune gain response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_PROTUNE_GAIN, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testVideoProtuneSharpnessResponse(self):
        """ Test that video protune sharpness response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_PROTUNE_SHARPNESS, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testVideoProtuneExposureResponse(self):
        """ Test that video protune exposure response works """
        message = (mavutil.mavlink.GOPRO_COMMAND_PROTUNE_EXPOSURE, mavutil.mavlink.GOPRO_REQUEST_SUCCESS)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.processMsgQueue.assert_called_with()

    def testFailedResponse(self):
        """ Test that failed request sends state back to client """
        self.mgr.sendState = Mock()
        message = (mavutil.mavlink.GOPRO_COMMAND_VIDEO_SETTINGS, mavutil.mavlink.GOPRO_REQUEST_FAILED)
        self.mgr.set_response_callback('vehicle','name', message)
        self.mgr.sendState.assert_called_with()
        self.mgr.processMsgQueue.assert_called_with()


class TestSendGoProRequest(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.v = Mock()
        self.v.message_factory = Mock()
        shotmgr.vehicle = self.v
        self.mgr = GoProManager.GoProManager(shotmgr)
        self.mgr.queueMsg = Mock()

    def testSendBattery(self):
        """ Test sending a request to the Gopro for its battery life """
        self.v.message_factory.gopro_get_request_encode.return_value = 7
        self.mgr.sendGoProRequest(mavutil.mavlink.GOPRO_COMMAND_BATTERY)

        self.v.message_factory.gopro_get_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_BATTERY)
        self.mgr.queueMsg.assert_called_with(7)

    def testInvalidRequest(self):
        """ Test sending an invalid request """
        self.mgr.sendGoProRequest(141)
        self.assertFalse(self.v.message_factory.gopro_set_request_encode.called)


class TestSendGoProCommand(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.v = Mock()
        self.v.message_factory = Mock()
        shotmgr.vehicle = self.v
        self.mgr = GoProManager.GoProManager(shotmgr)
        self.mgr.queueMsg = Mock()

    def testSendModeChange(self):
        """ If we send a mode change command, we need to follow it up with a mode request to make sure it worked """
        self.mgr.sendGoProRequest = Mock()
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_CAPTURE_MODE, (1, 0, 0, 0))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_CAPTURE_MODE, (1, 0, 0, 0))
        self.mgr.queueMsg.assert_called_with(3)

    def testSendShutterTo1(self):
        """ Test sending a shutter command with value 1 """
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_SHUTTER, (1, 0, 0, 0))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_SHUTTER, (1, 0, 0, 0))
        self.mgr.queueMsg.assert_called_with(3)

    def testSendVideoSettingsChange(self):
        """ Test sending a video settings command """
        self.mgr.sendGoProRequest = Mock()
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_VIDEO_SETTINGS, (0, 3, 7, 1))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_VIDEO_SETTINGS, (0, 3, 7, 1))
        self.mgr.queueMsg.assert_called_with(3)
        self.mgr.sendGoProRequest.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_VIDEO_SETTINGS)

    def testSendVideoLowLight(self):
        """ Test sending a video low light command """
        self.mgr.sendGoProRequest = Mock()
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_LOW_LIGHT, (1, 0, 0, 0))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_LOW_LIGHT, (1, 0, 0, 0))
        self.mgr.queueMsg.assert_called_with(3)
        self.mgr.sendGoProRequest.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_LOW_LIGHT)

    def testSendPhotoResolution(self):
        """ Test sending a photo resolution command """
        self.mgr.sendGoProRequest = Mock()
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_PHOTO_RESOLUTION, (1, 0, 0, 0))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_PHOTO_RESOLUTION, (1, 0, 0, 0))
        self.mgr.queueMsg.assert_called_with(3)
        self.mgr.sendGoProRequest.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_PHOTO_RESOLUTION)

    def testSendPhotoBurstRate(self):
        """ Test sending a photo burst rate command """
        self.mgr.sendGoProRequest = Mock()
        self.mgr.sendGoProRequest = Mock()
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_PHOTO_BURST_RATE, (1, 0, 0, 0))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_PHOTO_BURST_RATE, (1, 0, 0, 0))
        self.mgr.queueMsg.assert_called_with(3)
        self.mgr.sendGoProRequest.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_PHOTO_BURST_RATE)

    def testSendVideoProtune(self):
        """ Test sending a video protune command """
        self.mgr.sendGoProRequest = Mock()
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_PROTUNE, (1, 0, 0, 0))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_PROTUNE, (1, 0, 0, 0))
        self.mgr.queueMsg.assert_called_with(3)
        self.mgr.sendGoProRequest.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_PROTUNE)


    def testSendVideoProtuneWhiteBalance(self):
        """ Test sending a video protune white balance command """
        self.mgr.sendGoProRequest = Mock()
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_PROTUNE_WHITE_BALANCE, (1, 0, 0, 0))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_PROTUNE_WHITE_BALANCE, (1, 0, 0, 0))
        self.mgr.queueMsg.assert_called_with(3)
        self.mgr.sendGoProRequest.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_PROTUNE_WHITE_BALANCE)


    def testSendVideoProtuneColor(self):
        """ Test sending a video protune color command """
        self.mgr.sendGoProRequest = Mock()
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_PROTUNE_COLOUR, (1, 0, 0, 0))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_PROTUNE_COLOUR, (1, 0, 0, 0))
        self.mgr.queueMsg.assert_called_with(3)
        self.mgr.sendGoProRequest.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_PROTUNE_COLOUR)


    def testSendVideoProtuneGain(self):
        """ Test sending a video protune gain command """
        self.mgr.sendGoProRequest = Mock()
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_PROTUNE_GAIN, (1, 0, 0, 0))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_PROTUNE_GAIN, (1, 0, 0, 0))
        self.mgr.queueMsg.assert_called_with(3)
        self.mgr.sendGoProRequest.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_PROTUNE_GAIN)

    def testSendVideoProtuneSharpness(self):
        """ Test sending a video protune sharpness command """
        self.mgr.sendGoProRequest = Mock()
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_PROTUNE_SHARPNESS, (1, 0, 0, 0))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_PROTUNE_SHARPNESS, (1, 0, 0, 0))
        self.mgr.queueMsg.assert_called_with(3)
        self.mgr.sendGoProRequest.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_PROTUNE_SHARPNESS)


    def testSendVideoProtuneExposure(self):
        """ Test sending a video protune exposure command """
        self.mgr.sendGoProRequest = Mock()
        self.v.message_factory.gopro_set_request_encode.return_value = 3
        self.mgr.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_PROTUNE_EXPOSURE, (1, 0, 0, 0))

        self.v.message_factory.gopro_set_request_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,
                            mavutil.mavlink.GOPRO_COMMAND_PROTUNE_EXPOSURE, (1, 0, 0, 0))
        self.mgr.queueMsg.assert_called_with(3)
        self.mgr.sendGoProRequest.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_PROTUNE_EXPOSURE)

    def testInvalidCommand(self):
        """ Test sending an invalid command """
        self.mgr.sendGoProCommand(140, (1, 0, 0, 0))
        self.assertFalse(self.v.message_factory.gopro_set_request_encode.called)

class TestHandleRecordCommand(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.v = Mock()
        self.v.message_factory = Mock()
        shotmgr.vehicle = self.v
        self.mgr = GoProManager.GoProManager(shotmgr)
        self.mgr.status = mavutil.mavlink.GOPRO_HEARTBEAT_STATUS_CONNECTED
        self.mgr.sendGoProCommand = Mock()
        self.mgr.sendState = Mock()

    def testStartRecord(self):
        """ Test starting video recording """
        self.mgr.handleRecordCommand( CAPTURE_MODE_VIDEO, RECORD_COMMAND_START )
        self.mgr.sendGoProCommand.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_SHUTTER, (1, 0, 0, 0))

    def testStartRecordAlreadyRecording(self):
        """ Test starting video recording while already recording """
        self.mgr.isRecording = True
        self.mgr.captureMode = CAPTURE_MODE_VIDEO
        self.mgr.handleRecordCommand( CAPTURE_MODE_VIDEO, RECORD_COMMAND_START )
        self.assertTrue(self.mgr.isRecording)
        assert not self.mgr.sendGoProCommand.called
        assert not self.mgr.sendState.called

    def testSwitchToStillsAndTakeAStill(self):
        """ Should switch modes to still and take a still """
        self.mgr.captureMode = CAPTURE_MODE_VIDEO
        self.mgr.handleRecordCommand( CAPTURE_MODE_PHOTO, RECORD_COMMAND_START )
        self.assertFalse(self.mgr.isRecording)
        call1 = call(mavutil.mavlink.GOPRO_COMMAND_CAPTURE_MODE, (CAPTURE_MODE_PHOTO, 0, 0, 0))
        call2 = call(mavutil.mavlink.GOPRO_COMMAND_SHUTTER, (1, 0, 0, 0))

        self.mgr.sendGoProCommand.assert_has_calls( [call1, call2] )

    def testToggleStartRecord(self):
        """ If we're not recording, start recording """
        self.mgr.captureMode = CAPTURE_MODE_VIDEO
        self.mgr.handleRecordCommand( CAPTURE_MODE_VIDEO, RECORD_COMMAND_TOGGLE )
        self.mgr.sendGoProCommand.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_SHUTTER, (1, 0, 0, 0))

    def testToggleStopRecord(self):
        """ If we're recording, stop recording """
        self.mgr.captureMode = CAPTURE_MODE_VIDEO
        self.mgr.isRecording = True
        self.mgr.handleRecordCommand( CAPTURE_MODE_VIDEO, RECORD_COMMAND_TOGGLE )
        self.mgr.sendGoProCommand.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_SHUTTER, (0, 0, 0, 0))

    def testStartBurstShot(self):
        '''If GoPro is in burst shot mode then record button takes a burst shot'''
        self.mgr.captureMode = CAPTURE_MODE_BURST
        self.mgr.handleRecordCommand( CAPTURE_MODE_BURST, RECORD_COMMAND_START )
        self.mgr.sendGoProCommand.assert_called_with(mavutil.mavlink.GOPRO_COMMAND_SHUTTER, (1, 0, 0, 0))

    def testWrongMode(self):
        """ Don't do anything if we're not in the right mode """
        self.mgr.status = mavutil.mavlink.GOPRO_HEARTBEAT_STATUS_DISCONNECTED
        self.mgr.handleRecordCommand( CAPTURE_MODE_VIDEO, RECORD_COMMAND_TOGGLE )
        self.assertFalse(self.mgr.sendGoProCommand.called)

class TestQueueMsg(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.v = Mock()
        shotmgr.vehicle = self.v
        self.mgr = GoProManager.GoProManager(shotmgr)

    def testQueueMsg(self):
        """ Test queuing up a message """
        self.mgr.isGoproBusy = True
        self.mgr.lastRequestSent = monotonic.monotonic()
        self.mgr.queueMsg(4)
        self.assertFalse( self.mgr.msgQueue.empty() )
        self.assertTrue(self.mgr.isGoproBusy)

    def testQueueMultiMsg(self):
        """ Test queuing up multiple messages """
        for i in range(10):
            self.mgr.queueMsg(i)

        self.assertEqual( self.mgr.msgQueue.qsize(), 9)

    def testQueueSend(self):
        """ if the queue is not busy, we start sending a message instead of queuing up """
        self.mgr.queueMsg(37)
        self.assertTrue( self.mgr.msgQueue.empty() )
        self.v.send_mavlink.assert_called_with(37)

    def testQueueFlushQueue(self):
        """ Test queue is flushed with outstanding message sent more than 2 seconds ago """
        self.mgr.sendState = Mock()
        self.mgr.isGoproBusy = True
        self.mgr.lastRequestSent = monotonic.monotonic()
        self.mgr.queueMsg(1)
        self.mgr.queueMsg(2)
        self.assertEqual(self.mgr.msgQueue.qsize(), 2)
        self.mgr.lastRequestSent = monotonic.monotonic() - 3.0
        self.mgr.queueMsg(3)
        self.assertTrue(self.mgr.msgQueue.empty)
        self.mgr.sendState.assert_called_with()

class TestProcessMsgQueue(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.v = Mock()
        shotmgr.vehicle = self.v
        self.mgr = GoProManager.GoProManager(shotmgr)

    def testSendNextMessage(self):
        """ send the next message in the queue """
        self.mgr.isGoproBusy = True
        self.mgr.lastRequestSent = monotonic.monotonic()
        self.mgr.queueMsg(3)
        self.mgr.queueMsg(2)
        self.mgr.queueMsg(1)
        self.mgr.processMsgQueue()
        self.v.send_mavlink.assert_called_with(3)
        self.assertEqual( self.mgr.msgQueue.qsize(), 2)

    def testQueueisEmpty(self):
        """ if our queue is empty, set ourselves to not busy """
        self.mgr.isGoproBusy = True
        self.mgr.processMsgQueue()
        self.assertFalse( self.mgr.isGoproBusy )

class TestHandlePacket(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.mgr = GoProManager.GoProManager(shotmgr)

    def testEnableGoPro(self):
        """ Should enable gopro commands """
        pkt = struct.pack('<I', 1)
        self.mgr.setGoProEnabled = Mock()
        self.mgr.handlePacket(app_packet.GOPRO_SET_ENABLED, pkt)
        self.mgr.setGoProEnabled.assert_called_with(True)

    def testSetRequest(self):
        """ Handle a set request """
        self.mgr.sendGoProCommand = Mock()
        value = struct.pack('<HH', 8, 22)
        self.mgr.handlePacket(app_packet.GOPRO_SET_REQUEST, value)
        self.mgr.sendGoProCommand.assert_called_with( 8, (22, 0, 0, 0) )

    def testRecord(self):
        """ Handle a record packet """
        self.mgr.handleRecordCommand = Mock()
        self.mgr.captureMode = CAPTURE_MODE_VIDEO
        value = struct.pack('<I', 1)
        self.mgr.handlePacket(app_packet.GOPRO_RECORD, value)
        self.mgr.handleRecordCommand.assert_called_with( CAPTURE_MODE_VIDEO, 1 )

    def testStateRequest(self):
        """ Should send state on request """
        pkt = struct.pack('<')
        self.mgr.sendState = Mock()
        self.mgr.handlePacket(app_packet.GOPRO_REQUEST_STATE, pkt)
        self.mgr.sendState.assert_called_with()

    def testSetExtendedRequest(self):
        """ Handle extended payload settings request """
        self.mgr.sendGoProCommand = Mock()
        value = struct.pack('<HBBBB', 5, 0, 3, 7, 1)
        self.mgr.handlePacket(app_packet.GOPRO_SET_EXTENDED_REQUEST, value)
        self.mgr.sendGoProCommand.assert_called_with(5, (0, 3, 7, 1))

class TestSendState(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.mgr = GoProManager.GoProManager(shotmgr)

    def testSendState(self):
        """ Send state sends the current gopro state to the app """
        self.mgr.enabled = 1
        self.mgr.model = MODEL_HERO3PLUS_BLACK
        self.mgr.status = STATUS_GOPRO_CONNECTED
        self.mgr.isRecording = False
        self.mgr.captureMode = CAPTURE_MODE_VIDEO
        self.mgr.videoFormat = VIDEO_FORMAT_NTSC
        self.mgr.videoResolution = 3
        self.mgr.videoFrameRate = 1
        self.mgr.videoFieldOfView = 2
        self.mgr.videoLowLight = True
        self.mgr.photoResolution = 1
        self.mgr.photoBurstRate = 2
        self.mgr.videoProtune = True
        self.mgr.videoProtuneWhiteBalance = 2
        self.mgr.videoProtuneColor = 1
        self.mgr.videoProtuneGain = 3
        self.mgr.videoProtuneSharpness = 2
        self.mgr.videoProtuneExposure = 1

        # Send old spec version
        # 2 unsigned shorts for a header, 26 unsigned bytes, then 5 unsigned shorts
        pkt1 = struct.pack('<IIBBBBBBBBBBBBBBBBBBBBBBBBBBHHHHH', app_packet.GOPRO_V1_STATE, 36, \
            GOPRO_V1_SPEC_VERSION,
            self.mgr.model,
            self.mgr.status,
            self.mgr.isRecording,
            self.mgr.captureMode,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0
            )

        # send new spec version
        # 2 unsigned shorts for a header, 26 unsigned bytes, then 5 unsigned shorts
        pkt2 = struct.pack('<IIBBBBBBBBBBBBBBBBBBBBBBBBBBHHHHH', app_packet.GOPRO_V2_STATE, 36, \
            GOPRO_V2_SPEC_VERSION,
            self.mgr.model,
            self.mgr.status,
            self.mgr.isRecording,
            self.mgr.captureMode,
            self.mgr.videoFormat,
            self.mgr.videoResolution,
            self.mgr.videoFrameRate,
            self.mgr.videoFieldOfView,
            self.mgr.videoLowLight,
            self.mgr.photoResolution,
            self.mgr.photoBurstRate,
            self.mgr.videoProtune,
            self.mgr.videoProtuneWhiteBalance,
            self.mgr.videoProtuneColor,
            self.mgr.videoProtuneGain,
            self.mgr.videoProtuneSharpness,
            self.mgr.videoProtuneExposure,
            self.mgr.enabled,
            0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0
            )

        self.mgr.sendState()
        call1 = call(pkt1)
        call2 = call(pkt2)
        self.mgr.shotMgr.appMgr.sendPacket.assert_has_calls([call1, call2])

class TestSetGimbalEnabledParam(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.mgr = GoProManager.GoProManager(shotmgr)

    def testSetEnabled(self):
        """ Tell gimbal to turn on gopro commands """
        self.mgr.enabled = True
        self.mgr.setGimbalEnabledParam()
        self.mgr.shotMgr.vehicle.message_factory.param_set_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,    # target system, target component
                                                        "GMB_GP_CTRL", 1.0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32 )

    def testSetDisabled(self):
        """ Tell gimbal to turn off gopro commands """
        self.mgr.enabled = False
        self.mgr.setGimbalEnabledParam()
        self.mgr.shotMgr.vehicle.message_factory.param_set_encode.assert_called_with(0, mavutil.mavlink.MAV_COMP_ID_GIMBAL,    # target system, target component
                                                        "GMB_GP_CTRL", 0.0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32 )

class TestSetGoProEnabled(unittest.TestCase):
    def setUp(self):
        shotmgr = Mock()
        self.mgr = GoProManager.GoProManager(shotmgr)
        mock = patch('settings.writeSetting')
        self.addCleanup(mock.stop)
        self.mockWrite = mock.start()
        self.mgr.setGimbalEnabledParam = Mock()

    def testSetEnabled(self):
        """ Tell gimbal to turn on gopro commands """
        self.mgr.setGoProEnabled(True)
        self.assertTrue(self.mgr.enabled)
        self.mockWrite.assert_called_with("GoProEnabled", "1")
        self.mgr.setGimbalEnabledParam.assert_called_with()

    def testSetDisabled(self):
        """ Tell gimbal to turn off gopro commands """
        self.mgr.setGoProEnabled(False)
        self.assertFalse(self.mgr.enabled)
        self.mockWrite.assert_called_with("GoProEnabled", "0")
        self.mgr.setGimbalEnabledParam.assert_called_with()