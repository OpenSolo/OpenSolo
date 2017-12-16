#
#  pano.py
#  shotmanager
#
#  The pano smart shot controller.
#  Runs as a DroneKit-Python script under MAVProxy.
#
#  Created by Jason Short and Will Silva on 11/30/2015.
#  Copyright (c) 2016 3D Robotics.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


from dronekit import Vehicle, LocationGlobalRelative, VehicleMode

from pymavlink import mavutil
import os
from os import sys, path
import math
import struct

sys.path.append(os.path.realpath(''))
import app_packet
import camera
import location_helpers
import shotLogger
import shots
from shotManagerConstants import *
import GoProManager
from GoProConstants import *
from sololink import btn_msg


# in degrees per second
YAW_SPEED = 10.0

# Cylinder Pano constants
CYLINDER_LENS_ANGLE = 160.0
PANO_CAPTURE_DELAY = int(UPDATE_RATE * 2.5)
PANO_MOVE_DELAY = int(UPDATE_RATE * 3.5)

PANO_YAW_SPEED = 60.0 # deg/s
PANO_PITCH_SPEED = 60.0 # deg/s

PANO_DEFAULT_VIDEO_YAW_RATE = 2.0
PANO_DEFAULT_FOV = 220

MAX_YAW_RATE = 60  # deg/s
MAX_YAW_ACCEL_PER_TICK = (MAX_YAW_RATE) / (4 * UPDATE_RATE)  # deg/s^2/tick

# modes for Pano
PANO_CYLINDER = 0
PANO_SPHERE = 1
PANO_VIDEO = 2

PANO_SETUP = 0
PANO_RUN = 1
PANO_EXIT = 2

VIDEO_COUNTER = 15

TICKS_TO_BEGIN = -25


logger = shotLogger.logger

class PanoShot():

    def __init__(self, vehicle, shotmgr):
        # assign the vehicle object
        self.vehicle = vehicle

        # assign the shotManager object
        self.shotmgr = shotmgr

        # ticks to track timing in shot
        self.ticks = 0

        #state machine
        self.state = PANO_SETUP

        # Default panoType to None
        self.panoType = PANO_CYLINDER

        # steps to track incrementing in shot
        self.step = 0
        self.stepsTotal = 0

        # Yaw rate for Video Pano shot
        self.degSecondYaw = PANO_DEFAULT_VIDEO_YAW_RATE

        # default FOV for Cylinder Pano shot
        self.cylinder_fov = PANO_DEFAULT_FOV
        self.lensFOV = CYLINDER_LENS_ANGLE

        # list of angles in Cylinder Pano shot
        self.cylinderAngles = None
        self.sphereAngles = None

        # default camPitch
        self.camPitch = camera.getPitch(self.vehicle)

        # default camYaw to current pointing
        self.camYaw = camera.getYaw(self.vehicle)

        # only used for non-gimbaled copters
        self.camDir = 1
        self.counter = 0

        # set button mappings on Artoo
        self.setButtonMappings()

        # switch vehicle into GUIDED mode
        self.vehicle.mode = VehicleMode("GUIDED")

        # switch gimbal into MAVLINK TARGETING mode
        self.setupTargeting()
        
        # give the app our defaults
        self.updateAppOptions()
        
        # take over RC
        self.shotmgr.rcMgr.enableRemapping( True )


    # channels are expected to be floating point values in the (-1.0, 1.0)
    # range
    def handleRCs(self, channels):
        if self.panoType == PANO_VIDEO:
            self.runVideo(channels)
            self.manualPitch(channels)
            self.handlePitchYaw()
            
        else:
            if self.state == PANO_SETUP:
                self.manualPitch(channels)
                self.manualYaw(channels[YAW])
                self.handlePitchYaw()
            else:
                if self.panoType == PANO_SPHERE:
                    self.runSphere()
                    self.handlePitchYaw()

                elif self.panoType == PANO_CYLINDER:
                    self.runCylinder()
                    self.handlePitchYaw()


    def initPano(self):
        # We reset to the beginning for all states
        if self.panoType == PANO_SPHERE:
            logger.log("[PANO]: Init Sphere")
            self.enterPhotoMode()
            self.initSphere()

        elif self.panoType == PANO_CYLINDER:
            logger.log("[PANO]: Init Cylinder")
            self.enterPhotoMode()
            self.initCylinder()
        else:
            logger.log("[PANO]: Init Video Pan")


    def resetPano(self):
        self.cylinderAngles = None
        self.sphereAngles = None


    def initSphere(self):
        '''Initialize the cylinder pano shot'''

        # give first move some room to get there
        self.ticks = TICKS_TO_BEGIN

        # Store angle presets in array
        # more steps
        if self.lensFOV < 140:
            self.sphereAngles = [[-90,0], [-45,300], [-45,240], [-45,180], [-45,120], [-45,60], [-45,0], [0,315], [0,270], [0,225], [0,180], [0,135], [0,90], [0,45], [0,0]]
        else:
            # Fewer steps
            self.sphereAngles = [[-90,0], [-45,270], [-45,180], [-45,90], [-45,0], [0,300], [0,240], [0,180], [0,120], [0,60], [0,0]]

        self.stepsTotal = len(self.sphereAngles)
        self.updatePanoStatus(0, self.stepsTotal)

        # go to first angle
        tmp = self.sphereAngles.pop()
        self.camPitch = tmp[0]
        self.camYaw = tmp[1]
        


    def runSphere(self):
        '''Run the Hemi pano program'''
        self.ticks += 1
        if self.sphereAngles is None:
            self.initPano()

        if self.state == PANO_RUN:
            # time delay between camera moves
            if self.ticks == PANO_CAPTURE_DELAY:
                self.shotmgr.goproManager.handleRecordCommand(self.shotmgr.goproManager.captureMode, RECORD_COMMAND_TOGGLE)
                self.updatePanoStatus((self.stepsTotal) - len(self.sphereAngles), self.stepsTotal)

            if self.ticks > PANO_MOVE_DELAY:
                self.ticks = 0

                if len(self.sphereAngles) == 0:
                    self.state = PANO_EXIT
                    # grab a last photo?
                else:
                    # select new angle
                    tmp = self.sphereAngles.pop()
                    self.camPitch = tmp[0]
                    self.camYaw = tmp[1]

        elif self.state == PANO_EXIT:
            self.camPitch = -10

            logger.log("[PANO]: completed Hemi")
            # let user take a new Pano
            self.state = PANO_SETUP
            self.resetPano()
            self.updateAppOptions()
            self.setButtonMappings()


    def initCylinder(self):
        '''Initialize the cylinder pano shot'''
        # limit the inputed FOV from App
        self.cylinder_fov = max(self.cylinder_fov, 91.0)
        self.cylinder_fov = min(self.cylinder_fov, 360.0)

        self.yaw_total = self.cylinder_fov - (self.lensFOV/4)
        steps = math.ceil(self.cylinder_fov / (self.lensFOV/4))
        num_photos = math.ceil(self.cylinder_fov / (self.lensFOV/4))
        yawDelta = self.yaw_total / (num_photos - 1)

        self.origYaw = camera.getYaw(self.vehicle)
        yawStart = self.origYaw - (self.yaw_total / 2.0)

        self.cylinderAngles = []
        
        for x in range(0, int(steps)):
            tmp = yawStart + (x * yawDelta)
            if tmp < 0:
                tmp += 360
            elif tmp > 360:
                tmp -= 360
            self.cylinderAngles.append(int(tmp))

        self.stepsTotal = len(self.cylinderAngles)

        # go to first angle
        self.camYaw = self.cylinderAngles.pop()
        
        # give first move an extra second to get there
        self.ticks = TICKS_TO_BEGIN
        self.updatePanoStatus(0, self.stepsTotal)


    def runCylinder(self):
        '''Run the Cylinder pano program'''
        self.ticks += 1

        if self.cylinderAngles is None:
            self.initPano()

        if self.state == PANO_RUN:
            # time delay between camera moves
            if self.ticks == PANO_CAPTURE_DELAY:
                self.shotmgr.goproManager.handleRecordCommand(self.shotmgr.goproManager.captureMode, RECORD_COMMAND_TOGGLE)
                self.updatePanoStatus((self.stepsTotal) - len(self.cylinderAngles), self.stepsTotal)

            if self.ticks > PANO_MOVE_DELAY:
                self.ticks = 0

                if len(self.cylinderAngles) == 0:
                    self.state = PANO_EXIT
                else:
                    # select new angle
                    self.camYaw = self.cylinderAngles.pop()

        elif self.state == PANO_EXIT:
            self.camYaw = self.origYaw
            # let user take a new Pano
            self.state = PANO_SETUP
            self.resetPano()
            self.updateAppOptions()
            self.setButtonMappings()


    def runVideo(self, channels):
        '''Run the Video pano program'''
        # modulate yaw rate based on yaw stick input
        if channels[YAW] != 0:
            self.degSecondYaw = self.degSecondYaw + (channels[YAW] * MAX_YAW_ACCEL_PER_TICK)

        # limit yaw rate
        self.degSecondYaw = min(self.degSecondYaw,  MAX_YAW_RATE)
        self.degSecondYaw = max(self.degSecondYaw, -MAX_YAW_RATE)

        # increment desired yaw angle
        self.camYaw += (self.degSecondYaw * UPDATE_TIME)
        self.camYaw %= 360.0
        #logger.log("[PANO]: self.camYaw %f" % self.camYaw)

        self.counter += 1
        if self.counter > VIDEO_COUNTER:
            self.counter = 0
            self.updateAppOptions()
            

    # send our current set of options to the app
    def updateAppOptions(self):
        # B = uint_8 
        # h = int_16
        # f = float_32
        # d = float_64
        packet = struct.pack('<IIBBhff', app_packet.SOLO_PANO_OPTIONS, 12, self.panoType, self.state, self.cylinder_fov, self.degSecondYaw, self.lensFOV)
        self.shotmgr.appMgr.sendPacket(packet)


    def updatePanoStatus(self, _index, _total):
        #logger.log("[Pano]: steps %d of %d" % (_index, _total))
        packet = struct.pack('<IIBB', app_packet.SOLO_PANO_STATE, 2, _index, _total)
        self.shotmgr.appMgr.sendPacket(packet)

    
    def handlePacket(self, packetType, packetLength, packetValue):
        try:
            if packetType == app_packet.SOLO_PANO_OPTIONS:
                (self.panoType, _run, self.cylinder_fov, self.degSecondYaw, self.lensFOV) = struct.unpack('<BBhff', packetValue)
                logger.log("[PANO]: panoType %d" % self.panoType)
                logger.log("[PANO]: state %d" % _run)
                logger.log("[PANO]: cylinder_fov %d" % self.cylinder_fov)
                logger.log("[PANO]: video degSecondYaw %f" % self.degSecondYaw)
                logger.log("[PANO]: lens fov %f" % self.lensFOV)
                
                # range limit lens
                self.lensFOV = max(self.lensFOV, 60)
                self.lensFOV = min(self.lensFOV, 180)
                                
                # tell main loop to run Pano
                if _run == PANO_RUN:
                    self.state = PANO_RUN
                else:
                    self.resetPano()
                    self.state = PANO_SETUP

                self.setButtonMappings()
            else:
                return False

        except Exception as e:
            logger.log('[PANO]: Error handling packet. (%s)' % e)
            return False
        else:
            return True


    def setButtonMappings(self):
        buttonMgr = self.shotmgr.buttonManager

        if self.panoType == PANO_VIDEO:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_PANO, 0, "\0")
        else:        
            if self.state == PANO_RUN:
                buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_PANO, btn_msg.ARTOO_BITMASK_ENABLED, "Cancel\0")
            else:
                buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_PANO, btn_msg.ARTOO_BITMASK_ENABLED, "Begin\0")

        if self.state == PANO_SETUP:
            if self.panoType == PANO_VIDEO:
                buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_PANO, btn_msg.ARTOO_BITMASK_ENABLED, "Video\0")
            elif self.panoType == PANO_SPHERE:
                buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_PANO, btn_msg.ARTOO_BITMASK_ENABLED, "Sphere\0")
            elif self.panoType == PANO_CYLINDER:
                buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_PANO, btn_msg.ARTOO_BITMASK_ENABLED, "Cylinder\0")
        else:
            buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_PANO, 0, "\0")


    # if we can handle the button we do
    def handleButton(self, button, event):
        if button == btn_msg.ButtonA and event == btn_msg.ClickRelease:
            # don't use A button for video ever
            if self.panoType != PANO_VIDEO:
                if self.state == PANO_SETUP:
                    self.state = PANO_RUN
                else:
                    # enter standby
                    self.resetPano()
                    self.state = PANO_SETUP
                    logger.log("[PANO]: Cancel Pano")
                    # if we are in video mode, stop Yawing
                    if self.panoType == PANO_VIDEO:
                        self.degSecondYaw = 0
            self.setButtonMappings()

                
        if button == btn_msg.ButtonLoiter and event == btn_msg.ClickRelease:
            if self.panoType == PANO_VIDEO:
                self.degSecondYaw = 0

        # cycle through options
        if self.state == PANO_SETUP and button == btn_msg.ButtonB and event == btn_msg.ClickRelease:
            #clear Pano Video yaw speed
            self.degSecondYaw = 0
            if self.panoType == PANO_VIDEO:
                self.panoType = PANO_SPHERE
            elif self.panoType == PANO_SPHERE:
                self.panoType = PANO_CYLINDER
            elif self.panoType == PANO_CYLINDER:
                self.panoType = PANO_VIDEO
            self.setButtonMappings()

        # tell the app what's happening
        self.updateAppOptions()


    def setupTargeting(self):
        # set gimbal targeting mode
        msg = self.vehicle.message_factory.mount_configure_encode(
                    0, 1,    # target system, target component
                    mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,  #mount_mode
                    1,  # stabilize roll
                    1,  # stabilize pitch
                    1,  # stabilize yaw
                    )
        self.vehicle.send_mavlink(msg)

    def manualPitch(self, channels):
        if abs(channels[THROTTLE]) > abs(channels[RAW_PADDLE]):
            value = channels[THROTTLE]
        else:
            value = channels[RAW_PADDLE]

        self.camPitch += value * PANO_PITCH_SPEED * UPDATE_TIME
        
        if self.camPitch > 0.0:
            self.camPitch = 0.0
        elif self.camPitch < -90:
            self.camPitch = -90
 
 
    def manualYaw(self, stick):
        if stick == 0:
            return
        self.camYaw += stick * PANO_YAW_SPEED * UPDATE_TIME
        if stick > 0:
            self.camDir = 1
        else:
            self.camDir = -1
        
        self.camYaw = location_helpers.wrapTo360(self.camYaw)


    def handlePitchYaw(self):
        '''Send pitch and yaw commands to gimbal or fixed mount'''
        # if we do have a gimbal, use mount_control to set pitch and yaw
        if self.vehicle.mount_status[0] is not None:
            msg = self.vehicle.message_factory.mount_control_encode(
                    0, 1,    # target system, target component
                    # pitch is in centidegrees
                    self.camPitch * 100,
                    0.0, # roll
                    # yaw is in centidegrees
                    0, # self.camYaw * 100, (Disabled by Matt for now due to ArduCopter master mount_control bug. Using condition_yaw instead)
                    0 # save position
            )
            self.vehicle.send_mavlink(msg)
            
            msg = self.vehicle.message_factory.command_long_encode( # Using condition_yaw temporarily until mount_control yaw issue is fixed
                    0, 0,    # target system, target component
                    mavutil.mavlink.MAV_CMD_CONDITION_YAW, #command
                    0, #confirmation
                    self.camYaw,  # param 1 - target angle
                    YAW_SPEED, # param 2 - yaw speed
                    self.camDir, # param 3 - direction
                    0.0, # relative offset
                    0, 0, 0 # params 5-7 (unused)
            )
            self.vehicle.send_mavlink(msg)
                        
        else:
            # if we don't have a gimbal, just set CONDITION_YAW
            msg = self.vehicle.message_factory.command_long_encode(
                    0, 0,    # target system, target component
                    mavutil.mavlink.MAV_CMD_CONDITION_YAW, #command
                    0, #confirmation
                    self.camYaw,  # param 1 - target angle
                    YAW_SPEED, # param 2 - yaw speed
                    self.camDir, # param 3 - direction
                    0.0, # relative offset
                    0, 0, 0 # params 5-7 (unused)
            )
            self.vehicle.send_mavlink(msg)

    def enterPhotoMode(self):
        # switch into photo mode if we aren't already in it
        self.shotmgr.goproManager.sendGoProCommand(mavutil.mavlink.GOPRO_COMMAND_CAPTURE_MODE, (CAPTURE_MODE_PHOTO, 0 ,0 , 0))

