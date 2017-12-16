#
# This is the entry point for shotmanager on Solo using Dronekit-Python


# Python native imports
import os
from os import sys, path
import select
import struct
import time
import traceback

# Dronekit/Mavlink imports
from dronekit.lib import VehicleMode
from pymavlink import mavutil

sys.path.append(path.realpath(''))

# Managers imports
import buttonManager
import appManager
import rcManager
from GoProConstants import *
import GoProManager
import rewindManager
import GeoFenceManager
import extFunctions

# Loggers imports
import shotLogger

# Constants imports
from shotManagerConstants import *

# Shotmanager imports
from shotFactory import ShotFactory
import app_packet
import shots
import modes
import monotonic
from location_helpers import rad2deg, wrapTo360, wrapTo180

try:
    from shotManager_version import VERSION
except ImportError:
    VERSION = "[shot]: Unknown Shotmanager version"

logger = shotLogger.logger

WPNAV_ACCEL_DEFAULT = 200
ATC_ACCEL_DEFAULT = 36000


class ShotManager():
    def __init__(self):
        # see the shotlist in app/shots/shots.py
        self.currentShot = shots.APP_SHOT_NONE
        self.currentModeIndex = DEFAULT_APM_MODE
        self.curController = None

    def Start(self, vehicle):
        logger.log("+-+-+-+-+-+-+ Starting up %s +-+-+-+-+-+-+" % VERSION)

        ### initialize dronekit vehicle ###
        self.vehicle = vehicle

        ### switch vehicle to loiter mode ###
        self.vehicle.mode = VehicleMode("LOITER")

        ### initialize rc manager ###
        self.rcMgr = rcManager.rcManager(self)

        ### initialize app manager ###
        self.appMgr = appManager.appManager(self)

        ### initialize button manager ###
        self.buttonManager = buttonManager.buttonManager(self)
        
        ### initialize extended functions ###
        self.extFunctions = extFunctions.extFunctions(self.vehicle,self)

        ### initialize gopro manager ###
        self.goproManager = GoProManager.GoProManager(self)

        ### Initialize GeoFence manager ###
        self.geoFenceManager = GeoFenceManager.GeoFenceManager(self)

        # instantiate rewindManager
        self.rewindManager = rewindManager.RewindManager(self.vehicle, self)

        ### init APM stream rates ###
        self.initStreamRates()

		### register callbacks ###
        self.registerCallbacks()
        
        # Try to maintain a constant tick rate
        self.timeOfLastTick = monotonic.monotonic()
        # how many ticks have we performed since an RC update?

        # register all connections (gopro manager communicates via appMgr's socket)
        self.inputs = [self.rcMgr.server, self.appMgr.server]
        self.outputs = []

		#check if gimbal is present
        if self.vehicle.gimbal.yaw is not None:
	        logger.log("[shot]: Gimbal detected.")
	        # Initialize gimbal to RC targeting
	        self.vehicle.gimbal.release()
        else:
            logger.log("[shot]: No gimbal detected.")

        # mark first tick time
        self.timeOfLastTick = monotonic.monotonic()

        # check for In-Air start from Shotmanager crash
        if self.vehicle.system_status == 'ACTIVE':
            logger.log("[shot]: Restart in air.")
            # load vehicle home    
            self.rewindManager.loadHomeLocation()
            # not yet enabled until this check proves effective
            #self.vehicle.mode = VehicleMode("RTL")

    def Run(self):
        while True:
            try:
                #print "in shotManager server loop"
                # handle TCP/RC packets
                # we set a timeout of UPDATE_TIME, so we roughly do this every UPDATE_TIME
                rl, wl, el = select.select( self.inputs, self.outputs, [], UPDATE_TIME )

                # handle reads
                for s in rl:
                    if s is self.appMgr.server: # if read is a connection attempt
                        self.appMgr.connectClient()

                    elif s is self.appMgr.client: # if read is from app
                        self.appMgr.parse()

                    elif s is self.rcMgr.server: # if read is an RC packet
                        self.rcMgr.parse()

                    elif s is self.buttonManager.client: # if read is from buttons
                        self.buttonManager.parse()

                # now handle writes (sololink.btn_msg handles all button writes)
                for s in wl:
                    if s is self.appMgr.client: # if write is for app
                        self.appMgr.write()

                # exceptions
                for s in el:
                    if s is self.appMgr.client: # if its the app socket throwing an exception
                        self.appMgr.exception()
                    else:
                        # otherwise remove whichever socket is excepting
                        if s in self.inputs:
                            self.inputs.remove(s)
                        if s in self.outputs:
                            self.outputs.remove(s)
                        s.close()

                self.buttonManager.checkButtonConnection()

                # Check if copter is outside fence or will be
                self.geoFenceManager.activateGeoFenceIfNecessary()

                # call main control/planning loop at UPDATE_RATE
                if time.time() - self.timeOfLastTick > UPDATE_TIME:
                    self.Tick()

            except Exception as ex:
                # reset any RC timeouts and stop any stick remapping
                self.rcMgr.detach()

                # try to put vehicle into LOITER
                self.vehicle.mode = VehicleMode("LOITER")

                exceptStr = traceback.format_exc()

                print exceptStr
                strlist = exceptStr.split('\n')

                for i in strlist:
                    logger.log(i)

                if self.appMgr.isAppConnected():
                    # send error to app
                    packet = struct.pack('<II%ds' % (len(exceptStr)), app_packet.SOLO_MESSAGE_SHOTMANAGER_ERROR, len(exceptStr), exceptStr)

                    self.appMgr.client.send(packet)
                    # sleep to make sure the packet goes out (for some reason
                    # setting client.setblocking(1) doesn't work)
                    time.sleep(0.4)

                # cleanup
                for socket in self.inputs:
                     socket.close()

                os._exit(1)

    def enterShot(self, shot):
        
        if shot not in shots.SHOT_NAMES:
            logger.log("[shot]: Shot not recognized. (%d)" % shot)
            return

        if shot == shots.APP_SHOT_NONE:
            pass

        # check our EKF - if it's bad and that we can't init the shot prior to EKF being OK, reject shot entry attempt
        elif self.last_ekf_ok is False and shot not in shots.CAN_START_BEFORE_EKF:

            logger.log('[shot]: Vehicle EKF quality is poor, shot entry into %s disallowed.' % shots.SHOT_NAMES[shot])

            # set shot to APP_SHOT_NONE
            shot = shots.APP_SHOT_NONE

            # notify the app of shot entry failure
            packet = struct.pack('<III', app_packet.SOLO_SHOT_ERROR, 4, app_packet.SHOT_ERROR_BAD_EKF)
            self.appMgr.sendPacket(packet)

        # check vehicle system status - if it's CRITICAL or EMERGENCY, reject shot entry attempt
        elif self.vehicle.system_status in ['CRITICAL', 'EMERGENCY']:

            logger.log('[shot]: Vehicle in %s, shot entry into %s disallowed.' % (self.vehicle.system_status, shots.SHOT_NAMES[shot]))

            # set shot to APP_SHOT_NONE
            shot = shots.APP_SHOT_NONE

            # notify the app of shot entry failure
            packet = struct.pack('<III', app_packet.SOLO_SHOT_ERROR, 4, app_packet.SHOT_ERROR_RTL)
            self.appMgr.sendPacket(packet)

        # check if vehicle is not armed or in STANDBY and that we can't init the shot prior to arm, reject shot entry attempt
        elif (self.vehicle.armed is False or self.vehicle.system_status == 'STANDBY') and shot not in shots.CAN_START_BEFORE_ARMING:

            logger.log('[shot]: Vehicle is unarmed, shot entry into %s disallowed.' % shots.SHOT_NAMES[shot])
            self.vehicle.mode = VehicleMode("LOITER")

            # set shot to APP_SHOT_NONE
            shot = shots.APP_SHOT_NONE

            # notify the app of shot entry failure
            packet = struct.pack('<III', app_packet.SOLO_SHOT_ERROR, 4, app_packet.SHOT_ERROR_UNARMED)
            self.appMgr.sendPacket(packet)

        #OK fine, you get to start the shot.
        if self.currentShot != shot:

            logger.log('[shot]: Entering shot %s.' % shots.SHOT_NAMES[shot])

            if self.currentShot == shots.APP_SHOT_REWIND:
                # we are exiting Rewind
                self.rewindManager.resetSpline()
            
            # APP_SHOT_NONE
            if shot == shots.APP_SHOT_NONE:

                # mark curController for garbage collection
                del self.curController

                # set curController to None (should also mark for garbage collection)
                self.curController = None

                # re-enable manual gimbal controls (RC Targeting mode)
                self.vehicle.gimbal.release()

                # disable the stick re-mapper
                self.rcMgr.enableRemapping( False )

                # if vehicle mode is in GUIDED or AUTO, then switch to LOITER
                if self.vehicle.mode.name in shots.SHOT_MODES:
                    logger.log("[shot]: Changing vehicle mode to FLY.")
                    self.vehicle.mode = VehicleMode("LOITER")
            else:
                self.curController = ShotFactory.get_shot_obj(shot, self.vehicle, self)
                self.setATCaccel(36000)

            # update currentShot
            self.currentShot = shot

            logger.log("[shot]: Successfully entered %s." % shots.SHOT_NAMES[shot])

        # already in that shot
        else:
            logger.log('[shot]: Already in shot %s.' % shots.SHOT_NAMES[shot])

        # let the world know
        if self.appMgr.isAppConnected():
            self.appMgr.broadcastShotToApp(shot)

        # let Artoo know too
        self.buttonManager.setArtooShot(shot)

        # set new button mappings appropriately
        self.buttonManager.setButtonMappings()

    def mode_callback(self, vehicle, name, mode):
        try:
            if mode.name != self.lastMode:
                logger.log("[callback]: Mode changed from %s -> %s"%(self.lastMode, mode.name))

                self.lastMode = mode.name
                
                modeIndex = modes.getAPMModeIndexFromName( mode.name, self.vehicle)
                
                if modeIndex < 0:
                    logger.log("couldn't find this mode index: %s" % self.mode.name)
                    return
                else:
                    self.currentModeIndex = modeIndex
                
                # If changing to Guided, we're probably in a smart shot so no
                # need to do anything here. If not, we need to run all this 
                # cleanup stuff in case the stick and button remapping did not
                # properly clear from the last smart shot.

                if mode.name == 'GUIDED':
                    return

                self.setNormalControl(modeIndex, mode)

        except Exception as e:
            logger.log('[shot]: mode callback error, %s' % e)

    def setNormalControl(self, modeIndex, mode):
        # If we were in a smart shot, log that we bailed out out due to a mode change
        if self.currentShot != shots.APP_SHOT_NONE:
            logger.log("[callback]: Detected that we are not in the correct apm mode for this shot. Exiting shot!")
            self.currentShot = shots.APP_SHOT_NONE

        # mark curController for garbage collection
        if self.curController != None:
            del self.curController
            self.curController = None

        # re-enable manual gimbal controls (RC Targeting mode)
        self.vehicle.gimbal.release()

        # disable the stick re-mapper
        self.rcMgr.enableRemapping( False )

        # let the world know
        if self.appMgr.isAppConnected():
            self.appMgr.broadcastShotToApp(shots.APP_SHOT_NONE)         

        # let Artoo know too
        self.buttonManager.setArtooShot(shots.APP_SHOT_NONE, modeIndex)

        # set new button mappings appropriately
        self.buttonManager.setButtonMappings()

    def ekf_callback(self, vehicle, name, ekf_ok):
        try:
            if ekf_ok != self.last_ekf_ok:
                self.last_ekf_ok = ekf_ok
                logger.log("[callback]: EKF status changed to %d" % (ekf_ok))
                self.buttonManager.setButtonMappings()

                # if we regain EKF and are landing - just push us into fly
                if ekf_ok and self.vehicle.mode.name == 'LAND':
                    self.enterShot(shots.APP_SHOT_NONE)
            
            # only store home in the air when no home loc exists
            if self.rewindManager:
                if ekf_ok and self.last_armed and self.rewindManager.homeLocation is None:
                    self.rewindManager.loadHomeLocation()
                
        except Exception as e:
            logger.log('[callback]: ekf callback error, %s' % e)

    def armed_callback(self, vehicle, name, armed):
        try:
            if armed != self.last_armed:
                self.last_armed = armed
                logger.log("[callback]: armed status changed to %d"%(armed))
                self.buttonManager.setButtonMappings()

                # clear Rewind manager cache
                self.rewindManager.resetSpline()

                if not armed and self.currentShot not in shots.CAN_START_BEFORE_ARMING:
                    self.enterShot(shots.APP_SHOT_NONE)
                    self.vehicle.mode = VehicleMode("LOITER")

                # stop recording upon disarm (landing, hopefully)
                if not armed:
                    self.goproManager.handleRecordCommand(self.goproManager.captureMode, RECORD_COMMAND_STOP)

                # read home loc from vehicle
                if armed:
                    self.rewindManager.loadHomeLocation()
                    
        except Exception as e:
            logger.log('[callback]: armed callback error, %s' % e)

    def camera_feedback_callback(self, vehicle, name, msg):
        try:
            if self.currentShot in shots.SITE_SCAN_SHOTS or self.vehicle.mode.name == 'AUTO':
                # issue GoPro record command
                self.goproManager.handleRecordCommand(CAPTURE_MODE_PHOTO, RECORD_COMMAND_START)

        except Exception as e:
            logger.log('[callback]: camera feedback callback error, %s.' % e)

    def initStreamRates(self):
        STREAM_RATES = {
            mavutil.mavlink.MAV_DATA_STREAM_EXTENDED_STATUS: 2,
            mavutil.mavlink.MAV_DATA_STREAM_EXTRA1: 10,
            mavutil.mavlink.MAV_DATA_STREAM_EXTRA2: 10,
            mavutil.mavlink.MAV_DATA_STREAM_EXTRA3: 2,
            mavutil.mavlink.MAV_DATA_STREAM_POSITION: 10,
            mavutil.mavlink.MAV_DATA_STREAM_RAW_SENSORS: 2,
            mavutil.mavlink.MAV_DATA_STREAM_RAW_CONTROLLER: 3,
            mavutil.mavlink.MAV_DATA_STREAM_RC_CHANNELS: 5,
        }

        for stream, rate in STREAM_RATES.items():
            msg = self.vehicle.message_factory.request_data_stream_encode(
                                                            0, 1,    # target system, target component
                                                            stream,        # requested stream id
                                                            rate,    # rate
                                                            1       # start it
                                                            )

            self.vehicle.send_mavlink(msg)

    def notifyPause(self, inShot=0):
        '''No longer used. Pause comes from the controller'''
        return


    # This fetches and returns the value of the parameter matching the given name
    # If the parameter is not found, returns the given default value instead
    def getParam(self, name, default=None):
        self.paramValue = self.vehicle.parameters.get(name, wait_ready=False) or default
        logger.log("[SHOT]: Parameter %s is %d" %(name, self.paramValue))
        return self.paramValue

    # This sets the parameter matching the given name
    def setParam(self, name, value):
        logger.log("[SHOT]: Setting parameter %s to %d" %(name, value))
        return self.vehicle.parameters.set(name, value)

    # Set the ATC_ACCEL_P and ATC_ACCEL_R parameters
    def setATCaccel(self,val):
        self.setParam("ATC_ACCEL_P_MAX",val)
        self.setParam("ATC_ACCEL_R_MAX",val)

    # we call this at our UPDATE_RATE
    # drives the shots as well as anything else timing-dependent
    def Tick(self):
        self.timeOfLastTick = time.time()
        self.rcMgr.rcCheck()

        # update rewind manager        
        if (self.currentShot == shots.APP_SHOT_REWIND or self.currentShot == shots.APP_SHOT_RTL or self.vehicle.mode.name == 'RTL') is False:
            self.rewindManager.updateLocation()


        # Always call remap
        channels = self.rcMgr.remap()            
        
        if self.curController:
            self.curController.handleRCs(channels)
        

    def getHomeLocation(self):
        if self.rewindManager.homeLocation is None or self.rewindManager.homeLocation.lat == 0:
            return None
        else:
            return self.rewindManager.homeLocation


    def enterFailsafe(self):
        ''' called when we loose RC link or have Batt FS event '''

        # Nothing to do here now. ArduCopter handles it.


    def registerCallbacks(self):
        self.last_ekf_ok = False
        self.last_armed = False
        self.lastMode = self.vehicle.mode.name

        # MODE
        self.vehicle.add_attribute_listener('mode', self.mode_callback) #register with vehicle class (dronekit)

        # EKF    
        # call ekf back first
        self.ekf_callback(self.vehicle, 'ekf_ok', self.vehicle.ekf_ok)
        self.vehicle.add_attribute_listener('ekf_ok', self.ekf_callback) #register with vehicle class (dronekit)

        # ARMED
        self.vehicle.add_attribute_listener('armed', self.armed_callback) #register with vehicle class (dronekit)

        # CAMERA FEEDBACK
        self.vehicle.add_message_listener('CAMERA_FEEDBACK', self.camera_feedback_callback) #register with vehicle class (dronekit)

        # gopro manager callbacks (defined in gopro manager)
        self.vehicle.add_attribute_listener('gopro_status', self.goproManager.state_callback)
        self.vehicle.add_attribute_listener('gopro_get_response', self.goproManager.get_response_callback)
        self.vehicle.add_attribute_listener('gopro_set_response', self.goproManager.set_response_callback)