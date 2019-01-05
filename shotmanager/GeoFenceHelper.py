#
#  geoFenceHelper.py
#  shotmanager
#
#  Helper class to do the math in fenceManager
#
#  Created by Yi Lu
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

from vector2 import *
import shotLogger
logger = shotLogger.logger


class GeoFenceHelper:

    @staticmethod
    def closestPointToSegment(point, segment):
        """
        Find the closest point from a point to a segment
        :param point: Vector2, source point
        :param segment: list of Vector2 with length of 2, denoting two end points of a segment
        :return: Tuple (Float, Vector2), first element is the position t of result point on the segment from 0-1
                 second element is a Vector2 denoting the resulting point
        """

        if len(segment) < 2:
            logger.log("[GeoFenceHelper]: Illegal segment %s" % segment)
            return None
        a = segment[0]
        b = segment[1]
        aToP = point - a
        aToB = b - a
        atb2 = aToB.x * aToB.x + aToB.y * aToB.y
        atp_dot_atb = aToP.dot(aToB)
        if atb2 != 0:
            t = float(atp_dot_atb) / atb2
        else:
            # a and b are infinitely close
            return a, (point - a).length()

        intersect = Vector2(a.x + aToB.x * t, a.y + aToB.y * t)
        distance = (point - intersect).length()
        if 0 <= t <= 1:
            return intersect, distance
        elif t < 0:
            return a, (point - a).length()
        else:
            return b, (point - b).length()

    @staticmethod
    def closestPointToPolygon(point, polygon):
        """
        Find the closest point from a point to a polygon defined by a list of vertices
        :param point: Vector2, source point
        :param polygon: list of Vector2, defines the vertices of polygon, minimum length 3
        :return: None if an illegal polygon has been passed
                 Vector2 denoting the resulting point if found
        """

        # Polygon must has at least 3 vertices plus repeated origin
        if len(polygon) < 4:
            logger.log("[GeoFenceHelper]: Polygon need at least three vertices")
            return None
        intersect = None
        distance = float("inf")
        for i in range(0, len(polygon) - 1):
            a = polygon[i]
            b = polygon[i + 1]
            segIntersect, segDistance = GeoFenceHelper.closestPointToSegment(point, [a, b])
            if segDistance < distance:
                intersect = segIntersect
                distance = segDistance
        return intersect

    @staticmethod
    def closestCollisionVectorToSegment(ray, segment):
        """
        http://stackoverflow.com/questions/14307158/how-do-you-check-for-intersection-between-a-line-segment-and-a-line-ray-emanatin
        Detect the collision point for a ray with a segment
        :param ray: Tuple of Vector2, origin and direction denoting a ray
        :param segment: Tuple of Vector2, denoting segment to be tested against collision
        :return: None if ray is not intersecting with segment
                 Float t if intersecting, t is the position of intersection on the ray
                 in equation: r(t) = ray[0] + t * (ray[1] - ray[0])
        """
        denom = ((ray[1].x - ray[0].x) * (segment[1].y - segment[0].y)) - (ray[1].y - ray[0].y) * (segment[1].x - segment[0].x)
        if denom == 0:
            return None
        r = (((ray[0].y - segment[0].y) * (segment[1].x - segment[0].x)) - (ray[0].x - segment[0].x) * (segment[1].y - segment[0].y)) / denom
        s = (((ray[0].y - segment[0].y) * (ray[1].x - ray[0].x)) - (ray[0].x - segment[0].x) * (ray[1].y - ray[0].y)) / denom
        if r >= 0 and 0 <= s <= 1:
            return r
        return None

    @staticmethod
    def closestCollisionVectorToPolygon(ray, polygon):
        """
        Detect the closet collision point for a ray with a polygon
        :param ray: Tuple of Vector2, origin and direction denoting a ray
        :param polygon: list of Vector2
        :return: None if ray is not intersecting with polygon
                 (Int, Double, Vector2) if intersection is found
                 Int being edge index
                 Double being position along collision vector
                 Vector2 being collision point on Polygon
        """
        # Polygon must has at least 3 vertices plus repeated origin
        if len(polygon) < 4:
            logger.log("[GeoFenceHelper]: Illegal polygon, vertex count must be 3 or more, got %s" % len(polygon))
            return None
        collidingPoint = (-1, float("inf"), None)

        for i in range(len(polygon) - 1):
            t = GeoFenceHelper.closestCollisionVectorToSegment(ray, (polygon[i], polygon[i + 1]))
            if t is not None and 0 < t < collidingPoint[1]:
                intersection = Vector2(ray[0].x + t * (ray[1].x - ray[0].x), ray[0].y + t * (ray[1].y - ray[0].y))
                collidingPoint = (i, t, intersection)

        if collidingPoint[0] == -1:
            return None
        return collidingPoint

    @staticmethod
    def isPointInPolygon(point, polygon):
        """
        http://geomalgorithms.com/a03-_inclusion.html#wn_PnPoly()
        :param point: Vector2 denoting the point
        :param polygon: list of Vector2 denoting vertices of polygon
        :return: Winding number of point and polygon:
                 0 if point is outside polygon
                 >0 if polygon is winding around point 1 or more times
                 <0 if polygon is not ccw?
        """
        # Polygon must has at least 3 vertices plus repeated origin
        if len(polygon) < 4:
            logger.log("[GeoFenceHelper]: polygon must have 3 or more vertices, got %s" % len(polygon))
            return None
        wn = 0
        for i in range(0, len(polygon) - 1):
            v1 = polygon[i]
            v2 = polygon[i + 1]
            if v1.y <= point.y:
                if v2.y > point.y:
                    if GeoFenceHelper.isLeft(v1, v2, point) > 0:
                        wn += 1
            else:
                if v2.y <= point.y:
                    if GeoFenceHelper.isLeft(v1, v2, point) < 0:
                        wn -= 1
        return wn

    @staticmethod
    def isLeft(p0, p1, p2):
        """
        http://geomalgorithms.com/a01-_area.html
        Test if a point is Left|On|Right of an infinite 2D line.
        :param p0: Vector2, first point of segment
        :param p1: Vector2, second point of segment
        :param p2: Vector2, point to be tested against segment
        :return: >0 for P2 left of the line through P0 to P1
                =0 for P2 on the line
                 <0 for P2 right of the line
        """
        return (p1.x - p0.x) * (p2.y - p0.y) - (p2.x - p0.x) * (p1.y - p0.y)
