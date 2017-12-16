'''
buttonManager.py

This file handles incoming buttons from Artoo as well as assigning/reporting
button assignments to/from the mobile apps. Extended button functions for
Open Solo are handled in extFunctions.py, which is called from the end of this
file as applicable.

BUTTON ENUMERATIONS AND USAGE:
    ButtonPower = 0     Not used here. On Artoo only.
    ButtonFly = 1       Exits smart shots. All other functions on Artoo only
    ButtonRTL = 2       Not used here. On Artoo only.
    ButtonLoiter = 3    Pause in smart shots. All other functions on Artoo only
    ButtonA = 4         Normal use here, added use in Open Solo extFunctions
    ButtonB = 5         Normal use here, added use in Open Solo extFunctions
    ButtonPreset1 = 6   Not used here. Added use in Open Solo extFunctions
    ButtonPreset2 = 7   Not used here. Added use in Open Solo extFunctions
    ButtonCameraClick = 8   Normal use here, Added use in Open Solo extFunctions


EVENT ENUMERATIONS AND USAGE:
    Press =  0          Not used in Open Solo anymore. Still used in stock solo
    Release = 1         Not used in Open Solo anymore. Still used in stock solo
    ClickRelease = 2    Normal single button click (< 0.5 seconds)
    Hold = 3            Not used
    ShortHold = 4       Not used
    LongHold = 5        3 second button hold
    DoubleClick = 6     Not used
    HoldRelease = 7     2 second hold and let go
    LongHoldRelease =8  Not used. Just use LongHold since it's more intuitive.

'''
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
import modes
import settings
import shots
import shotLogger
import shots
from pymavlink import mavutil
from dronekit import VehicleMode
from sololink import btn_msg
from GoProConstants import *
sys.path.append(os.path.realpath(''))

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
            logger.log("[button]: Button A - shot %s, mode %s" % (shots.SHOT_NAMES[self.freeButtonMappings[0][0]], modes.MODE_NAMES[self.freeButtonMappings[0][1]]))
            logger.log("[button]: Button B - shot %s, mode %s" % (shots.SHOT_NAMES[self.freeButtonMappings[1][0]], modes.MODE_NAMES[self.freeButtonMappings[1][1]]))

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
                    logger.log("[button]: sending %s to Artoo as mode" % (modes.MODE_NAMES[mode].upper()))
                else:
                    btn_msg.sendShotString(self.client, shots.SHOT_NAMES[shot].upper())
                    logger.log("[button]: sending %s to Artoo as shot" % (shots.SHOT_NAMES[shot].upper()))
            except:
                logger.log("[button]: %s" % e)
                self.disconnect()

    def getFreeButtonMapping(self, button):
        # our index is 0 -> Button A, 1 -> Button B
        index = button - btn_msg.ButtonA

        if index < 0 or index > 1:
            logger.log("[button]: Error, someone requested a button mapping for button %d"% (button))
            return (-1, -1)

        return self.freeButtonMappings[index]

    # update one of our free button mappings
    def setFreeButtonMapping(self, button, shot, APMmode):
        # our index is 0 -> Button A, 1 -> Button B
        index = button - btn_msg.ButtonA

        if index < 0 or index > 1:
            logger.log("[button]: Error, someone tried to map button %d" % (button))
            return

        if APMmode not in modes.MODE_NAMES.keys():
            logger.log("[button]: Error, someone tried to map an invalid mode %d" % (APMmode))
            return

        if shot not in shots.SHOT_NAMES.keys():
            logger.log("[button]: Error, someone tried to map an invalid shot %d" % (shot))
            return

        self.freeButtonMappings[index] = (shot, APMmode)
        self.setButtonMappings()

        buttonName = "A" if button == btn_msg.ButtonA else "B"
        value = "%d, %d"% (shot, APMmode)
        settings.writeSetting(buttonName, value)

    def isButtonConnected(self):
        return self.connected

    def isButtonInited(self):
        return self.buttonsInitialized

    def handleButtons(self, buttonEvent):

        if buttonEvent is None:
            return

        button, event = buttonEvent

        '''
        Press, DoubleClick, ShortHold, Hold, and Release events are not used any
        further in Open Solo. We dump those events here and now so they don't
        clog up the rest of the button handling. Most aren't even sent from
        Artoo anymore, but just in case someone uses a controller with stock
        firmware, we need to dump these events.
        '''
        if (event == btn_msg.Press or event == btn_msg.DoubleClick
           or event == btn_msg.ShortHold or event == btn_msg.Hold
           or event == btn_msg.Release):
            return

        logger.log("[button]: Received button %r event %r" % (button, event))

        '''POWER BUTTON
        The power button is handled entirely by the Artoo STM32. It's only
        purpose here in shotmanager is logging.
        '''
        if button == btn_msg.ButtonPower:
            if event == btn_msg.LongHold:
                logger.log("[Button]: Controller power button held long.")
            return

        '''FLY BUTTON
        The fly button directly initiates a mode change to Fly (loiter) from
        artoo on a single press. And directly initiates takeoff/land mode from
        artoo on a long hold. It's only purpose here in shotmanager is logging
        and to cleanly exit any smart shot that happens to be running.
        '''
        if button == btn_msg.ButtonFly:
            if event == btn_msg.ClickRelease:
                logger.log("[Button]: Fly button pressed.")
                if self.shotMgr.currentShot != shots.APP_SHOT_NONE:
                    self.shotMgr.enterShot(shots.APP_SHOT_NONE)
            elif event == btn_msg.LongHold:
                logger.log("[Button]: Fly button long hold.")
            return

        '''HOME BUTTON
        The home button is handled entirely by the Artoo STM32. It will directly
        initiate a mode change to RTL if GPS available, or land mode is no GPS
        available when pressed. Its only purpose here in shotmanager is logging.
        '''
        if button == btn_msg.ButtonRTL:
            if event == btn_msg.ClickRelease:
                logger.log("[Button]: Home button pressed.")
            return

        '''PAUSE BUTTON
        The pause button is handled in both the Artoo STM32 and here in
        shotmanager. It serves multiple purposes.

        On ClickRease:
            The STM32 will send mavlink command MAV_CMD_SOLO_BTN_PAUSE_CLICK to
            ArduCopter. ArduCopter will handle what to do with it as follows:
              - If not in Guided Mode, ArduCopter will brake then go into
                fly (loiter) mode. If no GPS, it will go into manual (alt hold).
              - If in Guided Mode, ArduCopter will ignore it, assuming
                we're in a smart shot.
            Here in shot manager, if a smart shot is running, the pause button
            single click is sent to the shot for handling.

        On HoldRelease (2 second hold), The Artoo STM32 will set RC CH7
        to low (1000). On LongHold, the Artoo STM32 will set RC CH7 to
        high (2000). You can set the CH7 on/off options in a GCS like Mission
        Planner, Tower, QGC, etc.

        No other functions should be assigned to the pause button here
        or in extFunctions.
        '''
        if button == btn_msg.ButtonLoiter:
            if event == btn_msg.ClickRelease:
                if self.shotMgr.currentShot != shots.APP_SHOT_NONE:
                    self.shotMgr.curController.handleButton(button, event)
            return

        '''
        The upper and lower camera preset ClickRelease & HoldRelease events are
        managed completely on Artoo. These button events should not be given any
        other usage here because it will hose the Artoo handling.
        The HoldRelease and LongHold events will be sent to extFunctions for
        further handling.
        '''
        if button == btn_msg.ButtonPreset1 or button == btn_msg.ButtonPreset2:
            if event == btn_msg.ClickRelease or event == btn_msg.HoldRelease:
                return
            elif event == btn_msg.HoldRelease or event == btn_msg.LongHold:
                self.shotMgr.extFunctions.handleExtButtons(buttonEvent)
            return

        ''' A BUTTON & B BUTTON
        The ClickRelease events of A & B are managed exclusively here in
        shotmanager. These button events will be processed just as they always
        were with flight modes or smart shots assigned from the apps. They will
        also be sent to any active smart shot for their re-mapped handling.
        The HoldRelease and LongHold events will be sent to extFunctions for
        further handling.
        '''
        if button == btn_msg.ButtonA or button == btn_msg.ButtonB:
            if event == btn_msg.ClickRelease:
                if self.shotMgr.currentShot == shots.APP_SHOT_NONE:
                    (shot, mode) = self.getFreeButtonMapping(button)
                    if shot in shots.CAN_START_FROM_ARTOO:
                        logger.log("[button]: Trying shot via Artoo button: %s" % shots.SHOT_NAMES[shot])
                        self.shotMgr.enterShot(shot)
                    elif mode >= 0:
                        logger.log("[button]: Requested a mode change via Artoo button to %s." % (modes.MODE_NAMES[mode]))
                        self.shotMgr.vehicle.mode = VehicleMode(mavutil.mode_mapping_acm.get(mode))
                else:
                    self.shotMgr.curController.handleButton(button, event)
                    logger.log("[button]: A/B Button ClickRelease sent to smart shot.")
            elif event == btn_msg.HoldRelease or event == btn_msg.LongHold:
                self.shotMgr.extFunctions.handleExtButtons(buttonEvent)
            return

        '''CAMERA TRIGGER BUTTON
        The camera trigger button is handled entirely here in shotmanager.
        The ClickRelease event triggers the camera shutter / record just as
        it always has. The HoldRelease and LongHold events will be sent to
        extFunctions for further handling.
        '''
        if button == btn_msg.ButtonCameraClick:
            if event == btn_msg.ClickRelease:
                self.shotMgr.goproManager.handleRecordCommand(self.shotMgr.goproManager.captureMode, RECORD_COMMAND_TOGGLE)
            elif event == btn_msg.HoldRelease or event == btn_msg.LongHold:
                self.shotMgr.extFunctions.handleExtButtons(buttonEvent)
            return
        return
