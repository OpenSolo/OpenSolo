#
#  rewindManager.py
#  shotmanager
#
#  The section smart shot controller.
#  Runs as a DroneKit-Python script.
#
#  Created by Jason Short
#  Copyright (c) 2015 3D Robotics.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from dronekit import Vehicle, LocationGlobalRelative, LocationGlobal
from pymavlink import mavutil

import shots
import location_helpers
import struct
import app_packet
import math
import shotLogger

RTL_STEP_DIST = 1
RTL_MIN_DISTANCE = 10
RTL_DEFAULT_DISTANCE = 20
RTL_MAX_DISTANCE = 60

LOOP_LIMITER = 4
logger = shotLogger.logger

class RewindManager():

    def __init__(self, vehicle, shotmgr):
        logger.log("[RewindManager] Init")

        # assign the vehicle object
        self.vehicle = vehicle
        
        self.shotmgr = shotmgr

        # should we hover after RTL (True) or Land (False)
        self.hover = False

        # should we rewind or just RTL
        self.enabled = True

        # length of breadcrumb trail
        self.rewindDistance = RTL_DEFAULT_DISTANCE

        # Size of location storage
        self.bufferSize  = int(math.floor(self.rewindDistance / RTL_STEP_DIST))

        # location buffer and pointer
        self.buffer = None
        self.currentIndex = 0

        # Flag to fill buffer once we get good locations
        self.did_init = False

        # compute limiting
        self.counter = 0

        # proxy for the vehcile home
        self.homeLocation = None
        
        # manages behavior in Auto
        self.fs_thr = self.shotmgr.getParam( "FS_THR_ENABLE", 2 )
        


    def resetSpline(self):
        logger.log("[RewindManager] reset Spline to size %d" % self.bufferSize)
        vehicleLocation = self.vehicle.location.global_relative_frame

        if vehicleLocation is None or vehicleLocation.lat is None or vehicleLocation.lon is None or vehicleLocation.alt is None:    
            self.did_init = False
            return
        else:
            self.buffer = [None for i in range(self.bufferSize)]
            self.did_init = True
            self.buffer[0] = vehicleLocation
            self.currentIndex = 0


    def loadHomeLocation(self):
        ''' Hack method to avoid Dronekit issues with loading home from vehicle'''
        if self.vehicle is None:
            logger.log("no Vehicle!")
                
        #load home from vehicle
        # total grossness for getting HOME_LOCATION! Should be done properly in dronekit instead
        self.vehicle.add_message_listener('MISSION_ITEM', self.handleMissionItem)
        # formulate mavlink message to request home position
        self.vehicle.message_factory.mission_request_send(0, 1, 0)  # target_system, target_component, seq
        #logger.log("loading home from vehicle2")

    def handleMissionItem(self, vehicle, name, msg):
        ''' Handles callback for home location from vehicle '''
        self.vehicle.remove_message_listener('MISSION_ITEM', self.handleMissionItem)
        self.homeLocation = LocationGlobal(msg.x, msg.y, msg.z)
        logger.log("[RewindManager] loaded home %f %f, alt %f" % (self.homeLocation.lat, self.homeLocation.lon, self.homeLocation.alt))
        # Send home to the App
        self.updateAppOptions()
        

    def updateAppOptions(self):
        ''' send home loc to App '''
        # f = float_32
        # d = float_64
        packet = struct.pack('<IIddf', app_packet.SOLO_HOME_LOCATION, 20, self.homeLocation.lat, self.homeLocation.lon, self.homeLocation.alt)
        self.shotmgr.appMgr.sendPacket(packet)


    def updateLocation(self):
        ''' Store locations for Rewind Spline'''

        # load limiter
        self.counter += 1

        if self.counter > LOOP_LIMITER:
            self.counter = 0
        else:
            return

        if not self.vehicle.armed or self.vehicle.system_status != 'ACTIVE':
            # we don't want to reset every cycle while on ground
            if self.currentIndex != 0:
                self.resetSpline()
            return

        vehicleLocation = self.vehicle.location.global_relative_frame

        if vehicleLocation is None or vehicleLocation.lat is None or vehicleLocation.lon is None or vehicleLocation.alt is None:
            return

        # reset buffer with the current location if needed
        if self.did_init is False or self.buffer[self.currentIndex] is None:
            self.resetSpline()
            return

        try:
            # calc distance from home
            dist = location_helpers.getDistanceFromPoints3d(self.buffer[self.currentIndex], vehicleLocation)

        except Exception as e:
            logger.log('[RewindManager]: loc was None, %s' % e)


        #logger.log("dist %f"% dist)

        if dist >= RTL_STEP_DIST:
            # store new location in next index
            self.currentIndex += 1
            # mind the size of the buffer
            if(self.currentIndex >= self.bufferSize):
                self.currentIndex = 0

            # store the location
            self.buffer[self.currentIndex] = vehicleLocation

            # keep for testing
            #logger.log("[RWMGR]: Save %d %f %f %f" % (self.currentIndex,
            #                    vehicleLocation.lat,
            #                    vehicleLocation.lon,
            #                    vehicleLocation.alt))


    def queueNextloc(self):
        ''' Called by Rewind shot '''

        if self.buffer is None:
            return None

        # get ref to current buffered location
        temp = self.buffer[self.currentIndex]

        # put a None in the array to clear it
        self.buffer[self.currentIndex] = None

        # decrement index
        self.currentIndex -= 1
        if self.currentIndex < 0:
            self.currentIndex = self.bufferSize - 1
        
        #logger.log("[RewindManager] next loc index %d %d" % (self.currentIndex, self.bufferSize))
        
        if temp is None:
            #logger.log("[RewindManager] next loc is None")
            self.resetSpline()

        return temp


    def handlePacket(self, packetType, packetLength, packetValue):
        '''handle incoming data from the client app'''
        try:
            if packetType == app_packet.SOLO_REWIND_OPTIONS:

                # don't read packet if we are in Rewind
                if self.shotmgr.currentShot != shots.APP_SHOT_REWIND:
                    #(self.enabled) = struct.unpack('<B', packetValue)
                    (self.enabled, self.hover, _rewindDistance) = struct.unpack('<BBf', packetValue)
                    logger.log("[RWMGR]: Rewind enabled: %d" % self.enabled)
                    logger.log("[RWMGR]: Rewind RTL hover: %d" % self.hover)
                    logger.log("[RWMGR]: Rewind distance: %d" % _rewindDistance)

                    if _rewindDistance != self.rewindDistance:
                        self.rewindDistance = max(min(_rewindDistance, RTL_MAX_DISTANCE), RTL_MIN_DISTANCE)
                        self.bufferSize  = int(math.floor(self.rewindDistance / RTL_STEP_DIST))
                        logger.log("[RWMGR]: self.bufferSize: %d" % self.bufferSize)
                        self.resetSpline()

            elif packetType == app_packet.SOLO_HOME_LOCATION:
                if self.homeLocation is None:
                    return True
                    
                ''' Store new home location for Return to Me'''
                (lat, lon, alt) = struct.unpack('<ddf', packetValue)
                                
                # only respond to the app data when we are armed and in the air
                if self.vehicle.armed == 1 and self.vehicle.system_status == 'ACTIVE':
                    self.homeLocation = LocationGlobal(lat, lon, self.homeLocation.alt)
                    #logger.log("[RWMGR]: New Home loc set: %f, %f, %f" % (lat, lon, self.homeLocation.alt))

                    # let the app know we repsoned to the data
                    self.updateAppOptions()
            else:
                return False
        except Exception as e:
            logger.log('[RWMGR]: Error handling packet. (%s)' % e)
            return False
        else:
            return True


