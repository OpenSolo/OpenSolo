#
#  Code common across shots to handle movement on paths
#
from pymavlink import mavutil
import location_helpers
import shotLogger
from shotManagerConstants import *
import math
import shots

logger = shotLogger.logger

#Path accel/decel constants
PATH_ACCEL = 2
ACCEL_PER_TICK = PATH_ACCEL * UPDATE_TIME


class PathHandler():
    def __init__(self, vehicle, shotmgr):
        self.vehicle = vehicle
        self.shotMgr = shotmgr

        # Automatic cruising of the cable
        self.cruiseSpeed = 0.0
        self.resumeSpeed = 0.0

    def pause(self):
        self.resumeSpeed = self.cruiseSpeed
        self.setCruiseSpeed(0.0)
        logger.log("[%s]: Pausing cruise" % shots.SHOT_NAMES[self.shotMgr.currentShot].lower())

    def togglePause(self):
        if self.isPaused():
            self.resume()
        else:
            self.pause()

    def resume(self):
        self.setCruiseSpeed(0.0) # self.resumeSpeed to enable actual resume speed
        logger.log("[%s]: Resuming cruise." % shots.SHOT_NAMES[self.shotMgr.currentShot].lower())

    def isPaused(self):
        return self.cruiseSpeed == 0.0

    def setCruiseSpeed(self, speed):
        self.cruiseSpeed = speed


# special case of PathHandler
class TwoPointPathHandler(PathHandler):
    def __init__(self, pt1, pt2, vehicle, shotmgr):
        PathHandler.__init__(self, vehicle, shotmgr)
        self.pt1 = pt1
        self.pt2 = pt2
        self.curTarget = None

        #for simulated acceleration
        self.currentSpeed = 0.0
        self.desiredSpeed = 0.0

    # given RC input, calculate a speed and use it to
    # move towards one of our endpoints
    # return the speed we set for the copter
    def MoveTowardsEndpt( self, channels ):
        # allow both up/down and left/right to move along the cable
        # use the max of them
        if abs(channels[1]) > abs(channels[2]):
            value = channels[1]
        else:
            value = -channels[2]

        # user controls speed
        if self.cruiseSpeed == 0.0:
            self.desiredSpeed = value * MAX_SPEED
        # cruise control
        else:
            speed = abs(self.cruiseSpeed)
            # if sign of stick and cruiseSpeed don't match then...
            if math.copysign(1,value) != math.copysign(1,self.cruiseSpeed): # slow down
                speed *= (1.0 - abs(value))
            else: # speed up
                speed += (MAX_SPEED - speed) * abs(value)

            # carryover user input sign
            if self.cruiseSpeed < 0:
                speed = -speed

            # limit speed
            if speed > MAX_SPEED:
                speed = MAX_SPEED
            elif -speed > MAX_SPEED:
                speed = -MAX_SPEED

            self.desiredSpeed = speed

        # Synthetic acceleration
        if self.desiredSpeed > self.currentSpeed:
            self.currentSpeed += ACCEL_PER_TICK
            self.currentSpeed = min(self.currentSpeed, self.desiredSpeed)
        elif self.desiredSpeed < self.currentSpeed:
            self.currentSpeed -= ACCEL_PER_TICK
            self.currentSpeed = max(self.currentSpeed, self.desiredSpeed)
        else:
            self.currentSpeed = self.desiredSpeed

        #Check direction of currentSpeed
        goingForwards = self.currentSpeed > 0.0

        if goingForwards:
            target = self.pt2
        else:
            target = self.pt1

        if target != self.curTarget: #switching target and logging
            self.vehicle.simple_goto(target)
            self.curTarget = target
            logger.log("[%s]: Going to pt %d"%(shots.SHOT_NAMES[self.shotMgr.currentShot].lower(), 2 if goingForwards else 1 ) )
            logger.log("[%s]: Target is %.12f, %.12f, %.12f."%
                    (shots.SHOT_NAMES[self.shotMgr.currentShot].lower(), target.lat, target.lon,
                        target.alt))

        # should replace with a dronekit command when it gets in there
        msg = self.vehicle.message_factory.command_long_encode(
             0, 1,    # target system, target component
             mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
             0,       # confirmation
             1, abs(self.currentSpeed), -1, # params 1-3
             0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)

        # send command to vehicle
        self.vehicle.send_mavlink(msg)

        return abs(self.currentSpeed), goingForwards

    # returns if we're near our target or not
    def isNearTarget(self):
        if self.desiredSpeed > 0.0 and \
                location_helpers.getDistanceFromPoints3d( \
                self.vehicle.location.global_relative_frame, \
                self.pt2 ) < WAYPOINT_NEARNESS_THRESHOLD:
            return True
        elif self.desiredSpeed < 0.0 and \
                location_helpers.getDistanceFromPoints3d( \
                self.vehicle.location.global_relative_frame, \
                self.pt1 ) < WAYPOINT_NEARNESS_THRESHOLD:
            return True
        return False
