'''
extFunctions.py

This is the extended button function handler for Open Solo.  This allows
controller button events above and beyond the original design to be configured
and utilized. The enumerations and available use here in extFunctions is
detailed below:

BUTTON ENUMERATIONS AND USAGE:
    ButtonPower = 0     Not used here. On Artoo only.
    ButtonFly = 1       Not used here. Artoo and buttonManager.py only.
    ButtonRTL = 2       Not used here. Artoo and buttonManager.py only.
    ButtonLoiter = 3    Not used here. Artoo and buttonManager.py only.
    ButtonA = 4         HoldRelease & LongHold available here
    ButtonB = 5         HoldRelease & LongHold available here
    ButtonPreset1 = 6   LongHold available here
    ButtonPreset2 = 7   LongHold available here
    ButtonCameraClick = 8   HoldRelease & LongHold available here


EVENT ENUMERATIONS AND USAGE:
    Press =  0          Not used in Open Solo.
    Release = 1         Not used in Open Solo.
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

logger = shotLogger.logger

# PWM values used in DO_SET_SERVO commands.
# Change these as desired. Or you can change the individial values
# in the function calls below
SERVO_PWM_LOW = 1000
SERVO_PWM_MID = 1500
SERVO_PWM_HIGH = 2000


class extFunctions():

    def __init__(self, vehicle, shotMgr):
        self.vehicle = vehicle
        self.shotMgr = shotMgr
        self.gimablRetracted = 0
        self.shotSetting = -1
        self.modeSetting = -1
        self.FuncSetting = -1

    def handleExtButtons(self, btnevent):

        if btnevent is None:
            return

        button, event = btnevent

        # form a string in the format of {button},{event}
        lookup = "%r,%r" % (button, event)

        # log the string
        logger.log("[Ext Func]: Reading Button Event %s" % lookup)

        # lookup the setting for {button},{event} in extFunctions.conf
        # returns the enumerations as shot,mode,function as a string
        lookupResult = settings.readSettingExt(lookup)

        # dump it if no result
        if lookupResult == 0:
            return

        # log the found settings string
        logger.log("[Ext Func]: Read %s" % lookupResult)

        # split the result string
        buttonMapping = lookupResult.split(',')

        # set the shot, mode, and function setting vars using the split string
        self.shotSetting = int(buttonMapping[0])
        self.modeSetting = int(buttonMapping[1])
        self.funcSetting = int(buttonMapping[2])

        # if setting is a smart shot, call the specified shot
        # if setting is a flight mode, call mode change function
        if self.shotSetting >= 0 and self.modeSetting == -1:
            self.enterSmartShot(self.shotSetting)
        elif self.shotSetting == -1 and self.modeSetting >= 0:  # Button is assigned a flight mode
            self.changeFlightMode(self.modeSetting)

        # if setting has a function, do that too.
        if self.funcSetting >= 0:  # Button is assigned a function
            #  FUNCTIONS:
            #  -1 = none
            #  1 = Landing gear up
            #  2 = Landing gear down
            #  3 = Gimbal lock toggle
            #  4 = Servo 6 low
            #  5 = Servo 6 med
            #  6 = Servo 6 high
            #  7 = Servo 7 low
            #  8 = Servo 7 med
            #  9 = Servo 7 high
            #  10 = Servo 8 low
            #  11 = Servo 8 med
            #  12 = Servo 8 high
            #  13 = Gripper Close
            #  14 = Gripper Open

            if self.funcSetting == 1:       # landing gear up
                self.landingGear(1)
            elif self.funcSetting == 2:     # landing gear down
                self.landingGear(0)
            elif self.funcSetting == 3:     # gimbal lock toggle
                self.gimbalRetractToggle()
            elif self.funcSetting == 4:     # servo 6 low
                self.setServo(6, SERVO_PWM_LOW)
            elif self.funcSetting == 5:     # servo 6 mid
                self.setServo(6, SERVO_PWM_MID)
            elif self.funcSetting == 6:     # servo 6 high
                self.setServo(6, SERVO_PWM_HIGH)
            elif self.funcSetting == 7:     # servo 7 low
                self.setServo(7, SERVO_PWM_LOW)
            elif self.funcSetting == 8:     # servo 7 mid
                self.setServo(7, SERVO_PWM_MID)
            elif self.funcSetting == 9:     # servo 7 high
                self.setServo(7, SERVO_PWM_HIGH)
            elif self.funcSetting == 10:    # servo 8 low
                self.setServo(8, SERVO_PWM_LOW)
            elif self.funcSetting == 11:    # servo 8 mid
                self.setServo(8, SERVO_PWM_MID)
            elif self.funcSetting == 12:    # servo 8 high
                self.setServo(8, SERVO_PWM_HIGH)
            elif self.funcSetting == 13:    # gripper close
                self.setGripper(0)
            elif self.funcSetting == 13:    # gripper open
                self.setGripper(1)
            else:
                pass

    def enterSmartShot(self, shot):
        if self.shotMgr.currentShot != shots.APP_SHOT_NONE:
            # exit whatever shot we're already in if we're in one.
            self.shotMgr.enterShot(shots.APP_SHOT_NONE)
        if shot in shots.CAN_START_FROM_ARTOO:
            # enter the requested shot
            logger.log("[Ext Func]: Trying shot %s via Artoo extended button" % shots.SHOT_NAMES[shot])
            self.shotMgr.enterShot(shot)

    def changeFlightMode(self, mode):
        # Change flight modes. Exit a smart shot if we're in one.
        if mode >= 0:
            self.shotMgr.vehicle.mode = VehicleMode(mavutil.mode_mapping_acm.get(mode))
            logger.log("[Ext Func]: Requested a mode change via Artoo button to %s." % (modes.MODE_NAMES[mode]))
        else:
            logger.log("[Ext Func]: Invalid mode request. Quit pushing my buttons.")

    def landingGear(self, up_down):
        # Raise or lower landing gear using mavlink command
        # Argument up_down: 0 = down, 1 = up
        if up_down == 0:
            logger.log("[Ext Func] Landing Gear Down")
        elif up_down == 1:
            logger.log("[Ext Func] Landing Gear Up")
        else:
            logger.log("[Ext Func] Landing Gear Command Error. Putting gear down.")
            up_down = 0
        msg = self.vehicle.message_factory.command_long_encode(
             0, 1,           # target system, target component
             mavutil.mavlink.MAV_CMD_AIRFRAME_CONFIGURATION,  # frame
             0,              # confirmation
             -1,             # param 1:-1 = all landing gear
             up_down,        # param 2: 0 = down, 1 = up
             0, 0, 0, 0, 0)  # params 3-7 (not used)
        self.vehicle.send_mavlink(msg)

    def gimbalRetractToggle(self):
        if self.gimablRetracted == 0:
            self.gimablRetracted = 1
            logger.log("[Ext Func] Toggling gimbal to locked")
            # set gimbal mode to locked'''
            msg = self.vehicle.message_factory.command_long_encode(
                 0, 1,     # target system, target component
                 mavutil.mavlink.MAV_CMD_DO_MOUNT_CONTROL,  # frame
                 0,        # confirmation
                 0, 0, 0, 0, 0, 0,  # params 1-6 not used
                 mavutil.mavlink.MAV_MOUNT_MODE_RETRACT)  # param 7 MAV_MOUNT_MODE
            self.vehicle.send_mavlink(msg)
        else:
            self.gimablRetracted = 0
            logger.log("[Ext Func] Toggling gimbal to unlocked")
            # set gimbal mode to normal
            msg = self.vehicle.message_factory.command_long_encode(
                 0, 1,     # target system, target component
                 mavutil.mavlink.MAV_CMD_DO_MOUNT_CONTROL,  # frame
                 0,        # confirmation
                 1, 1, 1,  # parms 1-4 stabilize yes
                 0, 0, 0,  # params 4-6 not used
                 mavutil.mavlink.MAV_MOUNT_MODE_RC_TARGETING)  # param 7 MAV_MOUNT_MODE
            self.vehicle.send_mavlink(msg)


    def setServo(self, ServoNum, PWMval):
        # Set an ArduPilot servo output
        # Argument ServoNum is the ArduPilot servo number
        # Argument PWMval is the PWM value the servo will be set for

        msg = self.vehicle.message_factory.command_long_encode(
             0, 1,           # target system, target component
             mavutil.mavlink.MAV_CMD_DO_SET_SERVO,  # frame
             0,              # confirmation
             ServoNum,       # param 1: Desired servo number
             PWMval,         # param 2: Desired PWM value
             0, 0, 0, 0, 0)  # params 3-7 (not used)
        self.vehicle.send_mavlink(msg)


    def setGripper(self, CloseOpen):
        # Set the ArduPilot gripper
        # Argument CloseOpen is 0 for close and 1 for open

        msg = self.vehicle.message_factory.command_long_encode(
             0, 1,           # target system, target component
             mavutil.mavlink.MAV_CMD_DO_GRIPPER,  # frame
             0,              # confirmation
             1,              # param 1: Gripper # (ArduPilot only supports 1)
             CloseOpen,      # param 2: Open or Close
             0, 0, 0, 0, 0)  # params 3-7 (not used)
        self.vehicle.send_mavlink(msg)

