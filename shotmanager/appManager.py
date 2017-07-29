#
#  appManager.py
#  shotmanager
#
#  Handles app connection state and IO.
#
#  Created by Will Silva on 3/5/2016.
#  Copyright (c) 2016 3D Robotics.
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
sys.path.append(os.path.realpath(''))
import modes
import settings
import shots
import Queue
import struct
from dronekit.lib import LocationGlobalRelative
from sololink import btn_msg
import app_packet
import GoProManager
import shotLogger
import GeoFenceManager

logger = shotLogger.logger

APP_SERVER_PORT = 5507
APP_TCP_BUFSIZE = 1024

class appManager():
    def __init__(self, shotMgr):
        self.shotMgr = shotMgr
        self.connected = False
        self.client = None
        self.client_address = None
        self.clientQueue = None
        self.packetBuffer = ""
        self.bindServer()

    def bindServer(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if platform.system() != 'Darwin':
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)   # After 1 second, start KEEPALIVE
            self.server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)  # TCP Idle true 
            self.server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5) # 5 seconds in between keepalive pings
            self.server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)   # 5 max fails

        # Bind the socket to the port
        while True:
            try:
                self.server.bind(('', APP_SERVER_PORT))
            except:
                logger.log("[app]: Can't bind, address in use. Retrying in 1 second.")
                time.sleep(1.0)
            else:
                break

        logger.log("[app]: Ready for connections from app.")

        # Listen for incoming connections
        self.server.listen(0)

    # establishes a connection to a Solo app
    def connectClient(self):
        client, client_address = self.server.accept()

        if self.isAppConnected():
            if client_address[0] != self.client_address[0]:
                logger.log("[app]: Already connected to client %s - rejecting %s." % (self.client_address, client_address))
                #TO DO:send system INFO packet to app with rejection flag True
                client.close()
                return
            else:
                logger.log("[app]: Detected re-connection attempt for client %s - reconnecting.")
                self.disconnectClient()
        
        self.client = client
        self.client_address = client_address
        logger.log("[app]: Connected to App. %s" % (self.client_address,))
        #TO DO:send system INFO packet to app with rejection flag False
        self.connected = True
        self.client.setblocking(0)
        self.shotMgr.inputs.append(self.client)
        self.clientQueue = Queue.Queue()
        self.broadcastShotToApp(self.shotMgr.currentShot)

        self.shotMgr.buttonManager.setButtonMappings() # called to un-grey out Artoo buttons
        self.shotMgr.goproManager.sendState() # send gopro state to app


    def disconnectClient(self):
        if self.isAppConnected():
            logger.log("[app]: Closing client connection with %s." % (self.client_address,))
            self.connected = False
            if self.client in self.shotMgr.outputs:
                self.shotMgr.outputs.remove(self.client)
            if self.client in self.shotMgr.inputs:
                self.shotMgr.inputs.remove(self.client)
            self.client.close()
            self.client = None
            self.clientQueue = None
            self.shotMgr.buttonManager.setButtonMappings() # called to grey-out Artoo buttons

            # if this type of shot requires a client present at all times, then kill the shot
            if self.shotMgr.currentShot in shots.ALWAYS_NEEDS_APP_CONNECTION:
                self.shotMgr.enterShot(shots.APP_SHOT_NONE)
            # Clear Geofence when app disconnect
            self.shotMgr.geoFenceManager.clearGeoFence()
        else:
            logger.log('[app]: Attempted to close app connection, but no app was connected!')

    def isAppConnected(self):
        return self.connected

    def sendPacket(self, pkt):
        if self.isAppConnected():
            self.clientQueue.put(pkt)
            if self.client not in self.shotMgr.outputs:
               self.shotMgr.outputs.append(self.client)
        else:
            logger.log('[app]: Can\'t send packet - app is not connected!')

    def broadcastShotToApp(self, shot):
        packet = struct.pack('<IIi', app_packet.SOLO_MESSAGE_GET_CURRENT_SHOT, 4, shot)
        self.sendPacket(packet)

    def exception(self):
        logger.log("[app]: Exception with " + self.client.getpeername())
        self.appMgr.disconnectClient()

    def write(self):
        if self.clientQueue:
            try:
                msg = self.clientQueue.get_nowait()
            except Queue.Empty:
                # no messages left, stop checking
                self.shotMgr.outputs.remove(self.client)
            else:
                try:
                    self.client.send(msg)
                except Exception as ex:
                    logger.log("[app]: Exception on send. (%s)" % ex)
                    self.disconnectClient()

    def parse(self):
        try:
            data = self.client.recv(APP_TCP_BUFSIZE) # grab one kB
            if not data:
                raise socket.error()
        except socket.error:
            logger.log('[app]: Data from client %s is nil.' % (self.client_address,))
            self.disconnectClient()
            return

        self.packetBuffer += data

        while self.packetBuffer is not '':

            if len(self.packetBuffer) < app_packet.SOLO_MESSAGE_HEADER_LENGTH:
                logger.log('[app]: Not enough data for a Solo packet header yet.')
                return
            
            (packetType, packetLength) = struct.unpack('<II', self.packetBuffer[:app_packet.SOLO_MESSAGE_HEADER_LENGTH])
            
            if len(self.packetBuffer) < app_packet.SOLO_MESSAGE_HEADER_LENGTH + packetLength:
                logger.log('[app]: Not enough data for a Solo packet (ID: %s) yet.' % (packetType,))
                return

            # extract packet value from TLV based on known packetLength and packetType
            packetValue = self.packetBuffer[app_packet.SOLO_MESSAGE_HEADER_LENGTH:(app_packet.SOLO_MESSAGE_HEADER_LENGTH+packetLength)]

            handled = False

            # if a shot is active, pass the TLV packet to the shot's handlePacket function
            if self.shotMgr.curController:
                handled = self.shotMgr.curController.handlePacket(packetType, packetLength, packetValue)
            
            # if the packet wasn't understood by the shot, then try to handle it
            if not handled:
                handled = self.handlePacket(packetType, packetLength, packetValue)

            # crop out the packet from the buffer and move on
            self.packetBuffer = self.packetBuffer[app_packet.SOLO_MESSAGE_HEADER_LENGTH+packetLength:]

    def handlePacket(self, packetType, packetLength, packetValue):
        try:
            if packetType == app_packet.SOLO_MESSAGE_SET_CURRENT_SHOT:
                shot = struct.unpack('<i', packetValue)[0]
                logger.log("[app]: App requested shot : %s." % shots.SHOT_NAMES[shot])
                self.shotMgr.enterShot(shot)

            elif packetType == app_packet.SOLO_MESSAGE_GET_BUTTON_SETTING:
                # this is a request for the current button mapping.
                # fill in the fields and send it back
                (button, event, shot, APMmode) = struct.unpack('<iiii', packetValue)
                if event == btn_msg.Press:
                    (mappedShot, mappedMode) = self.shotMgr.buttonManager.getFreeButtonMapping(button)
                    logger.log("[app]: App requested button mapping for %d"%(button))

                    # send back to the app
                    packet = struct.pack('<IIiiii', app_packet.SOLO_MESSAGE_GET_BUTTON_SETTING, 16, button, event, mappedShot, mappedMode)
                    self.sendPacket(packet)

            # app is trying to map a button
            elif packetType == app_packet.SOLO_MESSAGE_SET_BUTTON_SETTING:
                (button, event, shot, APMmode) = struct.unpack('<iiii', packetValue)
                if event == btn_msg.Press:
                    self.shotMgr.buttonManager.setFreeButtonMapping( button, shot, APMmode )

            # Gopromanager handles these messages
            elif packetType in GoProManager.GOPROMESSAGES:
                self.shotMgr.goproManager.handlePacket( packetType, packetValue )

            elif packetType == app_packet.SOLO_REWIND_OPTIONS or packetType == app_packet.SOLO_HOME_LOCATION:
                self.shotMgr.rewindManager.handlePacket( packetType, packetLength, packetValue )

            # Geofence messages
            elif packetType in GeoFenceManager.GEO_FENCE_MESSAGES:
                self.shotMgr.geoFenceManager.handleFenceData(packetType, packetValue)

            else:
                logger.log("[app]: Got an unknown packet type: %d." % (packetType,))

        except Exception as e:
            logger.log('[app]: Error handling packet. (%s)' % e)
            return False
        else:
            return True
