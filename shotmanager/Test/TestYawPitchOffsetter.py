# Unit tests for yawPitchOffsetter
import mock
from mock import Mock
import os
from os import sys, path
import struct
import unittest

sys.path.append(os.path.realpath('..'))
from shotManagerConstants import *
import yawPitchOffsetter

class TestInit(unittest.TestCase):
    def testInit(self):
        """ test initial variables """
        setter = yawPitchOffsetter.YawPitchOffsetter()
        self.assertEquals( setter.yawOffset, 0.0 )
        self.assertEquals( setter.pitchOffset, 0.0 )
        self.assertTrue( setter.handlePitch )
        self.assertTrue( setter.isNudge )

    def testNoHandlePitch(self):
        """ Test if we set handlePitch to False """
        setter = yawPitchOffsetter.YawPitchOffsetter(False)
        self.assertFalse( setter.handlePitch )

class TestUpdate(unittest.TestCase):
    def setUp(self):
        self.setter = yawPitchOffsetter.YawPitchOffsetter()
        self.setter.offsetYaw = Mock()
        self.setter.offsetPitch = Mock()

    def testChan3ToYaw(self):
        """ Channel 3 is used to offset yaw """
        channels = [0.0, 1.0, 0.0, 0.3, 0.0, 0.0, 0.0, 0.0]
        self.setter.Update( channels )
        self.setter.offsetYaw.assert_called_with( 0.3 )

    def testChan7Pitch(self):
        """ When abs(chan7) > abs (chan0) it's used for pitch """
        channels = [0.3, 1.0, 0.0, 0.3, 0.0, 0.0, 0.0, -0.8]
        self.setter.Update( channels )
        self.setter.offsetPitch.assert_called_with( -0.8 )

    def testChan0Pitch(self):
        """ When abs(chan0) > abs (chan7) it's used for pitch """
        channels = [0.38, 1.0, 0.0, 0.3, 0.0, 0.0, 0.0, -0.142]
        self.setter.Update( channels )
        self.setter.offsetPitch.assert_called_with( 0.38 )

    def testUpdateNoChange(self):
        """ Update should return false if neither yawOffset nor pitchOffset change """
        channels = [0.38, 1.0, 0.0, 0.3, 0.0, 0.0, 0.0, -0.142]
        result = self.setter.Update( channels )
        self.assertFalse( result )

    def testUpdateYawChange(self):
        """ Update should return true if yawOffset changes """
        def alter(a):
            self.setter.yawOffset = 20.0

        channels = [0.38, 1.0, 0.0, 0.3, 0.0, 0.0, 0.0, -0.142]
        self.setter.offsetYaw = Mock(side_effect = alter )
        result = self.setter.Update( channels )
        self.assertTrue( result )

    def testUpdatePitchChange(self):
        """ Update should return true if pitchOffset changes """
        def alter(a):
            self.setter.pitchOffset = 20.0

        channels = [0.38, 1.0, 0.0, 0.3, 0.0, 0.0, 0.0, -0.142]
        self.setter.offsetPitch = Mock(side_effect = alter )
        result = self.setter.Update( channels )
        self.assertTrue( result )

class TestOffsetYaw(unittest.TestCase):
    def setUp(self):
        self.setter = yawPitchOffsetter.YawPitchOffsetter()

    def testOffsetYawOnce(self):
        """ offset yaw once """
        self.setter.offsetYaw( 0.5 )
        self.assertEquals( self.setter.yawOffset, 0.5 * yawPitchOffsetter.YAW_OFFSET_SPEED * UPDATE_TIME )

    def testOffsetYawNeg10x(self):
        """ offset yaw 10 x in the negative direction """
        startYaw = 20.2
        self.setter.yawOffset = startYaw
        for i in range(10):
            self.setter.offsetYaw( -0.3 )
            startYaw -= 0.3 * yawPitchOffsetter.YAW_OFFSET_SPEED * UPDATE_TIME
        self.assertEquals( self.setter.yawOffset, startYaw )
        self.assertEquals( self.setter.yawDir, -1 )

    def testReturnToZero(self):
        """ Eventually this yawOffset should return to zero """
        self.setter.yawOffset = 80.5
        for i in range(1000):
            self.setter.offsetYaw( 0.00 )
        self.assertEquals( self.setter.yawOffset, 0.0 )
        self.assertEquals( self.setter.yawDir, 1 )

    def testNoReturnToZero(self):
        """ If nudge mode is off we do not return to zero """
        self.setter.yawOffset = 30.5
        self.setter.isNudge = False
        for i in range(100):
            self.setter.offsetYaw( 0.0 )
        self.assertEquals( self.setter.yawOffset, 30.5 )

    def testYawBounds(self):
        """ Should not go past YAW_OFFSET_THRESHOLD """
        self.setter.yawOffset = -59.5
        for i in range(1000):
            self.setter.offsetYaw( -1.0 )
        self.assertEquals( self.setter.yawOffset, -yawPitchOffsetter.YAW_OFFSET_THRESHOLD )

    def testNoYawBounds(self):
        """ In non-nudge mode, we are unconstrained, except for keeping things in the (0, 360) range """
        startYaw = 18.546584
        self.setter.yawOffset = startYaw
        self.setter.isNudge = False
        for i in range(1000):
            self.setter.offsetYaw( -0.8 )
            startYaw -= 0.8 * yawPitchOffsetter.YAW_OFFSET_SPEED * UPDATE_TIME
            if startYaw < 0.0:
                startYaw += 360.0
        self.assertEquals( self.setter.yawOffset, startYaw )

class TestOffsetPitch(unittest.TestCase):
    def setUp(self):
        self.setter = yawPitchOffsetter.YawPitchOffsetter()

    def testOffsetPitchOnce(self):
        """ offset pitch once """
        self.setter.offsetPitch( 0.22 )
        self.assertEquals( self.setter.pitchOffset, 0.22 * yawPitchOffsetter.PITCH_OFFSET_SPEED * UPDATE_TIME )

    def testOffsetPitchNeg10x(self):
        """ offset pitch 12 x  """
        startPitch = 2.8
        self.setter.pitchOffset = startPitch
        for i in range(10):
            self.setter.offsetPitch( 0.6 )
            startPitch += 0.6 * yawPitchOffsetter.PITCH_OFFSET_SPEED * UPDATE_TIME
        self.assertEquals( self.setter.pitchOffset, startPitch )

    def testReturnToZero(self):
        """ Eventually this pitchOffset should return to zero """
        self.setter.pitchOffset = -26.8
        for i in range(1000):
            self.setter.offsetPitch( 0.02 )
        self.assertEquals( self.setter.yawOffset, 0.0 )

    def testNoReturnToZero(self):
        """ With nudging off, we do not return to zero """
        self.setter.isNudge = False
        self.setter.pitchOffset = -33.333
        for i in range(100):
            self.setter.offsetPitch( 0.0 )
        self.assertEquals( self.setter.pitchOffset, -33.333 )

    def testPitchBounds(self):
        """Should not go past negative PITCH_OFFSET_THRESHOLD """
        self.setter.pitchOffset = -19.5
        for i in range(1000):
            self.setter.offsetPitch( -1.0 )
        self.assertEquals( self.setter.pitchOffset, -yawPitchOffsetter.PITCH_OFFSET_THRESHOLD )

    def testNoNudgePitchBounds(self):
        """ With nudge off, we have different constraints """
        self.setter.pitchOffset = -19.645
        self.setter.isNudge = False
        for i in range(1000):
            self.setter.offsetPitch( 1.0 )
        self.assertEquals( self.setter.pitchOffset, 0.0 )

    def testNoNudgePitchBoundsNegative(self):
        """ With nudge off, our constraint is PITCH_OFFSET_NO_NUDGE_THRESHOLD (-90) """
        self.setter.pitchOffset = -19.5
        self.setter.isNudge = False
        for i in range(1000):
            self.setter.offsetPitch( -1.0 )
        self.assertEquals( self.setter.pitchOffset, yawPitchOffsetter.PITCH_OFFSET_NO_NUDGE_THRESHOLD )

class TestEnableNudge(unittest.TestCase):
    def testEnableNudge(self):
        """ test that EnableNudge sets isNudge and clears out yaw/pitch offsets """
        setter = yawPitchOffsetter.YawPitchOffsetter()
        setter.isNudge = False
        setter.yawOffset = -17.9
        setter.pitchOffset = 28.9
        setter.enableNudge()
        self.assertTrue(setter.isNudge)
        self.assertEquals(setter.yawOffset, 0.0)
        self.assertEquals(setter.pitchOffset, 0.0)

class TestDisableNudge(unittest.TestCase):
    def testDisableNudge(self):
        """ test that DisableNudge sets isNudge to false and initializes yaw/pitch offsets """
        setter = yawPitchOffsetter.YawPitchOffsetter()
        setter.isNudge = True
        setter.yawOffset = -17.9
        setter.pitchOffset = 28.9
        setter.disableNudge( -13.444, 87.56 )
        self.assertFalse(setter.isNudge)
        self.assertEquals(setter.pitchOffset, -13.444)
        self.assertEquals(setter.yawOffset, 87.56)
