#
#  Code common across shots to offset yaw or pitch
#

from shotManagerConstants import *

# in degrees per second
# The user will be able to offset yaw from the interpolated position at this speed
# this is the speed the user is able to offset yaw at
YAW_OFFSET_SPEED = 60.0
# this is the speed that the yaw offset corrects itself
# should be less than YAW_OFFSET_SPEED
YAW_CORRECT_SPEED = 9.0
# amount a user is able to offset yaw (in degrees)
YAW_OFFSET_THRESHOLD = 120.0

#pitch offset constants
# The user will be able to offset pitch from the interpolated position at this speed
# this is the speed the user is able to offset pitch at
PITCH_OFFSET_SPEED = 90.0
# this is the speed that the pitch offset corrects itself
# should be less than PITCH_OFFSET_SPEED
PITCH_CORRECT_SPEED = 9.0
# amount a user is able to offset pitch (in degrees)
PITCH_OFFSET_THRESHOLD = 30.0
# our gimbal threshold in the no nudge case
PITCH_OFFSET_NO_NUDGE_THRESHOLD = -90.0


class YawPitchOffsetter():
    # pass in False for handlePitch if you don't want it overriding pitch
    def __init__(self, handlePitch = True):
        self.yawOffset = 0.0
        self.pitchOffset = 0.0
        # 1 is clockwise, -1 is counter clockwise
        self.yawDir = 1
        self.handlePitch = handlePitch
        """
        We default to nudge mode.  In this mode, we only calculate offsets to
        a real yaw/pitch.  We're capped by the above thresholds.
        If this is off, then our yaw/pitch offsets become actual yaw/pitch values
        """
        self.isNudge = True
        self.freeLook = False

    # given RC input, update our pitch/yaw offsets
    # returns whether we changed yaw/pitch offset or not
    def Update(self, channels):
        lastYaw = self.yawOffset
        lastPitch = self.pitchOffset
        self.offsetYaw( channels[3] )

        if self.handlePitch:
            if self.freeLook:
                value = channels[0]
            else:
                if abs(channels[7]) > abs(channels[0]):
                    value = channels[7]
                else:
                    value = channels[0]

            self.offsetPitch( value )

        if lastYaw != self.yawOffset:
            return True
        if lastPitch != self.pitchOffset:
            return True

        return False

    def offsetYaw( self, yawStick ):
        # if stick is centered, return yaw offset to 0.0
        if yawStick == 0.0:
            # only if we're in nudge mode
            if self.isNudge:
                if self.yawOffset > 0.0:
                    self.yawOffset -= YAW_CORRECT_SPEED * UPDATE_TIME
                    if self.yawOffset < 0.0:
                        self.yawOffset = 0.0
                        self.yawDir = -1
                else:
                    self.yawOffset += YAW_CORRECT_SPEED * UPDATE_TIME
                    if self.yawOffset > 0.0:
                        self.yawOffset = 0.0
                        self.yawDir = 1

            return

        self.yawOffset += YAW_OFFSET_SPEED * yawStick * UPDATE_TIME

        if self.isNudge:
            if self.yawOffset > YAW_OFFSET_THRESHOLD:
                self.yawOffset = YAW_OFFSET_THRESHOLD
            elif self.yawOffset < -YAW_OFFSET_THRESHOLD:
                self.yawOffset = -YAW_OFFSET_THRESHOLD
        else:
            # otherwise, the only constraints we have are to keep it in a (0.0, 360.0) range
            if self.yawOffset < 0.0:
                self.yawOffset += 360.0
            elif self.yawOffset > 360.0:
                self.yawOffset -= 360.0

        if yawStick > 0.0:
            self.yawDir = 1
        else:
            self.yawDir = -1

    def offsetPitch( self, gimbalPaddle ):
        # if stick is centered, return pitch offset to 0.0
        if gimbalPaddle == 0.0:
            # only if we're in nudge mode
            if self.isNudge:
                if self.pitchOffset > 0.0:
                    self.pitchOffset -= PITCH_CORRECT_SPEED * UPDATE_TIME
                    if self.pitchOffset < 0.0:
                        self.pitchOffset = 0.0
                else:
                    self.pitchOffset += PITCH_CORRECT_SPEED * UPDATE_TIME
                    if self.pitchOffset > 0.0:
                        self.pitchOffset = 0.0

            return

        self.pitchOffset += PITCH_OFFSET_SPEED * gimbalPaddle * UPDATE_TIME

        if self.isNudge:
            if self.pitchOffset > PITCH_OFFSET_THRESHOLD:
                self.pitchOffset = PITCH_OFFSET_THRESHOLD
            elif self.pitchOffset < -PITCH_OFFSET_THRESHOLD:
                self.pitchOffset = -PITCH_OFFSET_THRESHOLD
        else:
            # In the non nudge case, we have a different set of constraints
            # These are just the gimbal constraints (-90.0, 0.0)
            if self.pitchOffset > 0.0:
                self.pitchOffset = 0.0
            elif self.pitchOffset < PITCH_OFFSET_NO_NUDGE_THRESHOLD:
                self.pitchOffset = PITCH_OFFSET_NO_NUDGE_THRESHOLD


    # This turns on nudge mode.
    # It also clears out yaw/pitch offsets
    def enableNudge(self):
        self.isNudge = True
        self.pitchOffset = 0.0
        self.yawOffset = 0.0

    # This turns off nudge mode,
    # initializing yaw/pitch offsets to the given values
    def disableNudge(self, pitch, yaw):
        self.isNudge = False
        self.pitchOffset = pitch
        self.yawOffset = yaw
