#helper functions for location
from dronekit.lib import LocationGlobalRelative
import math
from vector3 import Vector3

LATLON_TO_M  =  111195.0

#optimize : store persistent sclaing
def getLonScale(lat):
    scale   = 1 / math.cos(math.radians(lat))
    return scale


#returns distance between the given points in meters
def getDistanceFromPoints(loc1, loc2):
    dlat    = (loc2.lat - loc1.lat)
    dlong   = (loc2.lon - loc1.lon) / getLonScale(loc1.lat)
    dist    = math.sqrt((dlat * dlat) + (dlong * dlong)) * LATLON_TO_M
    return dist


#returns distance between the given points in meters
def getDistanceFromPoints3d(loc1, loc2):
    dlat    = (loc2.lat - loc1.lat)
    dlong   = (loc2.lon - loc1.lon) / getLonScale(loc1.lat)
    dalt    = (loc2.alt - loc1.alt) / LATLON_TO_M
    dist    = math.sqrt((dlat * dlat) + (dlong * dlong) + (dalt * dalt)) * LATLON_TO_M
    return dist


#Calculate a Location from a start location, azimuth (in degrees), and distance
#this only handles the 2D component (no altitude)
def newLocationFromAzimuthAndDistance(loc, azimuth, distance):
    result = LocationGlobalRelative(loc.lat, loc.lon, loc.alt)
    az          = math.radians(azimuth)
    distance    = distance / LATLON_TO_M
    result.lat = loc.lat + math.cos(az) * distance
    result.lon = loc.lon + math.sin(az) * distance * getLonScale(loc.lat)
    return result


#calculate azimuth between a start and end point (in degrees)
def calcAzimuthFromPoints(loc1, loc2):
    off_x   = (loc2.lon - loc1.lon) / getLonScale(loc1.lat)
    off_y   = (loc2.lat - loc1.lat)  
    az      = 90 + math.degrees(math.atan2(-off_y, off_x))
    return wrapTo360(az)


# given a start and an end point, return a Vector containing deltas in meters between start/end 
# along each axis
# returns a Vector3 
def getVectorFromPoints(start, end):
    x = (end.lat - start.lat) * LATLON_TO_M

    # calculate longitude scaling factor.  We could cache this if necessary
    # but we aren't doing so now
    y = ((end.lon - start.lon) * LATLON_TO_M) / getLonScale(start.lat)
    z = end.alt - start.alt
    return Vector3(x, y, z)


# add the given Vector3 (storing meter deltas) to the given Location
# and return the resulting Location
def addVectorToLocation(loc, vec):
    xToDeg = vec.x / LATLON_TO_M
    # calculate longitude scaling factor.  We could cache this if necessary
    # but we aren't doing so now
    yToDeg = (vec.y / LATLON_TO_M) * getLonScale(loc.lat)
    return LocationGlobalRelative(loc.lat + xToDeg, loc.lon + yToDeg, loc.alt + vec.z)


# Casts a ray at the ground based on the location, heading and camera pitch
# The Spot lock location is always equal to home altitude (zero)
def getSpotLock(loc, pitch, yaw):
    #expecting 0(straight) to -90 (down)
    pitch = 90.0 - pitch
    dist = math.tan(math.radians(-pitch)) * loc.alt    
    loc = newLocationFromAzimuthAndDistance(loc, yaw, dist)
    loc.alt = 0
    return loc


# Given a location, find yaw and pitch from Solo to look at that point
# returns a (yaw, pitch) tuple
def calcYawPitchFromLocations(start, end):
    yaw = calcAzimuthFromPoints(start, end)
    dist = getDistanceFromPoints(start, end)
    # inverting the equation above:
    # dist = loc.alt * math.tan(iPitchR)
    # we get
    # iPitchR = math.atan(dist/alt) where alt is the alt difference between our points
    altDiff = start.alt - end.alt
    if altDiff < 1.0:
        return yaw, 0
    iPitchR = math.atan(dist/altDiff)
    iPitch = math.degrees(iPitchR)
    pitch = iPitch - 90

    return yaw, pitch


def wrapTo180(val):
    if (val < -180) or (180 < val):
        return wrapTo360(val + 180) - 180
    else:
        return val


def wrapTo360(val):
    wrapped = val % 360
    if wrapped == 0 and val > 0:
        return 360
    else:
        return wrapped

def deg2rad(deg):
    return deg * math.pi/180.

def rad2deg(rad):
    return rad * 180./math.pi