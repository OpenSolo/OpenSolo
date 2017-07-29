#
# This file handles incoming buttons from Artoo
# It also handles all communication to Artoo
#

import errno
import os
import platform
import select
import socket
import string
import sys
import threading
import monotonic
import time
from pymavlink import mavutil
from dronekit import VehicleMode
sys.path.append(os.path.realpath(''))
import modes
import settings
import shots
import shotLogger
from sololink import btn_msg
from GoProConstants import *
import shots

PORT = 5016
# connect to our simulation
if os.path.dirname(__file__) != '/usr/bin':
    HOST = "localhost"
else:
    HOST = "10.1.1.1"

logger = shotLogger.logger

class buttonManager():
    def __init__(self, shotMgr):
        self.shotMgr = shotMgr
        self.connected = False
        self.buttonsInitialized = False
        self.connectingThread = None
        self.connect()
        # These are the mappings for the A,B buttons during Free Flight
        # The A+B buttons are mapped to shot, mode tuples
        # only one of which should ever be active at any time
        self.freeButtonMappings = [(-1, -1), (-1, -1)]

        try:
            aMapping = settings.readSetting("A")
            bMapping = settings.readSetting("B")

            values = string.split(aMapping, ",")
            self.freeButtonMappings[0] = (int(values[0]), int(values[1]))
            values = string.split(bMapping, ",")
            self.freeButtonMappings[1] = (int(values[0]), int(values[1]))

        except:
            logger.log("[button]: error reading config file")
        else:
            logger.log("[button]: read in button mappings")
            logger.log("[button]: Button A - shot %s, mode %s"%(shots.SHOT_NAMES[self.freeButtonMappings[0][0]], modes.MODE_NAMES[self.freeButtonMappings[0][1]]))
            logger.log("[button]: Button B - shot %s, mode %s"%(shots.SHOT_NAMES[self.freeButtonMappings[1][0]], modes.MODE_NAMES[self.freeButtonMappings[1][1]]))

    def connect(self):
        if not self.connectingThread or not self.connectingThread.is_alive():
            logger.log("[button]: Creating a new thread to connect to Artoo.")
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.setblocking(0)
            self.connectingThread = threading.Thread(target = self.connectThread)
            self.connectingThread.daemon = True
            self.connectingThread.start()

    def connectThread(self):
        while not self.connected:
            try:
                self.client.connect((HOST, PORT))
            except socket.error as e:
                pass
            finally:
                if e.errno == errno.EINPROGRESS:
                    time.sleep(1.0)
                elif e.errno == errno.ECONNREFUSED:
                    time.sleep(1.0)
                elif e.errno == errno.EALREADY:
                    time.sleep(1.0)
                elif e.errno == errno.EINVAL:
                    break
                elif e.errno == errno.EISCONN:
                    logger.log("[button]: Connected to Artoo.")
                    self.connected = True
                    self.buttonsInitialized = False
                else:
                    logger.log("[button]: Unexpected socket exception: %s" % e)
                    time.sleep(1.0)

    def parse(self):
        try:
            msg = btn_msg.recv(self.client)
            if not msg:
                raise Exception('No msg from Artoo.')
        except Exception as e:
            logger.log('[button]: Data from Artoo is nil.')
            self.disconnect()
        else:
            self.handleButtons((msg[1],msg[2]))
        
    def disconnect(self):
        logger.log('[button]: Disconnecting from Artoo.')
        self.shotMgr.inputs.remove(self.client)
        self.client.close()
        self.connected = False
        self.buttonsInitialized = False

    def checkButtonConnection(self):
        if not self.isButtonConnected():
            if not self.connectingThread or not self.connectingThread.is_alive():
                self.connect()
            return

        if not self.isButtonInited():
            self.shotMgr.inputs.append(self.client)
            self.setButtonMappings()
            self.setArtooShot(self.shotMgr.currentShot, self.shotMgr.currentModeIndex)
            self.buttonsInitialized = True

    # set Artoo's button mappings
    def setButtonMappings(self):
        if not self.isButtonConnected():
            return

        if self.shotMgr.currentShot == shots.APP_SHOT_NONE:
            aString = "\0"
            bString = "\0"

            enabled1 = btn_msg.ARTOO_BITMASK_ENABLED
            enabled2 = btn_msg.ARTOO_BITMASK_ENABLED

            if self.freeButtonMappings[0][0] >= 0:
                aString = shots.SHOT_NAMES[self.freeButtonMappings[0][0]]
                # if ekf is bad or the app is not connected, gray out
                if not self.shotMgr.vehicle.ekf_ok or not self.shotMgr.appMgr.isAppConnected():
                    enabled1 = 0
            elif self.freeButtonMappings[0][1] >= 0:
                aString = modes.MODE_NAMES[self.freeButtonMappings[0][1]]
            if self.freeButtonMappings[1][0] >= 0:
                bString = shots.SHOT_NAMES[self.freeButtonMappings[1][0]]
                # if ekf is bad or the app is not connected, gray out
                if not self.shotMgr.vehicle.ekf_ok or not self.shotMgr.appMgr.isAppConnected():
                    enabled2 = 0
            elif self.freeButtonMappings[1][1] >= 0:
                bString = modes.MODE_NAMES[self.freeButtonMappings[1][1]]

            self.setArtooButton(btn_msg.ButtonA, self.freeButtonMappings[0][0], enabled1, aString)
            self.setArtooButton(btn_msg.ButtonB, self.freeButtonMappings[1][0], enabled2, bString)
        else:
            self.shotMgr.curController.setButtonMappings()

        # only enable the pause button if we're armed
        brakeEnabled = self.shotMgr.vehicle.armed
        mask = btn_msg.ARTOO_BITMASK_ENABLED if brakeEnabled else 0
        self.setArtooButton(btn_msg.ButtonLoiter, shots.APP_SHOT_NONE, mask, "\0")

    def setArtooButton(self, button_id, shot, mask, string):
        if self.isButtonConnected():
            try:
                btn_msg.sendArtooString(self.client, button_id, shot, mask, string)
            except Exception as e:
                logger.log("[button]: %s" % e)
                self.disconnect()

    # Sends a single string to Artoo that it can display as the current user-facing mode
    # This is usually what shot the user is in, but if the user is not in a shot it can be the APM mode
    # Pass in the index of the shot and mode
    def setArtooShot(self, shot, mode = -1):
        if self.isButtonConnected():
            try:
                if shot == shots.APP_SHOT_NONE and mode >= 0:
                    btn_msg.sendShotString(self.client, modes.MODE_NAMES[mode].upper())
                    logger.log("[button]: sending %s to Artoo as mode"%(modes.MODE_NAMES[mode].upper()))
                else:
                    btn_msg.sendShotString(self.client, shots.SHOT_NAMES[shot].upper())
                    logger.log("[button]: sending %s to Artoo as shot"%(shots.SHOT_NAMES[shot].upper()))
            except:
                logger.log("[button]: %s" % e)
                self.disconnect()

    def getFreeButtonMapping(self, button):
        # our index is 0 -> Button A, 1 -> Button B
        index = button - btn_msg.ButtonA

        if index < 0 or index > 1:
            logger.log("[button]: Error, someone requested a button mapping for button %d"%(button))
            return (-1, -1)

        return self.freeButtonMappings[index]

    # update one of our free button mappings
    def setFreeButtonMapping(self, button, shot, APMmode):
        # our index is 0 -> Button A, 1 -> Button B
        index = button - btn_msg.ButtonA

        if index < 0 or index > 1:
            logger.log("[button]: Error, someone tried to map button %d"%(button))
            return

        if APMmode not in modes.MODE_NAMES.keys():
            logger.log("[button]: Error, someone tried to map an invalid mode %d"%(APMmode))
            return

        if shot not in shots.SHOT_NAMES.keys():
            logger.log("[button]: Error, someone tried to map an invalid shot %d"%(shot))
            return

        self.freeButtonMappings[index] = (shot, APMmode)
        self.setButtonMappings()

        buttonName = "A" if button == btn_msg.ButtonA else "B"
        value = "%d, %d"%(shot, APMmode)
        settings.writeSetting(buttonName, value)

    def isButtonConnected(self):
        return self.connected

    def isButtonInited(self):
        return self.buttonsInitialized

    def handleButtons(self, buttonEvent):

        if buttonEvent is None:
            return

        button, event = buttonEvent

        #if button == btn_msg.ButtonPreset1 and event == btn_msg.Press:
        #    crash
        
        if self.shotMgr.currentShot == shots.APP_SHOT_NONE:
            if event == btn_msg.Press:
                if button == btn_msg.ButtonA or button == btn_msg.ButtonB:
                    # see what the button is mapped to
                    (shot, mode) = self.getFreeButtonMapping(button)

                    # only allow entry into these shots if the app is attached
                    if shot in shots.CAN_START_FROM_ARTOO:
                        logger.log("[button]: Trying shot via Artoo button: %s" % shots.SHOT_NAMES[shot])
                        self.shotMgr.enterShot(shot)
                    elif mode >= 0: 
                        self.shotMgr.vehicle.mode = VehicleMode(mavutil.mode_mapping_acm.get(mode))
                        logger.log("[button]: Requested a mode change via Artoo button to %s." % (modes.MODE_NAMES[mode]))

            # check while on release to avoid issues with entering Rewind
            if event == btn_msg.Release and button == btn_msg.ButtonLoiter:
                self.shotMgr.notifyPause() #trigger brake if not in Loiter

        else:
            if button == btn_msg.ButtonFly and event == btn_msg.Press:
                self.shotMgr.enterShot(shots.APP_SHOT_NONE)
                logger.log("[button]: Exited shot via Artoo Fly button.")
            else:
                self.shotMgr.curController.handleButton(button, event)

        
        if button == btn_msg.ButtonRTL:
            if self.shotMgr.currentShot == shots.APP_SHOT_RTL:
                self.shotMgr.curController.handleButton(button, event)
            elif event == btn_msg.Press:
                self.shotMgr.enterShot(shots.APP_SHOT_RTL)

        if button == btn_msg.ButtonCameraClick and event == btn_msg.Press:
            self.shotMgr.goproManager.handleRecordCommand(self.shotMgr.goproManager.captureMode, RECORD_COMMAND_TOGGLE)

        if event == btn_msg.LongHold and button == btn_msg.ButtonLoiter:
            self.shotMgr.enterShot(shots.APP_SHOT_REWIND)
            # we are holding Pause - dont simply RTL at the end of the rewind spline
            if self.shotMgr.currentShot is shots.APP_SHOT_REWIND:
                self.shotMgr.curController.exitToRTL = False


