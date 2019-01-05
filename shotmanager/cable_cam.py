#
# Implement cable cam using DroneAPI
# This is called from shotManager running in MavProxy
# As of Solo version 2.0.0 this shot is no longer supported. It is replaced with multipoint.py.
# It is preserved here for compatibility with old versions of the app.
#
from dronekit.lib import VehicleMode
from dronekit.lib import LocationGlobal
from pymavlink import mavutil
import os
from os import sys, path
import math
import struct

sys.path.append(os.path.realpath(''))
import app_packet
import camera
import location_helpers
import pathHandler
import shotLogger
import shots
from shotManagerConstants import *
import yawPitchOffsetter
# on host systems these files are located here
sys.path.append(os.path.realpath('../../flightcode/stm32'))
from sololink import btn_msg

# in degrees per second
YAW_SPEED = 120.0

# cm / second
DEFAULT_WPNAV_ACCEL_VALUE = 100.0

logger = shotLogger.logger

class Waypoint():
    def __init__(self, loc, yaw, pitch):
        self.loc = loc
        self.yaw = yaw
        self.pitch = pitch
        if self.pitch is None:
            self.pitch = 0.0


class CableCamShot():
    def __init__(self, vehicle, shotmgr):
        self.vehicle = vehicle
        self.shotmgr = shotmgr
        self.waypoints = []
        self.totalDistance = 0.0
        self.yawPitchOffsetter = yawPitchOffsetter.YawPitchOffsetter()
        self.pathHandler = None
        # this is the total yaw between the recording of point 1 and point 2
        self.aggregateYaw = 0.0
        self.lastYaw = 0.0

        # Cable cam options - set from the app
        # cam interpolation is whether to do camera interpolation or not
        self.camInterpolation = 1
        # yaw direction is which way direction to turn while on the cable
        # (from endpoint 0 to 1)
        # This is automatically set by seeing how the user yaws while flying
        # but it can be overridden by the app
        self.yawDirection = 0

        # use this to perform dead reckoning
        self.lastPerc = 0.0
        self.deadReckoningTicks = 0

        self.accel = shotmgr.getParam( "WPNAV_ACCEL", DEFAULT_WPNAV_ACCEL_VALUE ) / 100.0
        logger.log("[cable cam]: Retrieved WPNAV_ACCEL: %f" % (self.accel * 100.0))
        self.desiredSpeed = 0.0

        # set this to True once our targeting is set up
        self.haveSetupTargeting = False

    # channels are expected to be floating point values in the (-1.0, 1.0) range
    def handleRCs( self, channels ):
        if len(self.waypoints) < 2:
            # if we've already recorded one waypoint, start
            # trying to remember the intended rotation direction here
            currentYaw = camera.getYaw(self.vehicle)
            yawDiff = currentYaw - self.lastYaw
            if yawDiff > 180.0:
                yawDiff -= 360.0
            elif yawDiff < -180.0:
                yawDiff += 360.0
            self.aggregateYaw += yawDiff
            self.lastYaw = currentYaw
            return

        self.desiredSpeed, goingForwards = self.pathHandler.MoveTowardsEndpt(channels)

        # the moment we enter guided for the first time, setup our targeting
        # For some as yet unknown reason, this still doesn't work unless we call
        # InterpolateCamera a few times, which is the reason for the
        # not self.haveSetupTargeting check below
        if not self.haveSetupTargeting and self.vehicle.mode.name == "GUIDED" and self.pathHandler.curTarget:
            self.setupTargeting()
            self.haveSetupTargeting = True
            logger.log("[cable cam]: did initial setup of targeting")

        self.yawPitchOffsetter.Update(channels)

        if self.camInterpolation > 0 or not self.haveSetupTargeting:
            # because we flipped cable cam around, we actually need to flip goingForwards
            self.InterpolateCamera(not goingForwards)
        else:
            self.handleFreePitchYaw()

        if self.pathHandler.isNearTarget():
            self.pathHandler.currentSpeed = 0.0
            self.pathHandler.pause()
            self.updateAppOptions()

    def recordLocation(self):
        degreesYaw = camera.getYaw(self.vehicle)
        pitch = camera.getPitch(self.vehicle)

        # don't allow two waypoints near each other
        if len(self.waypoints) == 1:
            if location_helpers.getDistanceFromPoints3d(self.waypoints[0].loc, self.vehicle.location.global_relative_frame) < WAYPOINT_NEARNESS_THRESHOLD:
                logger.log("[cable cam]: attempted to record a point too near the first point")
                # update our waypoint in case yaw, pitch has changed
                self.waypoints[0].yaw = degreesYaw
                self.waypoints[0].pitch = pitch

                # force the app to exit and restart cable cam
                packet = struct.pack('<IIi', app_packet.SOLO_MESSAGE_GET_CURRENT_SHOT, 4, shots.APP_SHOT_NONE)
                self.shotmgr.appMgr.sendPacket(packet)
                packet = struct.pack('<IIi', app_packet.SOLO_MESSAGE_GET_CURRENT_SHOT, 4, shots.APP_SHOT_CABLECAM)
                self.shotmgr.appMgr.sendPacket(packet)
                packet = struct.pack('<IIddfff', app_packet.SOLO_CABLE_CAM_WAYPOINT,
                28, self.vehicle.location.global_relative_frame.lat, self.vehicle.location.global_relative_frame.lon,
                        self.vehicle.location.global_relative_frame.alt, degreesYaw, pitch)
                self.shotmgr.appMgr.sendPacket(packet)
                return

        # create a waypoint and add it to our list
        waypt = Waypoint(self.vehicle.location.global_relative_frame, degreesYaw, pitch)

        logger.log("[cable cam]: Recorded location %f, %f, %f.  Yaw = %f" %
                    ( self.vehicle.location.global_relative_frame.lat, self.vehicle.location.global_relative_frame.lon,
                        self.vehicle.location.global_relative_frame.alt, degreesYaw))
        logger.log("[cable cam]: gimbal pitch is " + str(pitch))

        self.waypoints.append(waypt)
        self.setButtonMappings()

        # send this waypoint to the app
        packet = struct.pack('<IIddfff', app_packet.SOLO_CABLE_CAM_WAYPOINT,
                28, self.vehicle.location.global_relative_frame.lat, self.vehicle.location.global_relative_frame.lon,
                        self.vehicle.location.global_relative_frame.alt, degreesYaw, pitch)
        self.shotmgr.appMgr.sendPacket(packet)

        #start monitoring heading changes
        if len(self.waypoints) == 1:
            self.aggregateYaw = 0.0
            self.lastYaw = degreesYaw
        elif len(self.waypoints) == 2:
            # Now change the vehicle into guided mode
            self.vehicle.mode = VehicleMode("GUIDED")

            logger.log("[cable cam]: Got second cable point.  Should be in guided %s" % (str(self.vehicle.mode)))

            self.totalDistance = location_helpers.getDistanceFromPoints3d(
                self.waypoints[0].loc, self.waypoints[1].loc)

            # handle the 0-360 border
            if self.waypoints[1].yaw - self.waypoints[0].yaw > 180.0:
                self.waypoints[0].yaw += 360.0
            elif self.waypoints[1].yaw - self.waypoints[0].yaw < -180.0:
                self.waypoints[1].yaw += 360.0

            #disregard aggregate yaw if it's less than 180
            if abs(self.aggregateYaw) < 180.0:
                self.aggregateYaw = self.waypoints[1].yaw - self.waypoints[0].yaw

            self.yawDirection = 1 if self.aggregateYaw > 0.0 else 0

            logger.log("[cable cam]: Aggregate yaw = %f. Yaw direction saved as %s" % (self.aggregateYaw, "CCW" if self.yawDirection == 1 else "CW"))

            # send this yawDir to the app
            self.updateAppOptions()
            self.pathHandler = pathHandler.TwoPointPathHandler( self.waypoints[1].loc, self.waypoints[0].loc, self.vehicle, self.shotmgr )

    def InterpolateCamera(self, goingForwards):
        # Current request is to interpolate yaw and gimbal pitch separately
        # This can result in some unsmooth motion, but maybe it's good enough.
        # Alternatives would include slerp, but we're not interested in the shortest path.

        # first, see how far along the path we are
        dist = location_helpers.getDistanceFromPoints3d(self.waypoints[0].loc, self.vehicle.location.global_relative_frame)
        if self.totalDistance == 0.0:
            perc = 0.0
        else:
            perc = dist / self.totalDistance

        # offset perc using dead reckoning
        if self.lastPerc == perc:
            self.deadReckoningTicks += 1

            # adjust our last seen velocity based on WPNAV_ACCEL
            DRspeed = self.vehicle.groundspeed

            timeElapsed = self.deadReckoningTicks * UPDATE_TIME

            # one problem here is we don't simulate deceleration when reaching the endpoints
            if self.desiredSpeed > DRspeed:
                DRspeed += (timeElapsed * self.accel)
                if DRspeed > self.desiredSpeed:
                    DRspeed = self.desiredSpeed
            else:
                DRspeed -= (timeElapsed * self.accel)
                if DRspeed < self.desiredSpeed:
                    DRspeed = self.desiredSpeed

            if self.totalDistance > 0.0:
                percSpeed = DRspeed * timeElapsed / self.totalDistance

                #logger.log("same location, dead reckoning with groundspeed: %f"%(DRspeed))

                # and adjust perc
                if goingForwards:
                    perc += percSpeed
                else:
                    perc -= percSpeed

        else:
            self.deadReckoningTicks = 0
            self.lastPerc = perc
            # logger.log("NEW location, resetting dead reckoning.  Groundspeed: %f"%(self.vehicle.groundspeed))

        if perc < 0.0:
            perc = 0.0
        elif perc > 1.0:
            perc = 1.0

        invPerc = 1.0 - perc

        yawPt0 = self.waypoints[0].yaw
        yawPt1 = self.waypoints[1].yaw

        # handle if we're going other than the shortest dir
        if yawPt1 > yawPt0 and self.yawDirection == 0:
            yawPt0 += 360.0
        elif yawPt0 > yawPt1 and self.yawDirection == 1:
            yawPt1 += 360.0

        # interpolate vehicle yaw and gimbal pitch
        newYaw = perc * yawPt1 + invPerc * yawPt0

        # add in yaw offset
        newYaw += self.yawPitchOffsetter.yawOffset

        # since we possibly added 360 to either waypoint, correct for it here
        newYaw %= 360.0
        # print "point 0 yaw: " + str(self.waypoints[0].yaw) + " point 1 yaw: " + str(self.waypoints[1].yaw) + " interpolated yaw = " + str(newYaw) + " at position " + str(perc)
        newPitch = perc * self.waypoints[1].pitch + invPerc * self.waypoints[0].pitch
        newPitch += self.yawPitchOffsetter.pitchOffset

        if newPitch >= 0:
            newPitch = 0
        elif newPitch <= -90:
            newPitch = -90

        # if we do have a gimbal, mount_control it
        if self.vehicle.mount_status[0] is not None:
            msg = self.vehicle.message_factory.mount_control_encode(
                                            0, 1,    # target system, target component
                                            newPitch * 100, # pitch is in centidegrees
                                            0.0, # roll
                                            newYaw * 100, # yaw is in centidegrees
                                            0 # save position
                                            )
        else:
            # if we don't have a gimbal, just set CONDITION_YAW
            msg = self.vehicle.message_factory.command_long_encode(
                                            0, 0,    # target system, target component
                                            mavutil.mavlink.MAV_CMD_CONDITION_YAW, #command
                                            0, #confirmation
                                            newYaw, # param 1 - target angle
                                            YAW_SPEED, # param 2 - yaw speed
                                            self.yawDirection, # param 3 - direction
                                            0.0, # relative offset
                                            0, 0, 0 # params 5-7 (unused)
                                            )

        self.vehicle.send_mavlink(msg)

    # if we can handle the button we do
    def handleButton(self, button, event):
        if button == btn_msg.ButtonA and event == btn_msg.Press:
            if len(self.waypoints) == 0:
                self.recordLocation()
        if button == btn_msg.ButtonB and event == btn_msg.Press:
            if len(self.waypoints) == 1:
                self.recordLocation()
        if button == btn_msg.ButtonLoiter and event == btn_msg.Press:
            if self.pathHandler:
                self.shotmgr.notifyPause(True)
                self.pathHandler.togglePause()
                self.updateAppOptions()
            else:
                # notify autopilot of pause press (technically not in shot)
                self.shotmgr.notifyPause(False)

    # pass in the value portion of the SOLO_CABLE_CAM_OPTIONS packet
    def handleOptions(self, options):
        oldInterp = self.camInterpolation

        (self.camInterpolation, self.yawDirection, cruiseSpeed) = options

        logger.log( "[cable cam]: Set cable cam options to interpolation: %d, \
            yawDir: %d, cruising speed %f"%(self.camInterpolation, self.yawDirection, cruiseSpeed))

        # don't handle these if we're not ready
        if not self.pathHandler:
            return

        # pause or set new cruise speed
        if cruiseSpeed == 0.0:
            self.pathHandler.pause()
        else:
            self.pathHandler.setCruiseSpeed(cruiseSpeed)

        # change to a different targeting mode
        if oldInterp != self.camInterpolation:
            self.setupTargeting()


    def setButtonMappings(self):
        buttonMgr = self.shotmgr.buttonManager

        if len( self.waypoints ) == 0:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_CABLECAM, btn_msg.ARTOO_BITMASK_ENABLED, "Record Point\0")
            buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_CABLECAM, 0, "\0")
        elif len( self.waypoints ) == 1:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_CABLECAM, 0, "\0")
            buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_CABLECAM, btn_msg.ARTOO_BITMASK_ENABLED, "Record Point\0")
        else:
            buttonMgr.setArtooButton(btn_msg.ButtonA, shots.APP_SHOT_CABLECAM, 0, "\0")
            buttonMgr.setArtooButton(btn_msg.ButtonB, shots.APP_SHOT_CABLECAM, 0, "\0")

    # send our current set of options to the app
    def updateAppOptions(self):
        speed = 0.0

        if self.pathHandler:
            speed = self.pathHandler.cruiseSpeed
        packet = struct.pack('<IIHHf', app_packet.SOLO_CABLE_CAM_OPTIONS,
                8, self.camInterpolation, self.yawDirection, speed)
        self.shotmgr.appMgr.sendPacket(packet)

    def setupTargeting(self):
        # set gimbal targeting mode
        msg = self.vehicle.message_factory.mount_configure_encode(
                    0, 1,    # target system, target component
                    mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,  #mount_mode
                    1,  # stabilize roll
                    1,  # stabilize pitch
                    1,  # stabilize yaw
                    )

        self.shotmgr.rcMgr.enableRemapping( True )
        logger.log("[cable cam]: setting gimbal to mavlink mode")

        if self.camInterpolation > 0:
            logger.log("[cable cam]: turning on camera interpolation")
            self.yawPitchOffsetter.enableNudge()
        else:
            logger.log("[cable cam]: turning off camera interpolation")
            self.yawPitchOffsetter.disableNudge( camera.getPitch(self.vehicle), camera.getYaw(self.vehicle))

        self.vehicle.send_mavlink(msg)

    """
        In the case that we don't have view lock on, we enable 'free' movement of
        pitch/yaw.  Previously, we allowed flight code to control yaw, but since
        we want the throttle stick to control pitch, we need to handle it here.
        Our yawPitchOffsetter will contain the absolute pitch/yaw we want, so
        this function just needs to set them.
    """
    def handleFreePitchYaw(self):
        # if we do have a gimbal, use mount_control to set pitch and yaw
        if self.vehicle.mount_status[0] is not None:
            msg = self.vehicle.message_factory.mount_control_encode(
                                            0, 1,    # target system, target component
                                            self.yawPitchOffsetter.pitchOffset * 100, # pitch is in centidegrees
                                            0.0, # roll
                                            self.yawPitchOffsetter.yawOffset * 100, # yaw is in centidegrees
                                            0 # save position
                                            )
        else:
            # if we don't have a gimbal, just set CONDITION_YAW
            msg = self.vehicle.message_factory.command_long_encode(
                                            0, 0,    # target system, target component
                                            mavutil.mavlink.MAV_CMD_CONDITION_YAW, #command
                                            0, #confirmation
                                            self.yawPitchOffsetter.yawOffset, # param 1 - target angle
                                            YAW_SPEED, # param 2 - yaw speed
                                            self.yawPitchOffsetter.yawDir, # param 3 - direction
                                            0.0, # relative offset
                                            0, 0, 0 # params 5-7 (unused)
                                            )

        self.vehicle.send_mavlink(msg)

    def handlePacket(self, packetType, packetLength, packetValue):
        try:
            if packetType == app_packet.SOLO_RECORD_POSITION:
                self.recordLocation()

            elif packetType == app_packet.SOLO_CABLE_CAM_OPTIONS:
                options = struct.unpack('<HHf', packetValue)
                self.handleOptions(options)
            
            else:
                return False
        except Exception as e:
            logger.log('[cable cam]: Error handling packet. (%s)' % e)
            return False
        else:
            return True