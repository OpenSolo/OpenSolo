#
#  geoFenceManager.py
#  shotmanager
#
#  Utility to manage Geofence
#
#  Created by Yi Lu, improved based on Jason Short and Will Silva's GeoFence prototype
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

import struct
from enum import Enum
from dronekit import LocationGlobalRelative, VehicleMode, mavutil
import location_helpers
import app_packet
from vector3 import Vector3
from GeoFenceHelper import *
from math import sqrt
import shots
import json

logger = shotLogger.logger

GEO_FENCE_LATENCY_COEFF = 1.5 # seconds? not sure...

# tuple of message types that we handle
GEO_FENCE_MESSAGES = \
(
    app_packet.GEOFENCE_SET_DATA,
    app_packet.GEOFENCE_SET_ACK,
    app_packet.GEOFENCE_UPDATE_POLY,
    app_packet.GEOFENCE_CLEAR,
    app_packet.GEOFENCE_ACTIVATED
)


class _GeoFenceManagerState(Enum):
    notFenced = 0
    fenced = 1


class _GeoFenceManagerTetherState(Enum):
    notActive = 0
    active = 1


class GeoFence:

    def __init__(self, origin, verticesCart, subVerticesCart, stayOut=True):
        """
        This class define the structure of GeoFence data
        :param origin: GlobalLocationRelative
        :param verticesCart: [Vector3]
        :param subVerticesCart: [Vector3]
        :param stayOut: Bool
        """
        self.origin = origin
        self.vertices = verticesCart
        self.subVertices = subVerticesCart
        self.stayOut = stayOut

    def __str__(self):
        return "<Fence origin: %s, vertices: %s, stayOut: %s>" % (self.origin, self.vertices, self.stayOut)


class GeoFenceManager:
    """
    This class manage the GeoFence on Solo
    """

    def __init__(self, shotMgr):

        # assign the vehicle object
        self.vehicle = shotMgr.vehicle
        self.shotMgr = shotMgr

        self.polygons = []
        self.state = _GeoFenceManagerState.notFenced

        self.tetherLocation = None
        self.tetherState = _GeoFenceManagerTetherState.notActive

    def _reset(self):
        """
        Reset the states of GeoFence Manager. Will put copter into LOITER.
        Should be called to clean stuff up
        """

        self.polygons = []
        self.state = _GeoFenceManagerState.notFenced

        self.tetherLocation = None
        self.tetherState = _GeoFenceManagerTetherState.notActive

    def handleFenceData(self, packetType, packetValue):
        """
        handle all the incoming FLV data for GeoFence
        :param packetType: ShotManager packet type
        :param packetValue: Packet payloads
        """

        if packetType == app_packet.GEOFENCE_SET_DATA:
            geoFenceData = json.loads(packetValue)
            coordArr = geoFenceData['coord']
            subCoordArr = geoFenceData['subCoord']
            fenceTypeArr = geoFenceData['type']
            self._handleGeoFenceSetDataMessage(coordArr, subCoordArr, fenceTypeArr)

        elif packetType == app_packet.GEOFENCE_UPDATE_POLY:
            (updateType, polygonIndex, vertexIndex, lat, lng, subLat, subLng) = struct.unpack('<BHHdddd', packetValue)
            #TODO: updateType can be 0: update vertex, 1: add new vertex, 2: remove vertex. This parameter is ignored now and assumed to be updating vertex
            newCoord = LocationGlobalRelative(lat, lng, 0)
            newSubCoord = LocationGlobalRelative(subLat, subLng, 0)
            self._handleGeoFenceUpdateMessage(polygonIndex, vertexIndex, newCoord, newSubCoord)

        elif packetType == app_packet.GEOFENCE_CLEAR:
            self._reset()
            self._sendFenceSetAck(0, True)

    @staticmethod
    def _checkGeoFenceDataValidity(coordArr, subCoordArr, fenceTypeArr):
        if len(coordArr) != len(subCoordArr) or len(coordArr) != len(fenceTypeArr):
            # Data inconsistency
            logger.error("GeoFence data length mismatch: coord: %s, subCoord: %s, type: %s" % (len(coordArr), len(subCoordArr), len(fenceTypeArr)))
            return False
        for i in range(len(coordArr) - 1):
            if len(coordArr[i]) < 3:
                # Not a valid polygon
                logger.error("Illegal polygon received, polygon edge count: %s" % len(coordArr[i]))
                return False
            if len(coordArr[i]) != len(subCoordArr[i]):
                # Data inconsistency
                logger.error("Polygon and subpolygon have different edge count, polygon: %s, subpolygon: %s" % (len(coordArr[i]), len(subCoordArr[i])))
                return False
            for pair in coordArr[i]:
                if len(pair) != 2:
                    # Coord has length of 2
                    logger.error("Coordinate must be of length 2, got: %s" % len(pair))
                return False
            for pair in subCoordArr[i]:
                if len(pair) != 2:
                    logger.error("Coordinate must be of length 2, got: %s" % len(pair))
                    # Coord has length of 2
                return False
        return True

    def _handleGeoFenceSetDataMessage(self, coordArr, subCoordArr, fenceTypeArr):
        self.polygons = []

        # Check if data is well formatted
        dataValid = self._checkGeoFenceDataValidity(coordArr, subCoordArr, fenceTypeArr)

        if not dataValid:
            self._sendFenceSetAck(len(coordArr), False)
            return
        else:
            self._sendFenceSetAck(len(coordArr), True)

        # Data is good
        for i in range(len(coordArr)):
            coords = map(lambda coord: LocationGlobalRelative(coord[0], coord[1], 0), coordArr[i])
            subCoords = map(lambda coord: LocationGlobalRelative(coord[0], coord[1], 0), subCoordArr[i])
            fenceType = fenceTypeArr[i]
            # coords[0] is guaranteed to exist because a polygon with less than 3 vertices won't pass the validation
            origin = coords[0]
            coordsCart = map(lambda coord: location_helpers.getVectorFromPoints(origin, coord), coords)
            subCoordsCart = map(lambda coord: location_helpers.getVectorFromPoints(origin, coord), subCoords)

            # Repeat first coordinate, first elements are guaranteed to exist or validation will fail
            coordsCart.append(coordsCart[0])
            subCoordsCart.append(subCoordsCart[0])

            newGeoFence = GeoFence(origin, coordsCart, subCoordsCart, fenceType)
            logger.log("[GeoFenceManager]: coords: %s" % coordsCart)
            logger.log("[GeoFenceManager]: subCoords: %s" % subCoordsCart)
            self.polygons.append(newGeoFence)

    def _handleGeoFenceUpdateMessage(self, polygonIndex, vertexIndex, coord, subCoord):
        if polygonIndex < 0 or polygonIndex > len(self.polygons):
            logger.log("[GeoFenceManager]: Illegal polygonIndex, polygon count: %s, polygonIndex: %s" % (len(self.polygons), polygonIndex))
            self._sendFenceSetAck(0, False)
            return
        # Need to take 1 from the polygon vertex count because the first vertex is repeated
        if vertexIndex < 0 or vertexIndex > len(self.polygons[polygonIndex]) - 1:
            logger.log("[GeoFenceManager]: Illegal vertexIndex, vertices count: %s, vertexIndex: %s" % (len(self.polygons[polygonIndex]) - 1, vertexIndex))
            self._sendFenceSetAck(0, False)
            return
        origin = self.polygons[polygonIndex].origin
        coordCart = location_helpers.getVectorFromPoints(origin, coord)
        subCoordCart = location_helpers.getVectorFromPoints(origin, subCoord)
        self.polygons[polygonIndex].vertices[vertexIndex] = coordCart
        self.polygons[polygonIndex].subVertices[vertexIndex] = subCoordCart
        # Update extra vertex if the first vertex is being updated
        if vertexIndex == 0:
            lastIndex = len(self.polygons[polygonIndex])
            self.polygons[polygonIndex].vertices[lastIndex] = coordCart
            self.polygons[polygonIndex].subVertices[lastIndex] = subCoordCart
        self._sendFenceSetAck(len(self.polygons), True)

    def clearGeoFence(self):
        """
        Clear GeoFence when something bad happens, such as app disconnect
        """
        self._reset()

    def _sendFenceSetAck(self, count, valid):
        """
        Send Ack to app to acknowledge set count command
        :param count: the count of polygons received from app
        :param valid: Bool indicating if the acknowledging geofence is valid or not
        """
        packet = struct.pack('<IIH?', app_packet.GEOFENCE_SET_ACK, 3, count, valid)
        self.shotMgr.appMgr.sendPacket(packet)

    def sendClear(self):
        """
        Send Clear packet to the app to clear GeoFence
        """
        logger.log("[GeoFenceManager]: Sending clearing geofence")
        packet = struct.pack('<II', app_packet.GEOFENCE_CLEAR, 0)
        self.shotMgr.appMgr.sendPacket(packet)

    def _sendActivated(self):
        """
        Send activated packet to the app to clear GeoFence
        """
        packet = struct.pack('<II', app_packet.GEOFENCE_ACTIVATED, 0)
        self.shotMgr.appMgr.sendPacket(packet)

    def activateGeoFenceIfNecessary(self):
        """
        Test if GeoFence is about to be breached, if so, put copter into GUIDED and guide the copter to the best
        location. If not, do nothing.
        """

        if not self.vehicle.armed:
            return

        if self.vehicle.system_status in ['CRITICAL', 'EMERGENCY']:
            # Not enforcing Geofence in emergency
            return

        if self.tetherState is _GeoFenceManagerTetherState.active:
            # Still guiding to edge
            self._checkTetherLocation()
            return

        vehicleLocation = self.vehicle.location.global_relative_frame
        velocity = self.vehicle.velocity

        if vehicleLocation is None or vehicleLocation.lat is None or vehicleLocation.lon is None or vehicleLocation.alt is None:
            logger.log("[GeoFenceManager]: GeoFence: vehicle location not set")
            return
        if velocity is None:
            logger.log("[GeoFenceManager]: GeoFence: velocity is not set")
            return

        if len(self.polygons) == 0:
            # If GeoFence not set
            return

        velocityDirection = Vector2(velocity[0], velocity[1])

        collidingPoint = (-1, -1, float("inf"), None)

        # TODO: We are only supporting a single GeoFence right now, but it's subject to change in the future
        fence = self.polygons[0]
        if fence is None or fence.origin is None or fence.vertices is None:
            logger.log("[GeoFenceManager]: something is not right, fence:%s" % fence)
            return

        polygon = map(lambda coord: Vector2(coord.x, coord.y), fence.vertices)
        subPolygon = map(lambda coord: Vector2(coord.x, coord.y), fence.subVertices)
        v0_3d = location_helpers.getVectorFromPoints(fence.origin, vehicleLocation)
        v0 = Vector2(v0_3d.x, v0_3d.y)
        v1 = Vector2(v0.x + velocityDirection.x, v0.y + velocityDirection.y)

        # If not in fence, pull copter back into fence and return
        if GeoFenceHelper.isPointInPolygon(v0, polygon) == 0:
            logger.log("[GeoFenceManager]: Not in Fence!! v:%s poly: %s" % (v0, polygon))
            stopPoint2D = GeoFenceHelper.closestPointToPolygon(v0, subPolygon)
            if stopPoint2D is not None:
                # stopPoint2D can be None if an illegal polygon is passed
                stopPoint3D = Vector3(stopPoint2D.x, stopPoint2D.y, 0)
                stopCoordinate = location_helpers.addVectorToLocation(fence.origin, stopPoint3D)
                stopCoordinate.alt = vehicleLocation.alt
                self._stopAtCoord(stopCoordinate)
                return

        # Test if is going to collide
        currentCollidingPoint = GeoFenceHelper.closestCollisionVectorToPolygon(ray=(v0, v1), polygon=polygon)
        if currentCollidingPoint is not None and currentCollidingPoint[2] < collidingPoint[2]:
            collidingPoint = (0, currentCollidingPoint[0], currentCollidingPoint[1], currentCollidingPoint[2])

        if collidingPoint[0] != -1 and collidingPoint[1] != -1:
            fence = self.polygons[collidingPoint[0]]
            scalarSpeed = sqrt(velocity[0] * velocity[0] + velocity[1] * velocity[1])  # TODO: m/s ??
            currentCollidingPoint3D = Vector3(collidingPoint[3].x, collidingPoint[3].y, 0)
            collidingPointCoord = location_helpers.addVectorToLocation(fence.origin, currentCollidingPoint3D)
            scalarDistance = location_helpers.getDistanceFromPoints(vehicleLocation, collidingPointCoord)
            # Compensate for the latency
            scalarDistance -= scalarSpeed * GEO_FENCE_LATENCY_COEFF
            scalarDistance = max(scalarDistance, 0.0)
            maximumStoppingSpeed = self._stoppingSpeed(scalarDistance, scalarSpeed)

            if scalarDistance < 0 or scalarSpeed >= maximumStoppingSpeed:
                # If collision is None, that means copter has breached the subPolygon, tether to closest point on subpolygon,
                # otherwise, tether to the collision point on subpolygon
                collision = GeoFenceHelper.closestCollisionVectorToPolygon(ray=(v0, v1), polygon=subPolygon)
                if collision is None:
                    targetStopPoint2D = GeoFenceHelper.closestPointToPolygon(v0, subPolygon)
                else:
                    targetStopPoint2D = collision[2]


                if targetStopPoint2D is None:
                    logger.log("[GeoFenceManager]: Failed to activate geofence")
                    return
                logger.log("[GeoFenceManager]: Activating geofence, speed: %s max_speed:%s" % (scalarSpeed, maximumStoppingSpeed))
                logger.log("[GeoFenceManager]: copterLoc: %s will collide with %s, tether to %s" % (v0, collidingPoint[3], targetStopPoint2D))
                # If currently in a shot, end shot
                if self.shotMgr.currentShot != shots.APP_SHOT_NONE:
                    self.shotMgr.enterShot(shots.APP_SHOT_NONE)

                targetStopPoint3D = Vector3(targetStopPoint2D.x, targetStopPoint2D.y, 0)
                targetStopCoordinate = location_helpers.addVectorToLocation(fence.origin, targetStopPoint3D)
                targetStopCoordinate.alt = vehicleLocation.alt
                self._stopAtCoord(targetStopCoordinate)

    def _stopAtCoord(self, coordinate):
        """
        Move a copter to a point
        :param coordinate: LocationGlobalRelative, target coordinate
        """
        self._sendActivated()
        self.vehicle.mode = VehicleMode("GUIDED")
        posVelMsg = self.vehicle.message_factory.set_position_target_global_int_encode(
            0,       # time_boot_ms (not used)
            0, 1,    # target system, target component
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,  # frame
            0b0000110111000000,  # type_mask - enable pos/vel
            int(coordinate.lat * 10000000),  # latitude (degrees*1.0e7)
            int(coordinate.lon * 10000000),  # longitude (degrees*1.0e7)
            coordinate.alt,  # altitude (meters)
            0, 0, 0,  # North, East, Down velocity (m/s)
            0, 0, 0,  # x, y, z acceleration (not used)
            0, 0)    # yaw, yaw_rate (not used)
        self.vehicle.send_mavlink(posVelMsg)
        self.tetherState = _GeoFenceManagerTetherState.active
        self.tetherLocation = coordinate

    def _checkTetherLocation(self):
        """
        Check if the copter has reached the target location, if so, put the copter back to FLY
        """

        if self.tetherLocation is None or self.vehicle.location.global_relative_frame is None:
            logger.log("[GeoFenceManager]: something is not set, tetherLoc:%s vehicleLoc:%s" % (self.tetherLocation, self.vehicle.location.global_relative_frame))
            return

        distance = location_helpers.getDistanceFromPoints(self.vehicle.location.global_relative_frame, self.tetherLocation)
        # If vehicle is within 1 meter of destination or if vehicle is already within the shrunk polygon
        if distance < 1.0:
            self.tetherState = _GeoFenceManagerTetherState.notActive
            self.vehicle.mode = VehicleMode("LOITER")
            self.tetherLocation = None
            logger.log("[GeoFenceManager]: Deactivating GeoFence")
        else:
            # Re-enforce tether location in case user hit FLY
            if self.tetherLocation is not None and self.vehicle.mode != VehicleMode("GUIDED"):
                self._stopAtCoord(self.tetherLocation)

    @staticmethod
    def _stoppingSpeed(dist, speed):
        """
        Return maximum stopping speed, based on distance and current speed
        :param dist: Distance to go before stop
        :param speed: current scalar speed
        :return: Maximum speed at current distance before breach
        """
        # TODO: These are constant from multipoint.py
        tanAccelLim = 1.0897247358851685
        smoothStopP = 0.7
        linearVelocity = tanAccelLim / smoothStopP
        linearDist = linearVelocity / smoothStopP

        if speed > linearVelocity:
            return sqrt(2. * tanAccelLim * (speed**2/(2.*tanAccelLim) + dist))
        else:
            p1 = speed / smoothStopP
            p2 = p1 + dist

            if p2 > linearDist:
                return sqrt(2. * tanAccelLim * (p2 - 0.5*linearDist))
            else:
                return p2 * smoothStopP
