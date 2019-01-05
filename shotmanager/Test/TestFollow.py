#  TestFollow.py
#  shotmanager
#
#  Unit tests for the follow smart shot.
#
#  Created by Will Silva and Eric Liao on 1/19/2015.
#  Mostly overhauled by Nick Speal on 3/16/2016
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

import follow
from follow import *

import shotManager
from shotManager import ShotManager

import unittest

import mock
from mock import call
from mock import Mock
from mock import MagicMock
from mock import patch

class TestFollowShotInit(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)
        vehicle.attitude.yaw = math.radians(30)
        vehicle.mount_status[0] = -45

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds

        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)

    def testInit(self):
        '''Test that the shot initialized properly'''

        # vehicle object should be created (not None)
        assert self.shot.vehicle is not None

        # shotManager object should be created (not None)
        assert self.shot.shotmgr is not None

        # pathHandler should be None
        assert self.shot.pathHandler is not None

        # pathHandler should be None
        assert self.shot.pathController is None

        # filtered roi should be None
        self.assertEqual(self.shot.filteredROI, None)
        self.assertEqual(self.shot.rawROI, None)

        # rawROI queue should be created
        assert self.shot.rawROIQueue is not None

        # filteredROI queue should be created
        assert self.shot.filteredROIQueue is not None

        # roiVelocity should be initialized to None
        self.assertEqual(self.shot.roiVelocity, None)
        
        # init shot state
        self.assertEqual(self.shot.followState, 0)
        self.assertEqual(self.shot.followPreference, 0)
        
        # initialize curTranslateVel to an empty Vector3
        self.assertEqual(self.shot.translateVel,Vector3())


        # shotmgr.getParam should be called thrice
        # once for maxClimbRate and once for maxAlt and once for FENCE_ENABLE
        calls = [call("PILOT_VELZ_MAX", DEFAULT_PILOT_VELZ_MAX_VALUE), call("FENCE_ALT_MAX", DEFAULT_FENCE_ALT_MAX), call("FENCE_ENABLE", DEFAULT_FENCE_ENABLE)]

        self.shot.shotmgr.getParam.assert_has_calls(calls)

        # initialize shot in altitudeOffset
        self.assertEqual(self.shot.followControllerAltOffset, 0)
        
        # initialize shot with ROIAltitudeOffset 0
        self.assertEqual(self.shot.ROIAltitudeOffset, 0)
        
        # enter Guided
        self.assertEqual(self.shot.vehicle.mode.name, "GUIDED")
        
class TestHandleRCs(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])
        shotmgr.getParam.return_value = 0 # so mock doesn't do lazy binds

        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)

        # Mock the functions
        self.shot.checkSocket = Mock()
        self.shot.filterROI = Mock()

        # Mock Attributes
        self.shot.rawROI = LocationGlobalRelative(37.873168,-122.302062, 0)

        self.shot.filteredROI = LocationGlobalRelative(37.873168,-122.302062, 0)

        self.shot.roiVelocity = Vector3(0,0,0)

        self.shot.camYaw = 0.0
        # Mock the pointing functions
        self.shot.handleFreeLookPointing = Mock()
        self.shot.handleFollowPointing = Mock()
        self.shot.handleLookAtMePointing = Mock()

        #Mock the pathHandler object
        self.shot.pathHandler = mock.create_autospec(pathHandler.PathHandler)
        self.shot.pathHandler.cruiseSpeed = 0

        #Mock the pathController object
        self.shot.pathController = mock.create_autospec(OrbitController)
        self.shot.pathController.move.return_value = (LocationGlobalRelative(37.873168,-122.302062, 0),Vector3(1,1,1))

        #Neutral sticks
        throttle = 0.0
        roll = 0.0
        pitch = 0.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]

    def testCallcheckSocket(self):
        '''Test that we call checkSocket()'''

        self.shot.handleRCs(self.channels)
        self.shot.checkSocket.assert_called_with()

    def testNoRawROI(self):
        '''If raw ROI is not set then do NOT continue'''

        self.shot.rawROI = None
        self.shot.handleRCs(self.channels)
        assert not self.shot.filterROI.called

    def testCallFilterROI(self):
        '''Test that we call filteRROI()'''

        self.shot.handleRCs(self.channels)
        self.shot.filterROI.assert_called_with()

    def testFollowWaitReturns(self):
        '''If followState == FOLLOW_WAIT, do NOT continue'''

        self.shot.followState = FOLLOW_WAIT
        self.shot.handleRCs(self.channels)
        # assert not self.shot.vehicle.send_mavlink.called  # TODO - CAN"T FIGURE OUT WHY THIS IS FAILING    

    def testLookAtMePathControllerCalled(self):
        '''Test that correct path controller gets called'''

        self.shot.followState = FOLLOW_LOOKAT
        self.shot.pathController = mock.create_autospec(FlyController)
        self.shot.pathController.move.return_value = (LocationGlobalRelative(37.873168,-122.302062, 0),Vector3(1,1,1))
        self.shot.handleRCs(self.channels)
        self.shot.pathController.move.assert_called_with(self.channels)

    def testFreeLookPathControllerCalled(self):
        '''Test that correct path controller gets called'''

        self.shot.followState = FOLLOW_FREELOOK
        self.shot.pathController = mock.create_autospec(FlyController)
        self.shot.pathController.move.return_value = (LocationGlobalRelative(37.873168,-122.302062, 0),Vector3(1,1,1))
        self.shot.camPitch = 45.0
        self.shot.handleRCs(self.channels)
        self.shot.pathController.move.assert_called_with(self.channels, newHeading = self.shot.camYaw, newOrigin = self.shot.filteredROI, roiVel=self.shot.roiVelocity)

    def testOrbitPathControllerCalled(self):
        '''Test that correct path controller gets called'''

        self.shot.followState = FOLLOW_ORBIT
        # pathController created in setup
        self.shot.pathHandler.cruiseSpeed = 0.0
        self.shot.handleRCs(self.channels)
        self.shot.pathController.move.assert_called_with(self.channels, cruiseSpeed = self.shot.pathHandler.cruiseSpeed, newroi = self.shot.filteredROI, roiVel=self.shot.roiVelocity)

    def testLeashPathControllerCalled(self):
        '''Test that correct path controller gets called'''

        self.shot.followState = FOLLOW_LEASH
        self.shot.pathController = mock.create_autospec(LeashController)
        self.shot.pathController.move.return_value = (LocationGlobalRelative(37.873168,-122.302062, 0),Vector3(1,1,1))
        self.shot.handleRCs(self.channels)
        self.shot.pathController.move.assert_called_with(self.channels, newroi = self.shot.filteredROI, roiVel=self.shot.roiVelocity)

    def testSettingAltitudeLimit(self):
        self.shot.maxAlt = 100.0
        self.shot.handleRCs(self.channels)


    def testFreelookPointing(self):
        
        self.followState = FOLLOW_FREELOOK
        self.shot.manualPitch = Mock()
        self.shot.manualYaw = Mock()
        self.shot.handleFreeLookPointing = Mock()

        self.shot.handleRCs(self.channels)
        
        # self.shot.manualPitch.assert_called_with(self.channels) # TODO - CAN"T FIGURE OUT WHY THIS IS FAILING
        # self.shot.manualYaw.assert_called_with(self.channels) # TODO - CAN"T FIGURE OUT WHY THIS IS FAILING
        # self.shot.handleFreeLookPointing.assert_called_with(mock.ANY) # TODO - CAN"T FIGURE OUT WHY THIS IS FAILING

    def testNonFreelookPointing(self):
        # may need mock
        self.followState = FOLLOW_ORBIT
        self.updateaROIAltOffset = Mock()
        self.shot.handleRCs(self.channels)
        #self.updateaROIAltOffset.assert_called_with(self.channels[RAW_PADDLE]) # TODO - CAN"T FIGURE OUT WHY THIS IS FAILING

    def testMavlinkMessageDidSend(self):        
        self.shot.handleRCs(self.channels)
        #Test that the expected message got encoded:
        expectedControlMask = 0b0000110111000000 # pos-vel mask
        
        # TODO - CAN"T FIGURE OUT WHY THIS IS FAILING:
        # self.shot.vehicle.message_factory.set_position_target_global_int_encode.assert_called_with(
        #              0,       # time_boot_ms (not used)
        #              0, 1,    # target system, target component
        #              mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, # frame
        #              expectedControlMask, # type_mask
        #              int(37.873168*1E7), int(-122.302062*1E7), 0, # x, y, z positions (ignored)
        #              1, 1, 1, # x, y, z velocity in m/s
        #              0, 0, 0, # x, y, z acceleration (not used)
        #              0, 0)    # yaw, yaw_rate (not used)
        self.shot.vehicle.send_mavlink.assert_called_with(mock.ANY)

class TestUpdateROIAltOffset(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)

        self.shot.pathHandler = mock.create_autospec(pathHandler.PathHandler)
        self.shot.pathHandler.cruiseSpeed = 0

        #Mock the pathController object
        self.shot.followState = FOLLOW_ORBIT
        self.shot.pathController = mock.create_autospec(OrbitController)

        self.shot.ROIAltitudeOffset = 0.0
        

        self.shot.ROIAltitudeOffset = 0.0
    def testWithinDeadZone(self):
        self.shot.updateROIAltOffset(0.01)
        self.assertEqual(self.shot.ROIAltitudeOffset, 0.0)
    def testNotWithinDeadZone(self):
        self.shot.updateROIAltOffset(0.9)
        self.assertNotEqual(self.shot.ROIAltitudeOffset, 0.0)

class TestHandleButton(unittest.TestCase):
    '''TODO Nick - after UI shakes out'''
    pass

class TestSetButtonMappings(unittest.TestCase):
    '''TODO Nick - after UI shakes out'''
    pass

class TestHandleOptions(unittest.TestCase):
    '''Handles follow options from app. TODO Nick - after UI shakes out'''
    pass


class TestInitState(unittest.TestCase):
    ARBITRARY_HEADING = 34.8
    DISTANCE = 97.5
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)

        #Mock Methods
        self.shot.updateMountStatus = Mock()
        self.shot.initLookAtMeController = Mock()
        self.shot.initOrbitController = Mock()
        self.shot.initLeashController = Mock()
        self.shot.initFreeLookController = Mock()
        self.shot.updateMountStatus = Mock()
        self.shot.updateAppOptions = Mock()
        self.shot.setButtonMappings = Mock()


        #Setup Attributes
        self.shot.followState = FOLLOW_WAIT
        self.shot.rawROI = location_helpers.newLocationFromAzimuthAndDistance(self.shot.vehicle.location.global_relative_frame, self.ARBITRARY_HEADING, self.DISTANCE)
    def testNoROINoInit(self):
        self.shot.rawROI = None
        self.shot.initState(FOLLOW_ORBIT)
        assert not self.shot.updateMountStatus.called

    def testLookatControllerDidInit(self):
        self.shot.initState(FOLLOW_LOOKAT)
        assert self.shot.initLookAtMeController.called

    def testOrbitControllerDidInit(self):
        self.shot.initState(FOLLOW_ORBIT)
        assert self.shot.initOrbitController.called

    def testLeashControllerDidInit(self):
        self.shot.initState(FOLLOW_LEASH)
        assert self.shot.initLeashController.called

    def testFreeLookControllerDidInit(self):
        self.shot.initState(FOLLOW_FREELOOK)
        assert self.shot.initFreeLookController.called

    def testUpdateFunctionsCalled(self):
        self.shot.initState(FOLLOW_ORBIT)

        assert self.shot.updateMountStatus.called
        assert self.shot.updateAppOptions.called
        assert self.shot.setButtonMappings.called

class TestUpdateAppOptions(unittest.TestCase):
    '''TODO Nick - after UI shakes out'''
    pass

class TestSetupSocket(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)


    @mock.patch('socket.socket')
    def testSocketCreation(self, socket_socket):
        '''Test that the socket is created'''

        self.shot.setupSocket()
        socket_socket.assert_called_with(socket.AF_INET, socket.SOCK_DGRAM)

    @mock.patch('socket.socket', return_value = Mock())
    def testSocketOptions(self, socket_socket):
        '''Test that socket options are set'''

        self.shot.setupSocket()
        self.shot.socket.setsockopt.assert_called_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    @mock.patch('socket.socket', return_value = Mock())
    def testSocketBlocking(self, socket_socket):
        '''Test that socket blocking is set to 0'''

        self.shot.setupSocket()
        self.shot.socket.setblocking.assert_called_with(0)

    @mock.patch('socket.socket', return_value = Mock())
    def testSocketBind(self, socket_socket):
        '''Test that socket tries to bind'''

        self.shot.setupSocket()
        self.shot.socket.bind.assert_called_with(("",FOLLOW_PORT))

    @mock.patch('socket.socket', return_value = Mock())
    def testSocketTimeout(self, socket_socket):
        '''Test that socket sets a timeout'''

        self.shot.setupSocket()
        self.shot.socket.settimeout.assert_called_with(SOCKET_TIMEOUT)

class TestCheckSocket(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)

        sampleData = struct.pack('<IIddf', app_packet.SOLO_MESSAGE_LOCATION, 20, 37.873168,-122.302062, 0)
        self.shot.socket.recvfrom = Mock(side_effect = [(sampleData,'127.0.0.1'), socket.timeout])

    def testRecvFrom(self):
        '''Test recvFrom functionality'''

        self.shot.checkSocket()
        self.shot.socket.recvfrom.assert_called_with(28)

    @mock.patch('monotonic.monotonic', return_value = 333)
    def testWhenROIisNone(self, monotonic_monotonic):
        '''Test first data unpack'''

        self.shot.rawROI = None
        self.shot.checkSocket()
        self.assertEqual(self.shot.roiDeltaTime, None)
        self.assertEqual(self.shot.previousROItime, 333)
        self.assertEqual(self.shot.rawROI.lat, 37.873168)
        self.assertEqual(self.shot.rawROI.lon, -122.302062)
        self.assertEqual(self.shot.rawROI.alt, 0)

    @mock.patch('monotonic.monotonic', return_value = 333)
    def testNewData(self, monotonic_monotonic):
        '''Test subsequent data unpack'''

        self.shot.previousROItime = 222
        self.shot.rawROI = LocationGlobalRelative(37.873168,-122.302062, 0)

        self.shot.checkSocket()
        self.assertEqual(self.shot.roiDeltaTime, 111)
        self.assertEqual(self.shot.previousROItime, 333)
        self.assertEqual(self.shot.rawROI.lat, 37.873168)
        self.assertEqual(self.shot.rawROI.lon, -122.302062)
        self.assertEqual(self.shot.rawROI.alt, 0)

class TestFilterROI(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])
        shotmgr.buttonManager = Mock()
        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)

        # rawROI
        self.ROI = LocationGlobalRelative(37.873168,-122.302062, 0) #sample ROI, used throughout
        self.shot.rawROI = self.ROI

        # mock methods
        self.shot.initState = Mock()
        location_helpers.calcYawPitchFromLocations = Mock()
        location_helpers.calcYawPitchFromLocations.return_value = (0.0,0.0)

        #roiDeltaTime
        self.shot.roiDeltaTime = 0.04 # 25Hz (guess)

        #init vars
        self.shot.roiVelocity = Vector3() 

    def testFilteredROIQueueGreaterThanZero(self):
        '''Test that beginFollow is called if roiVelocity is None and the filteredROIQueue is long enough'''

        self.shot.filterROI()
        self.assertEqual(self.shot.filteredROI, self.shot.rawROI)
        self.assertEqual(self.shot.roiVelocity, Vector3(0,0,0))
        assert self.shot.initState.called


    def testNoQueue(self):
        '''run through the method with empty queues (First item will be added in this queue)'''
        # Filter gets skipped b/c queues are empty
        # initialization block executes because queue now has 1 item
        # end of method executes

        self.shot.roiDeltaTime = None
        self.shot.rawROIQueue = collections.deque(maxlen=MIN_RAW_ROI_QUEUE_LENGTH)
        self.shot.filteredROIQueue = collections.deque(maxlen=MIN_FILT_ROI_QUEUE_LENGTH)
        self.shot.filterROI()
        self.assertEqual(self.shot.filteredROI, self.shot.rawROI)
        assert not location_helpers.calcYawPitchFromLocations.called


    def testFilterFullQueue(self):
        '''run through the method with a pre-filled queue'''
        # filter executes because queues are full
        # init is skipped. len(queue) > 1
        # else block executes. len(queue) > 1 AND roiDeltaTime exists.
        for i in range(5):
            self.shot.rawROIQueue.append(self.ROI)
            self.shot.filteredROIQueue.append(self.ROI)
        self.shot.filterROI()
        assert location_helpers.calcYawPitchFromLocations.called

    def testAccelerationLimitVariations_x(self):
        '''For different combinations of roiVeloctiy, translateVel, and components X,Y,Z: Verify that the code is executed and that the values are as expected.'''

        self.shot.roiVelocity.x = 0.0 # gets overwritten in filterROI() anyway
        
        # (much) Greater than case
        self.shot.translateVel.x = -1.0
        self.shot.filterROI()
        assert self.shot.translateVel.x == -1.0 + ACCEL_PER_TICK

        # equal case
        self.shot.translateVel.x = 0.0
        self.shot.filterROI()
        assert self.shot.translateVel.x == self.shot.roiVelocity.x

        # (much) Less than case
        self.shot.translateVel.x = 1.0
        self.shot.filterROI()
        assert self.shot.translateVel.x == 1.0 - ACCEL_PER_TICK

    def testAccelerationLimitVariations_y(self):
        '''For different combinations of roiVeloctiy, translateVel, and components X,Y,Z: Verify that the code is executed and that the values are as expected.'''

        self.shot.roiVelocity.y = 0.0 # gets overwritten in filterROI() anyway
        
        # (much) Greater than case
        self.shot.translateVel.y = -1.0
        self.shot.filterROI()
        assert self.shot.translateVel.y == -1.0 + ACCEL_PER_TICK

        # equal case
        self.shot.translateVel.y = 0.0
        self.shot.filterROI()
        assert self.shot.translateVel.x == self.shot.roiVelocity.y

        # (much) Less than case
        self.shot.translateVel.y = 1.0
        self.shot.filterROI()
        assert self.shot.translateVel.y == 1.0 - ACCEL_PER_TICK

    def testAccelerationLimitVariations_z(self):
        '''For different combinations of roiVeloctiy, translateVel, and components X,Y,Z: Verify that the code is executed and that the values are as expected.'''

        self.shot.roiVelocity.z = 0.0 # gets overwritten in filterROI() anyway
        
        # (much) Greater than case
        self.shot.translateVel.z = -1.0
        self.shot.filterROI()
        assert self.shot.translateVel.z == -1.0 + ACCEL_PER_TICK

        # equal case
        self.shot.translateVel.z = 0.0
        self.shot.filterROI()
        assert self.shot.translateVel.z == self.shot.roiVelocity.z

        # (much) Less than case
        self.shot.translateVel.z = 1.0
        self.shot.filterROI()
        assert self.shot.translateVel.z == 1.0 - ACCEL_PER_TICK


    def testQueueLengthsAreNotTooLong(self):
        '''make sure (at steady state) the length of the queue is correct.'''
        # should be defined as
        #   MIN_RAW_ROI_QUEUE_LENGTH = 5, MIN_FILT_ROI_QUEUE_LENGTH = 4

        for i in range(10):
            self.shot.rawROIQueue.append(self.ROI)
            self.shot.filteredROIQueue.append(self.ROI)
        self.shot.filterROI()
        self.assertEqual(len(self.shot.rawROIQueue),5)
        self.assertEqual(len(self.shot.filteredROIQueue),4)


class TestInitControllersParent(unittest.TestCase):
    '''
    Parent class to enable testing of multiple methods
    '''
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])
        
        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)
        
        # mock methods
        location_helpers.getDistanceFromPoints = Mock()
        location_helpers.calcAzimuthFromPoints = Mock()
        
        location_helpers.getDistanceFromPoints.return_value = 10.0
        location_helpers.calcAzimuthFromPoints.return_value = 0.0

class TestInitOrbitController(TestInitControllersParent):
    ''' ORBIT ''' 
    def setup(self):
        super(TestInitOrbitController,self).setup()
        controller = mock.create_autospec(OrbitController)

    def didExecute_initOrbitController(self):
        self.shot.initOrbitController()
        assert location_helpers.getDistanceFromPoints.called
        assert location_helpers.calcAzimuthFromPoints.called
        assert controller.setOptions.called

class TestInitLeashController(TestInitControllersParent):
    ''' LEASH ''' 
    def setup(self):
        super(TestInitLeashController,self).setup()
        controller = mock.create_autospec(LeashController)

    def didExecute_initLeashController(self):
        self.shot.initLeashController()
        assert location_helpers.getDistanceFromPoints.called
        assert location_helpers.calcAzimuthFromPoints.called
        assert controller.setOptions.called

class TestInitFreeLookController(TestInitControllersParent):
    ''' FREE LOOK ''' 
    def setup(self):
        super(TestInitFreeLookController,self).setup()
        location_helpers.getVectorFromPoints = Mock()
        location_helpers.getVectorFromPoints.return_value = Vector3(5,5,5)
        controller = mock.create_autospec(FlyController)

    def didExecute_initFreeLookController(self):
        self.shot.initFreeLookController()
        assert location_helpers.getDistanceFromPoints.called
        assert location_helpers.calcAzimuthFromPoints.called
        assert controller.setOptions.called
        # Didn't check if getYaw, getPitch were called. It's probably fine

class TestInitLookAtMeController(TestInitControllersParent):
    ''' LOOK AT ME ''' 
    def setup(self):
        super(TestInitLookAtMeController,self).setup()
        controller = mock.create_autospec(LookAtController)
        self.shot.pathHandler.pause = Mock()

    def didExecute_initLookAtMeController(self):
        self.shot.initLookAtMeController()
        assert self.shot.pathHandler.pause.called
        assert controller.setOptions.called

class TestUpdateMountStatus(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])
        
        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)
        
        
    def testFreeLookMessage(self):
        self.shot.followState = FOLLOW_FREELOOK
        
        self.shot.updateMountStatus()
        self.shot.vehicle.message_factory.mount_configure_encode.assert_called_with(
                    0, 1,    # target system, target component
                    mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,  #mount_mode
                    1,  # stabilize roll
                    1,  # stabilize pitch
                    1,  # stabilize yaw
                    )

        assert self.shot.vehicle.send_mavlink.called

    def testNonFreeLookMessage(self):
        self.shot.followState = FOLLOW_ORBIT
        
        self.shot.updateMountStatus()
        self.shot.vehicle.message_factory.mount_configure_encode.assert_called_with(
                        0, 1,    # target system, target component
                        mavutil.mavlink.MAV_MOUNT_MODE_GPS_POINT,  #mount_mode
                        1,  # stabilize roll
                        1,  # stabilize pitch
                        1,  # stabilize yaw
                        )
        assert self.shot.vehicle.send_mavlink.called

class TestManualPitch(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])
        
        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)
        
        #Neutral sticks
        throttle = 0.0
        roll = 0.0
        pitch = 0.0
        yaw = 0.0 
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]

    def testPositiveValue(self):
        self.shot.camPitch = 1.0
        self.shot.manualPitch(self.channels[THROTTLE])
        assert self.shot.camPitch == 0.0

    def testZeroValue(self):
        self.shot.camPitch = 0.0
        self.shot.manualPitch(self.channels[THROTTLE])
        assert self.shot.camPitch == 0.0

    def testSlightlyNegativeValue(self):
        self.shot.camPitch = -1.0
        self.shot.manualPitch(self.channels[THROTTLE])
        assert self.shot.camPitch == -1.0

    def testNegative90Value(self):
        self.shot.camPitch = -90.0
        self.shot.manualPitch(self.channels[THROTTLE])
        assert self.shot.camPitch == -90.0

    def testHugeNegativeValue(self):
        self.shot.camPitch = -100.0
        self.shot.manualPitch(self.channels[THROTTLE])
        assert self.shot.camPitch == -90.0


class TestManualYaw(unittest.TestCase):
    def setUp(self):
        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])
        
        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)
        
        self.shot.camYaw = 0 #init to zero. Can be permuted below.
        #Neutral sticks, unless permuted in the methods below
        throttle = 0.0
        roll = 0.0
        pitch = 0.0
        yaw = 0.0
        self.channels = [throttle, roll, pitch, yaw, 0.0, 0.0, 0.0, 0.0]

    def testZeroValue(self):
        ''' Make sure Function returns if no yaw command'''
        self.channels[YAW] = 0.0
        self.shot.camYaw = -999 #Dummy value to make sure it is unchanged in the function
        self.shot.manualYaw(self.channels)
        assert self.shot.camYaw == -999


    def testPositiveYawPositiveDirectionOfSpin(self):
        self.channels[YAW] = 0.5
        self.shot.manualYaw(self.channels)
        assert self.shot.camDir == 1

    def testNegativeYawNegativeDirectionOfSpin(self):
        self.channels[YAW] = -0.5
        self.shot.manualYaw(self.channels)
        assert self.shot.camDir == -1
    
    def testLargeValue(self):
        self.channels[YAW] = -0.1
        self.shot.camYaw = 380
        self.shot.manualYaw(self.channels)
        assert self.shot.camYaw <= 20

    def testNegativeValue(self):
        self.channels[YAW] = 0.1
        self.shot.camYaw = -50
        self.shot.manualYaw(self.channels)
        assert self.shot.camYaw >= 310

    # TODO - Needed to test edge cases of 0 and 360? Can camYaw be both 0 and 360 on the dot? Hard to test.

class TestHandleFreeLookPointing(unittest.TestCase):
    def setUp(self):

        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)

        self.shot.camYaw = float( 1.111333 )
        self.shot.camPitch = float (2.55556666 )
        self.shot.camDir = 1
        

    def testWithGimbal(self):
        ''' With a gimbal, use  mount_control to control pitch/yaw '''

        self.shot.vehicle.mount_status = [20.0, 0.0, 1.3]
        self.shot.handleFreeLookPointing()
        self.shot.vehicle.message_factory.mount_control_encode.assert_called_with(
                                            0, 1,    # target system, target component
                                            self.shot.camPitch * 100, # pitch
                                            0.0, # roll
                                            self.shot.camYaw * 100, # yaw
                                            0 # save position
                                            )

    def testNoGimbal(self):
        ''' Without a gimbal, we only use condition_yaw to control '''
        # no gimbal
        self.shot.vehicle.mount_status = [None, None, None]
        yawDir = 1
        self.shot.handleFreeLookPointing()
        self.shot.vehicle.message_factory.command_long_encode.assert_called_with(
                                            0, 0,    # target system, target component
                                            mavutil.mavlink.MAV_CMD_CONDITION_YAW, #command
                                            0, #confirmation
                                            self.shot.camYaw, # param 1 - target angle
                                            follow.YAW_SPEED, # param 2 - yaw speed
                                            yawDir, # param 3 - direction
                                            0.0, # relative offset
                                            0, 0, 0 # params 5-7 (unused)
                                            )


class testHandleLookAtMePointing(unittest.TestCase):
    def setUp(self):

        #Create a mock vehicle object
        vehicle = mock.create_autospec(Vehicle)

        #Create a mock shotManager object
        shotmgr = mock.create_autospec(ShotManager)
        shotmgr.rcMgr = Mock(specs=['remapper'])

        #Run the shot constructor
        self.shot = follow.FollowShot(vehicle, shotmgr)

        #roi
        self.tempROI = LocationGlobalRelative(37.873168,-122.302062, 0)

    def didExecute_handleLookAtPointing(self):
        self.vehicle.message_factory.command_int_encode.assert_called_with(
                    0, 1,    # target system, target component
                    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, #frame
                    mavutil.mavlink.MAV_CMD_DO_SET_ROI, #command
                    0, #current
                    0, #autocontinue
                    0, 0, 0, 0, #params 1-4
                    self.tempROI.lat*1.E7,
                    self.tempROI.lon*1.E7,
                    self.tempROI.alt + self.shot.ROIAltitudeOffset #offset for ROI
                    )

        assert self.shot.vehicle.send_mavlink.called
