#
#  Code common across shots to handle movement on paths
#
from pymavlink import mavutil
import location_helpers
import shotLogger
from pathHandler import PathHandler
from shotManagerConstants import *
import math
from vector3 import Vector3

logger = shotLogger.logger

#Path accel/decel constants
WPNAV_ACCEL = 3.4
WPNAV_ACCEL_Z = 1.6

# for 3D max speed
HIGH_PATH_SPEED = 5.0
LOW_PATH_SPEED = 1.5
MAX_PATH_SPEED = HIGH_PATH_SPEED + LOW_PATH_SPEED 

# used to correct for drag or other factors
ERROR_P = .01

# special case of PathHandler
class VectorPathHandler(PathHandler):
    def __init__(self, vehicle, shotManager, heading, pitch):
        PathHandler.__init__(self, vehicle, shotManager)

        # the initial reference position
        self.initialLocation = vehicle.location.global_relative_frame
        self.heading = heading

        # creates a unit vector from telemetry data
        self.unitVector = self.getUnitVectorFromHeadingAndTilt(heading, pitch)
        
        # limit speed based on vertical component
        # We can't go full speed vertically
        # this section should be 2.0 to 8.0 m/s
        # to generate a nice speed limiting curve we scale it.
        # pitch is used to generate the vertical portion of the 3d Vector

        pitch = min(pitch, 0) # level
        pitch = max(pitch, -90) # down
        accelXY = shotManager.getParam( "WPNAV_ACCEL", WPNAV_ACCEL ) / 100.0
        accelZ = shotManager.getParam( "WPNAV_ACCEL_Z", WPNAV_ACCEL_Z ) / 100.0

        cos_pitch = math.cos(math.radians(pitch))
        
        self.maxSpeed = LOW_PATH_SPEED + (cos_pitch**3 * HIGH_PATH_SPEED)
        self.maxSpeed = min(self.maxSpeed, MAX_PATH_SPEED)
        self.accel = accelZ + (cos_pitch**3 * (accelXY - accelZ))        
        self.accel *= UPDATE_TIME

        # the current distance from the intitial location
        self.distance = 0.0

        #for synthetic acceleration
        self.currentSpeed = 0.0
        self.desiredSpeed = 0.0
        self.distError = 0.0

    # given RC input, calculate a speed to move along vector
    def move(self, channels):

        # allows travel along the vector
        # use the max of them
        if abs(channels[ROLL]) > abs(channels[PITCH]):
            userInput = channels[ROLL]
        else:
            userInput = -channels[PITCH]

        # user controls speed
        if self.cruiseSpeed == 0.0:
            self.desiredSpeed = userInput * self.maxSpeed

        # cruise control
        else:
            speed = abs(self.cruiseSpeed)
            # if sign of stick and cruiseSpeed don't match then...
            if math.copysign(1, userInput) != math.copysign(1, self.cruiseSpeed): # slow down
                speed *= (1.0 - abs(userInput))
            else: # speed up
                speed += (self.maxSpeed - speed) * abs(userInput)

            # carryover user input sign
            if self.cruiseSpeed < 0:
                speed = -speed

            # limit speed
            if speed > self.maxSpeed:
                speed = self.maxSpeed
            elif -speed > self.maxSpeed:
                speed = -self.maxSpeed

            self.desiredSpeed = speed
    
        # Synthetic acceleration
        if self.desiredSpeed > self.currentSpeed:
            self.currentSpeed += self.accel
            self.currentSpeed = min(self.currentSpeed, self.desiredSpeed)
        elif self.desiredSpeed < self.currentSpeed:
            self.currentSpeed -= self.accel
            self.currentSpeed = max(self.currentSpeed, self.desiredSpeed)
        else:
            self.currentSpeed = self.desiredSpeed


        # the distance to fly along the vectorPath
        self.distance += self.currentSpeed * UPDATE_TIME
        self.distance += self.distError * ERROR_P

        # generate Guided mode commands to move the copter
        self.travel()

        # report speed output
        return abs(self.currentSpeed)


    def travel(self):
        ''' generate a new location from our distance offset and initial position '''
                
        # the location of the vehicle in meters from the origin
        offsetVector = self.unitVector * self.distance

        # Scale unit vector by speed
        velVector  = self.unitVector * self.currentSpeed

        # Convert NEU to NED velocity
        #velVector.z = -velVector.z

        # generate a new Location from our offset vector and initial location
        loc = location_helpers.addVectorToLocation(self.initialLocation, offsetVector)

        # calc dot product so we can assign a sign to the distance
        vectorToTarget = location_helpers.getVectorFromPoints( self.initialLocation, self.vehicle.location.global_relative_frame)
        dp =  self.unitVector.x * vectorToTarget.x
        dp += self.unitVector.y * vectorToTarget.y
        dp += self.unitVector.z * vectorToTarget.z
        
        self.actualDistance = location_helpers.getDistanceFromPoints3d(self.initialLocation, self.vehicle.location.global_relative_frame)

        if (dp < 0):
            self.actualDistance = -self.actualDistance

        # We can now compare the actual vs vector distance
        self.distError = self.actualDistance - self.distance
                
        # formulate mavlink message for pos-vel controller
        posVelMsg = self.vehicle.message_factory.set_position_target_global_int_encode(
            0,       # time_boot_ms (not used)
            0, 1,    # target system, target component
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,  # frame
            0b0000110111000000,  # type_mask - enable pos/vel
            int(loc.lat * 10000000),  # latitude (degrees*1.0e7)
            int(loc.lon * 10000000),  # longitude (degrees*1.0e7)
            loc.alt,  # altitude (meters)
            velVector.x, velVector.y, velVector.z,  # North, East, Down velocity (m/s)
            0, 0, 0,  # x, y, z acceleration (not used)
            0, 0)    # yaw, yaw_rate (not used)

        # send pos-vel command to vehicle
        self.vehicle.send_mavlink(posVelMsg)


    def getUnitVectorFromHeadingAndTilt(self, heading, tilt):
        ''' generate a vector from the camera gimbal '''
        angle  = math.radians(90 - heading)
        tilt   = math.radians(tilt)
        
        # create a vector scaled by tilt
        x = math.cos(tilt)
        
        # Rotate the vector
        nx = x * math.cos(angle)
        ny = x * math.sin(angle)

        # Up
        z = math.sin(tilt)
                        
        return Vector3(ny, nx, z)

