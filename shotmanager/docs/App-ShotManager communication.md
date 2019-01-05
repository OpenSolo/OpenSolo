# App-ShotManager Communication

This document details App-Sololink communication for use in the Sololink behaviors.

  - [Setup](#setup)
  - [Shot Flows](#shot-flows)
    - [Multipoint cable cam](#multipoint-cable-cam)
        - [Record Mode](#record-mode)
        - [Play Mode](#play-mode)
        - [Definition of a Path](#definition-of-a-path)
    - [Selfie](#selfie)
    - [Orbit](#orbit)
    - [Follow](#follow)
    - [Cable cam (legacy)](#cable-cam-legacy)
    - [Button mapping](#button-mapping)
  - [Protocol](#protocol)
  - [Message definitions](#message-definitions)
    - [General messages](#general-messages)
      - [SOLO_MESSAGE_GET_CURRENT_SHOT](#solo_message_get_current_shot)
      - [SOLO_MESSAGE_SET_CURRENT_SHOT](#solo_message_set_current_shot)
      - [SOLO_MESSAGE_LOCATION](#solo_message_location)
      - [SOLO_MESSAGE_RECORD_POSITION](#solo_message_record_position)
      - [SOLO_CABLE_CAM_OPTIONS](#solo_cable_cam_options)
      - [SOLO_GET_BUTTON_SETTING](#solo_get_button_setting)
      - [SOLO_SET_BUTTON_SETTING](#solo_set_button_setting)
      - [SOLO_PAUSE](#solo_pause)
      - [SOLO_FOLLOW_OPTIONS](#solo_follow_options)
      - [SOLO_SHOT_OPTIONS](#solo_shot_options)
      - [SOLO_SHOT_ERROR](#solo_shot_error)
      - [SOLO_MESSAGE_SHOTMANAGER_ERROR](#solo_message_shotmanager_error)
      - [SOLO_CABLE_CAM_WAYPOINT](#solo_cable_cam_waypoint)
      - [SOLO_SECOND_PHONE_NOTIFICATION](#solo_second_phone_notification)
      - [SOLO_ZIPLINE_OPTIONS](#solo_zipline_options)
      - [SOLO_PANO_OPTIONS](#solo_pano_options)
    - [Multipoint cable cam (SOLO_SPLINE_) messages](#multipoint-cable-cam-solo_spline_-messages)
      - [SOLO_SPLINE_RECORD](#solo_spline_record)
      - [SOLO_SPLINE_PLAY](#solo_spline_play)
      - [SOLO_SPLINE_POINT](#solo_spline_point)
      - [SOLO_SPLINE_ATTACH](#solo_spline_attach)
      - [SOLO_SPLINE_SEEK](#solo_spline_seek)
      - [SOLO_SPLINE_PLAYBACK_STATUS](#solo_spline_playback_status)
      - [SOLO_SPLINE_PATH_SETTINGS](#solo_spline_path_settings)
      - [SOLO_SPLINE_DURATIONS](#solo_spline_durations)
    - [GoPro messages](#gopro-messages)
      - [GOPRO_SET_ENABLED](#gopro_set_enabled)
      - [GOPRO_SET_REQUEST](#gopro_set_request)
      - [GOPRO_RECORD](#gopro_record)
      - [GOPRO_STATE](#gopro_state)
      - [GOPRO_REQUEST_STATE](#gopro_request_state)
      - [GOPRO_SET_EXTENDED_REQUEST](#gopro_set_extended_request)
    - [GeoFence messages](#geofence-messages)
      - [GEOFENCE_SET_DATA](#geofence_set_data)
      - [GEOFENCE_SET_ACK](#geofence_set_ack)
      - [GEOFENCE_UPDATE_POLY](#geofence_update_poly)
      - [GEOFENCE_CLEAR](#geofence_clear)
      - [GEOFENCE_ACTIVATED](#geofence_activated)
    - [Site Scan Inspect (SOLO_INSPECT_) messages](#site-scan-inspect_-messages)
      - [SOLO_INSPECT_START](#solo_inspect_start)
      - [SOLO_INSPECT_SET_WAYPOINT](#solo_inspect_set_waypoint)
      - [SOLO_INSPECT_MOVE_GIMBAL](#solo_inspect_move_gimbal)
      - [SOLO_INSPECT_MOVE_VEHICLE](#solo_inspect_move_vehicle)
    - [Site Scan Scan (SOLO_SCAN_) messages](#site-scan-scan_-messages)
      - [SOLO_SCAN_START](#solo_scan_start)
    - [Site Scan Survey (SOLO_SURVEY_) messages](#site-scan-survey_-messages)
      - [SOLO_SURVEY_START](#solo_survey_start)



## Setup

*ShotManager* is the process that runs on Sololink that handles behaviors.

App-ShotManager communication happens over TCP on port 5507.




## Shot Flows

### Multipoint cable cam

The *Multipoint Cable Cam* shot allows the copter to fly a [Path](#definition-of-a-path) described by a spline.

There are two modes:  Record and Play

* In Record mode, *ShotManager* collects and assembles Keypoints into a Path.
* In Play mode, *ShotManager* controls the copter to fly along the Path defined in Record mode.

##### Record Mode

* When *ShotManager* enters Record mode, it clears the existing [Path](definition-of-a-path) (if there is one) and starts a new one.
* *ShotManager* attempts to create a new Keypoint when:

    * It receives a button press from Artoo
    * It receives [SOLO_MESSAGE_RECORD_POSITION](#solo_message_record_position) from the app
    * It receives [SOLO_SPLINE_POINT](#solo_spline_point) from the app

* After creating a Keypoint, *ShotManager* sends [SOLO_SPLINE_POINT](#solo_spline_point) to the app.
* It's possible for Keypoint creation to fail.

* *ShotManager* can coalesce multiple recording requests into a smaller number of Keypoints (i.e. to remove duplicates);  however, it must respond with exactly one [SOLO_SPLINE_POINT](#solo_spline_point) message for each [SOLO_SPLINE_POINT](#solo_spline_point) or [SOLO_MESSAGE_RECORD_POSITION](#solo_message_record_position) message it receives from the app. This is to provide an ACK mechanism.

##### Play Mode

* *ShotManager* enters Play mode:

    * In response to an Artooo button press.
    * When it receives a [SOLO_SPLINE_PLAY](#solo_spline_play) message from the app.

* *ShotManager* will only enter Play mode after a valid Path has been constructed in Record mode.
* When *ShotManager* enters Play mode, it sends all Keypoints on the current Path to the app using [SOLO_SPLINE_POINT](#solo_spline_point) messages
* The vehicle doesn't fly or snap to the path until it receives a message from the app
* The app sends a [SOLO_SPLINE_ATTACH](#solo_spline_attach) message to tell *ShotManager* to fly to the Path and await further commands.
* Once attached, the app uses the [SOLO_SPLINE_SEEK](#solo_spline_seek) message to tell *ShotManager* to fly the path.
* As the vehicle is flying, *ShotManager* sends [SOLO_SPLINE_PLAYBACK_STATUS](#solo_spline_playback_status) messages to the allow the app to visualize Solo’s location on the flight path.

##### Definition of a Path

* A Path is an ordered collection of Keypoints.
* Path indices are unique.
* Valid Keypoints are constructed only by *ShotManager*;  the validity of Keypoints must be confirmed by *ShotManager* if created or re-loaded by the app.

* A Path is valid if and only if:
    * It contains at least two Keypoints.
    * All its Keypoints are valid.
    * The indices of its Keypoints form a complete set;  that is, a path with *n* Keypoints contains a Keypoint with each of the indices *0..n-1*.

* Index 0 is the beginning of the Path. Index *n* is the end of the Path.
* When Path positions are expressed parametrically, index 0 corresponds to a parametric value of 0.0;  index *n* corresponds to a parametric value of 1.0.

Path Equivalence -- **TBD**

Camera Direction -- **TBD**

The direction in which the camera points with respect to the Path is *ShotManager* implementation-specific. Eventually, this API will provide options to control this;  it is currently undefined.


### Selfie

Selfie is much simpler than cable cam.

The flow must be initiated by the app via a [SOLO_MESSAGE_SET_CURRENT_SHOT](#solo_message_set_current_shot). *ShotManager* then expects 3 locations sent using [SOLO_MESSAGE_LOCATION](#solo_message_location). They are:

* 1st selfie waypoint (near point)
* 2nd selfie waypoint (far point)
* Selfie ROI point

Upon receiving these 3 points, *ShotManager* will put Solo into guided mode and the selfie will automatically start. It’s controllable and pausable just like cable cam though.

Locations cannot be changed after they are received. Instead, stop and start a new selfie.

User can press ‘FLY’ to exit as in cable cam.



### Orbit

Either the app can request that orbit starts (via [SOLO_MESSAGE_SET_CURRENT_SHOT](#solo_message_set_current_shot)) or the user can initiate from Artoo, in which case *ShotManager* will tell the app via a [SOLO_MESSAGE_GET_CURRENT_SHOT](#solo_message_get_current_shot). This only works if an app is connected to *ShotManager*.

To proceed, the user needs to lock onto a spot. This can be done in 2 ways:

* Press ‘A’ on Artoo. Orbit will record its current ROI.
* Drag/move the map until the orbit point on the map aligns with the desired orbit ROI,and then select either the app banner or ‘A’ on Artoo. This will send a [SOLO_MESSAGE_LOCATION](#solo_message_location) to *ShotManager*, which will be the ROI.

In any case, if an initial ROI is set for Orbit, it will send this location back to the app via a [SOLO_MESSAGE_LOCATION](#solo_message_location) message.

At any point, if the user hits ‘FLY’, it will exit orbit and *ShotManager* will send a [SOLO_MESSAGE_GET_CURRENT_SHOT](#solo_message_get_current_shot) with -1 to the app.

The app can send [SOLO_SHOT_OPTIONS](#solo_shot_options) to *ShotManager* to change cruise speed. If the user hits the "Pause" button on Artoo, *ShotManager* will adjust cruiseSpeed to 0.0 and send [SOLO_SHOT_OPTIONS](#solo_shot_options) to the app. Hitting “pause” again will set cruiseSpeed to the original speed and send it to the app.

When an initial ROI is set, *ShotManager* will set Solo to Guided and the copter will be in orbit mode.

During orbit mode, the app can send a [SOLO_MESSAGE_LOCATION](#solo_message_location) to update the ROI location and begin a new orbit around the new ROI. Note this differs from Follow mode, which sends new points but does not reset the orbit.

Prior to the ROI being set, the app should show on the app the projected ROI of orbit. This is not passed from *ShotManager* to the app, so the app should calculate it. This calculation works as follows:  

```python
if camera.getPitch(self.vehicle) > SHALLOW_ANGLE_THRESHOLD (-60):
    loc = location_helpers.newLocationFromAzimuthAndDistance(self.vehicle.location, camera.getYaw(self.vehicle), FAILED_ROI_DISTANCE  (20.0))
else:
    loc = roi.CalcCurrentROI(self.vehicle)
```

Buttons for cruising work as they do in cable cam.


### Follow

Follow is a special case of orbit. It works the same way except instead of setting or locking onto an roi, it uses the phone’s GPS. In order to do this, it needs to connect to a udp port on *ShotManager*.

First the app should tell *ShotManager* to enter the Follow shot via [SOLO_MESSAGE_SET_CURRENT_SHOT](#solo_message_set_current_shot). Follow is not enterable via Artoo.

Then the app should begin to stream positions in [SOLO_MESSAGE_LOCATION](#solo_message_location) packets to *ShotManager* on port 14558. It should stream locations at 25 Hz, because that is the update loop rate of *ShotManager*. 

Buttons for cruising work as they do in cable cam.

### Cable cam (legacy)

Either the app can request that cable cam starts (via [SOLO_MESSAGE_SET_CURRENT_SHOT](#solo_message_set_current_shot)) or the user can initiate from Artoo, in which case *ShotManager* will tell the app via a [SOLO_MESSAGE_GET_CURRENT_SHOT](#solo_message_get_current_shot). This only works if an app is connected to *ShotManager*.

To proceed, the user needs to record two locations.

The app can tell *ShotManager* to record a point using [SOLO_MESSAGE_RECORD_POSITION](#solo_message_record_position), but it should always wait to receive a [SOLO_CABLE_CAM_WAYPOINT](#solo_cable_cam_waypoint) before proceeding.

Otherwise, a user can Press ‘A’ to record a point on Artoo.

If a user tries to record two points on top of each other, the second one overwrites the first. To inform the app, *ShotManager* will send a [SOLO_MESSAGE_GET_CURRENT_SHOT](#solo_message_get_current_shot) with -1 as a shot which should tell the app to exit cable cam, then a [SOLO_MESSAGE_GET_CURRENT_SHOT](#solo_message_get_current_shot) with 2 to reenter cable cam, and then a [SOLO_CABLE_CAM_WAYPOINT](#solo_cable_cam_waypoint) to reflect the new starting point of the cable.

At any point, if the user hits ‘FLY’, it will exit cable cam and *ShotManager* will send a [SOLO_MESSAGE_GET_CURRENT_SHOT](#solo_message_get_current_shot) with -1 to the app.

After the second point is recorded, *ShotManager* will send a [SOLO_CABLE_CAM_OPTIONS](#solo_cable_cam_options) to the app so the app can retrieve the memorized yaw direction. The app can send [SOLO_CABLE_CAM_OPTIONS](#solo_cable_cam_options) to *ShotManager* to change any of the options. If the user hits the **Pause** button on Artoo, *ShotManager* will adjust cruiseSpeed to 0.0 and send [SOLO_CABLE_CAM_OPTIONS](#solo_cable_cam_options) to the app. Hitting “pause” again will set `cruiseSpeed` to the original speed and send it to the app. Two camera pointing modes are supported: interpolated camera ('interpolate cam') and user-controller camera ('free cam'). The 'camInterpolate' value in [SOLO_CABLE_CAM_OPTIONS](#solo_cable_cam_options) is a boolean that switches between these modes.

When the second point is recorded, *ShotManager* will set Solo to Guided and the copter will be on the cable.

### Zip Line

Zip Line is an infinitly long cable generated from Yaw/Pitch of the camera and initial location of the vehicle. Once created the pilot and fly the cable with the right stick and aim the camera with the left stick. 

Pressing A will allow the pilot to create a new Zip Line based on the camera pose. Pressing B will toggle from the default Free Look camera to a spot lock camera. The ROI will be sent to the app as a location.


The [SOLO_ZIPLINE_OPTIONS](#solo_zipline_options) packet is sent to control the speed and the option to take the camera pitch into account when creating Zip Lines. 

### Pano

Pano is constructed as 3 seperate modes - Video, Cylindical and Spherical. 

The Pano shot starts in a Setup state. Once the user chooses their point of view and options, the begin the shot. Once the shot is finished it exits to Fly or in the case of the Video Pan option, it will run indefinitely. 

The [SOLO_PANO_OPTIONS](#solo_pano_options) packet contains the desired type of Pano, the state (0 = setup, 1 = run), the Field of View in degrees for the cylinder shot, and the speed of the Video Pan for Pause/Resume functionality.


### Button mapping

The button mappings for ‘A’ and ‘B’ are stored on Solo. The app should poll these settings using [SOLO_GET_BUTTON_SETTING](#solo_get_button_setting), upon which *ShotManager* will send the current setting back.

If a user changes the setting, the app can set it with [SOLO_SET_BUTTON_SETTING](#solo_set_button_setting).

We only use "Press" events at the moment.


## Protocol

All communication follows this TLV format (little endian).

```cpp
Packet
{
    messageType : UInt32
    messageLength: UInt32
    messageValue : <n bytes as defined by messageLength>
}
```


## Message definitions


### General messages

We only have a few message types at the moment.

#### SOLO_MESSAGE_GET_CURRENT_SHOT

* **Sent by:** *ShotManager* to App. 
* **Valid:** ???

Sent from Solo to app when it enters a shot.

**SL version:** 1.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>0</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>4</td>
  </tr>
  <tr>
    <td>messageValue</td>
    <td>???</td>
    <td>Index of shot (SELFIE = 0, ORBIT=1, CABLECAM=2, FOLLOW=5)</td>
  </tr>
</table>


#### SOLO_MESSAGE_SET_CURRENT_SHOT

* **Sent by:** App to *ShotManager*.
* **Valid:** ???

Sent from app to Solo to request that Solo begin a shot.

**SL version:** 1.0

<table>
<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>1</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>4</td>
  </tr>
  <tr>
    <td>messageValue</td>
    <td>???</td>
    <td>Index of shot (SELFIE = 0, ORBIT=1, CABLECAM=2, FOLLOW=5, MPCABLECAM=6)</td>
  </tr>
</table>


#### SOLO_MESSAGE_LOCATION

* **Sent by:** App to *ShotManager*.
* **Valid:** ???

Sent from app to Solo to communicate a location.

**SL version:** 1.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>2</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>20</td>
  </tr>
  <tr>
    <td>latitude</td>
    <td>Double</td>
    <td></td>
  </tr>
  <tr>
    <td>longitude</td>
    <td>Double</td>
    <td></td>
  </tr>
  <tr>
    <td>altitude</td>
    <td>Float</td>
    <td>Altitude in meters.</td>
  </tr>
</table>


#### SOLO_MESSAGE_RECORD_POSITION

* **Sent by:** App to *ShotManager*.
* **Valid:** ???

Sent from app to Solo to request recording of a position.

**SL version:** 1.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>3</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>0</td>
  </tr>
</table>


#### SOLO_CABLE_CAM_OPTIONS

* **Sent by:** Bidirectional.
* **Valid:** Both App and *ShotManager* can send anytime after a legacy cable has been setup.

Sent from app to Solo to set [Cable cam (legacy)](#cable-cam-legacy) options. Sent from Solo to app to update cruise speed.

**SL version:** 1.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>4</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>8</td>
  </tr>
  <tr>
    <td>camInterpolation</td>
    <td>Short</td>
    <td>1 - On, 0 - Off</td>
  </tr>
  <tr>
    <td>yawDirection</td>
    <td>Short</td>
    <td>1 - Clockwise, 0 - Counterclockwise</td>
  </tr>
  <tr>
    <td>cruiseSpeed</td>
    <td>Float</td>
    <td>Cruise speed in meters/second.</td>
  </tr>
</table>


#### SOLO_GET_BUTTON_SETTING

* **Sent by:** Bidirectional.
* **Valid:** ???

Sent from app to Solo to request [Button mapping](#button-mapping) setting. Sent from Solo to app as a response.

**SL version:** 1.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>5</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>16</td>
  </tr>
  <tr>
    <td>button</td>
    <td>Int32</td>
    <td>ButtonPower = 0
ButtonFly = 1
ButtonRTL = 2
ButtonLoiter = 3
ButtonA = 4
ButtonB = 5
ButtonPreset1 = 6
ButtonPreset2 = 7
ButtonCameraClick = 8

</td>
  </tr>
  <tr>
    <td>event</td>
    <td>Int32</td>
    <td>Press =  0
Release = 1
ClickRelease = 2
Hold = 3
LongHold = 4
DoubleClick = 5</td>
  </tr>
  <tr>
    <td>shot</td>
    <td>Int32</td>
    <td>shot index, -1 if none. One of shot/mode should be -1, and the other should have a value</td>
  </tr>
  <tr>
    <td>mode</td>
    <td>Int32</td>
    <td>APM mode index, -1 if none</td>
  </tr>
</table>


#### SOLO_SET_BUTTON_SETTING

* **Sent by:** App to *ShotManager*.
* **Valid:** ???

Sent from app to Solo to set a [Button mapping](#button-mapping) setting.

**SL version:** 1.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>6</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>16</td>
  </tr>
  <tr>
    <td>button</td>
    <td>Int32</td>
    <td>ButtonPower = 0
ButtonFly = 1
ButtonRTL = 2
ButtonLoiter = 3
ButtonA = 4
ButtonB = 5
ButtonPreset1 = 6
ButtonPreset2 = 7
ButtonCameraClick = 8
</td>
  </tr>
  <tr>
    <td>event</td>
    <td>Int32</td>
    <td>Press =  0
Release = 1
ClickRelease = 2
Hold = 3
LongHold = 4
DoubleClick = 5</td>
  </tr>
  <tr>
    <td>shot</td>
    <td>Int32</td>
    <td>shot index, -1 if none. One of shot/mode should be -1, and the other should have a value</td>
  </tr>
  <tr>
    <td>mode</td>
    <td>Int32</td>
    <td>APM mode index, -1 if none</td>
  </tr>
</table>


#### SOLO_PAUSE

* **Sent by:** *ShotManager* <-> App.
* **Valid:** Valid only in a shot.

Used by *ShotManager* or app to transmit a pause request.


**SL version:** 2.4.0+


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 7
messageLength    | UInt32| 8


#### SOLO_FOLLOW_OPTIONS

* **Sent by:** Bidirectional.
* **Valid:** ???

Sent from app to Solo or vice versa to transmit follow options.

**SL version:** 1.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>19</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>8</td>
  </tr>
  <tr>
    <td>cruiseSpeed</td>
    <td>Float</td>
    <td>Cruise speed in meters/second.</td>
  </tr>
  <tr>
    <td>inLookAtMode</td>
    <td>int</td>
    <td>1 - yes, 0 - no</td>
  </tr>
</table>


**SL version:** 2.x.x ???

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>119</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>12</td>
  </tr>
  <tr>
    <td>cruiseSpeed</td>
    <td>Float</td>
    <td>Cruise speed in meters / second.</td>
  </tr>
  <tr>
    <td>inLookAtMode</td>
    <td>int</td>
    <td>1 - yes, 0 - no.</td>
  </tr>
  <tr>
    <td>freeLookMode</td>
    <td>int</td>
    <td>1 - yes, 0 - no</td>
  </tr>
</table>


#### SOLO_SHOT_OPTIONS

* **Sent by:** ???
* **Valid:** ???

Sent from app to Solo or vice versa to transmit selfie options.

These messages only go from *ShotManager* -> App.

**SL version:** 1.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>20</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>4</td>
  </tr>
  <tr>
    <td>cruiseSpeed</td>
    <td>Float</td>
    <td>Cruise speed in meters/second.</td>
  </tr>
</table>




#### SOLO_SHOT_ERROR

* **Sent by:** *ShotManager* -> App.
* **Valid:** ???

Sent from Solo to app when entry into a shot was attempted but rejected due to poor EKF, being unarmed, or RTL.

**SL version:** 1.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>21</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>4</td>
  </tr>
  <tr>
    <td>errorType</td>
    <td>Int32</td>
    <td>BAD_EKF = 0, UNARMED = 1, RTL = 2</td>
  </tr>
</table>


#### SOLO_MESSAGE_SHOTMANAGER_ERROR

* **Sent by:** *ShotManager* -> App.
* **Valid:** ???

Debugging tool - *ShotManager* sends this to the app when it has hit an exception.

**SL version:** 1.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>1000</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>N (length of exceptStr)</td>
  </tr>
  <tr>
    <td>exceptStr</td>
    <td></td>
    <td>Exception info and stacktrace</td>
  </tr>
</table>


#### SOLO_CABLE_CAM_WAYPOINT

* **Sent by:** *ShotManager* -> App.
* **Valid:** ???

Send the app our cable cam waypoint when it’s recorded.

**SL version:** 1.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>1001</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>28</td>
  </tr>
  <tr>
    <td>latitude</td>
    <td>Double</td>
    <td></td>
  </tr>
  <tr>
    <td>longitude</td>
    <td>Double</td>
    <td></td>
  </tr>
  <tr>
    <td>altitude</td>
    <td>Float</td>
    <td>Altitude in metres</td>
  </tr>
  <tr>
    <td>degreesYaw</td>
    <td>Float</td>
    <td>Yaw in degrees.</td>
  </tr>
  <tr>
    <td>pitch</td>
    <td>Float</td>
    <td>Camera pitch in degrees.</td>
  </tr>
</table>


#### SOLO_SECOND_PHONE_NOTIFICATION

* **Sent by:** *ShotManager* -> App.
* **Valid:** ???

*ShotManager* sends this to the app when the app is not the first to connect to *ShotManager* (it’s connection will be closed).

**SL version:** ???

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>1002</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>0</td>
  </tr>
</table>


#### SOLO_ZIPLINE_OPTIONS

* **Sent by:** Bidirectional.
* **Valid:** ???

Sent from app to Solo or vice versa to transmit zip line options.

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>119</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>6</td>
  </tr>
  <tr>
    <td>cruiseSpeed</td>
    <td>Float</td>
    <td>Cruise speed in meters / second.</td>
  </tr>
  <tr>
    <td>is3D</td>
    <td>UInt8</td>
    <td>1 - yes, 0 - no.</td>
  </tr>
  <tr>
    <td>camPointing</td>
    <td>UInt8</td>
    <td>1 -Spot Lock, 0 - Free Look</td>
  </tr>
</table>



#### SOLO_PANO_OPTIONS

* **Sent by:** Bidirectional.
* **Valid:** ???

Sent from app to Solo or vice versa to transmit Pano options.

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>119</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>8</td>
  </tr>
  <tr>
    <td>panoType</td>
    <td>UInt8</td>
    <td>1 - yes, 0 - no.</td>
  </tr>
  <tr>
    <td>run state</td>
    <td>UInt8</td>
    <td>1 - run, 0 - stop, reset</td>
  </tr>
  <tr>
    <td>cylinder_fov</td>
    <td>Int16</td>
    <td>91 to 360</td>
  </tr>
  <tr>
    <td>is3D</td>
    <td>UInt8</td>
    <td>1 - yes, 0 - no.</td>
  </tr>
  <tr>
    <td>degSecondYaw</td>
    <td>Float</td>
    <td>-60 to 60 (deg/sec)</td>
  </tr>
</table>



### Multipoint cable cam (SOLO_SPLINE_) messages


#### SOLO_SPLINE_RECORD

* **Sent by:** App -> *ShotManager*.
* **Valid:** ???

Tells *ShotManager* to enter [Record](#record-mode) mode and clear the current [Path](#definition-of-a-path). 

**SL version:** ???

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>50</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>0</td>
  </tr>
</table>




#### SOLO_SPLINE_PLAY

* **Sent by:** Bidirectional.
* **Valid:** ???

Bidirectional message: sent by the app to tell *ShotManager* to enter [Play mode](#play-mode);  sent by *ShotManager* to the app after entering Play mode in response to an Artoo button press.

In both cases, *ShotManager* follows this message with a sequence of [SOLO_SPLINE_POINT](#solo_spline_point) messages to transmit the current Path to the app.

*ShotManager* will only enter [Play mode](#play-mode) if a valid [Path](##definition-of-a-path) exists in [Record mode](#record-mode);  otherwise, the behavior is undefined. This implies that the app must only send this message when it knows a valid Path exists.

**SL version:** ???

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>51</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>0</td>
  </tr>
</table>



#### SOLO_SPLINE_POINT

* **Sent by:** Bidirectional.
* **Valid:** ???

Transmits proposed or actual Keypoints on the current camera [Path](#definition-of-a-path).

*ShotManager* uses this message for two things:

1. To transmit Keypoints it creates in response to Artoo button presses or [SOLO_MESSAGE_RECORD_POSITION](#solo_message_record_position) messages.
1. To confirm the validity of Keypoints it receives from the app; to ACK those Keypoints.

When *ShotManager* creates a Keypoint, it assigns an index. When the app receives this message and a Keypoint with the index already exists, it updates the Keypoint to the values in this message;  it replaces the existing Keypoint.

The app uses this message to load Keypoints from previously recorded, known valid Paths into *ShotManager*.

In every case, *ShotManager* sends a [SOLO_SPLINE_POINT](#solo_spline_point) message back to the app to confirm it was able to create the Keypoint. If it can't create the Keypoint, it sends a failure status.


**SL version:** ???

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>52</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>44</td>
  </tr>
  <tr>
    <td>version</td>
    <td>UInt16</td>
    <td>0</td>
  </tr>
  <tr>
    <td>absAltReference</td>
    <td>Float</td>
    <td>Absolute altitude of home location when cable was recorded, in meters.</td>
  </tr>
  <tr>
    <td>index</td>
    <td>Int32</td>
    <td>starting at 0</td>
  </tr>
  <tr>
    <td>latitude</td>
    <td>Double</td>
    <td>Latitude (decimal degrees).</td>
  </tr>
  <tr>
    <td>longitude</td>
    <td>Double</td>
    <td>Longitude (decimal degrees).</td>
  </tr>
  <tr>
    <td>altitude</td>
    <td>Float</td>
    <td>Relative altitude in metres.</td>
  </tr>
  <tr>
    <td>pitch</td>
    <td>Float</td>
    <td>Pitch (degrees).</td>
  </tr>
  <tr>
    <td>yaw</td>
    <td>Float</td>
    <td>Yaw (degrees)</td>
  </tr>
  <tr>
    <td>uPosition</td>
    <td>Float</td>
    <td>The parametric offset of the Keypoint along the Path. In Record mode, these values have no meaning since they can't be assigned until the Path is complete. In Play mode, *ShotManager* assigns these values and sends messages to the app. The app never creates these values.</td>
  </tr>
  <tr>
    <td>status</td>
    <td>Int16</td>
    <td><i>ShotManager</i> sends this value to indicate success or failure when creating a Keypoint. Negative values are failure;  0 or positive is success.
    
    <p><b>Error codes:</b></p>
<ul>
<li>-1 : mode error (tried setting a spline point when we were already in PLAY mode).</li>
<li>-2 : keypoint too close to a previous keypoint</li>
<li>-3 : duplicate index error (received multiple Keypoints for a single index)</li>
<li>-4..-MAXINT16 : unspecified failure</li>
</ul>
  </tr>
</table>




#### SOLO_SPLINE_ATTACH

* **Sent by:** Bidirectional.
* **Valid:** Only after Path is loaded.

This message directs *ShotManager* to fly to a Keypoint on the Path. After the vehicle reaches this point, *ShotManager* responds with a [SOLO_SPLINE_ATTACH](#solo_spline_attach) to indicate that it has reached the Path and is prepared to receive [SOLO_SPLINE_SEEK](#solo_spline_seek) messages.

When *ShotManager* enters playback mode, the vehicle may or may not be positioned on the path -- from the app’s point of view, the actual position and velocity of the vehicle with respect to the Path are unknown.

How *ShotManager* directs the vehicle to the Path is implementation specific and not defined.

This message is only valid **once** after a Path is loaded. There is no corresponding "detach" message -- the vehicle stays attached until playback mode is exited.


**SL version:** ???

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>57</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>4</td>
  </tr>
  <tr>
    <td>keypointIndex</td>
    <td>Int32</td>
    <td>The index of the Keypoint on the currently defined Path to which *ShotManager* will attach (or did attach, for <i>ShotManager</i> to App packets).</td>
  </tr>
</table>




#### SOLO_SPLINE_SEEK

* **Sent by:** App -> *ShotManager*.
* **Valid:** Valid only in [Play mode](#play-mode) when the vehicle is attached to the Path. Ignored at other times.

This message tells *ShotManager* to fly the vehicle to a position along the normalized length of the Path. The cruiseState value indicates pause/play state of the vehicle. This does *not* overwrite the stored cruise speed set by [SOLO_SPLINE_PATH_SETTINGS](#solo_spline_path_settings).

**SL version:** ???

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>53</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>8</td>
  </tr>
  <tr>
    <td>uPosition</td>
    <td>Float</td>
    <td>A parametric offset along the Path normalized to (0,1).</td>
  </tr>
  <tr>
    <td>cruiseState</td>
    <td>Int32</td>
    <td>Used by the app to determine the state of the cruise play/pause buttons.<ul>
    <li>-1: Cruising to the start of the cable(negative cruise speed).</li>
    <li>0 : Not moving/paused (cruise speed == 0). (DEFAULT)</li>
    <li>1 : Cruising to the end of the cable (positive cruise speed).</li>
    </ul></td>
  </tr>
</table>




#### SOLO_SPLINE_PLAYBACK_STATUS

* **Sent by:** *ShotManager* to App. 
* **Valid:** Valid only in [Play mode](#play-mode).

*ShotManager* sends this message to the app to indicate the vehicle's parametric position and cruise state along the Path. The source, precision, and accuracy of these values is solely determined by *ShotManager*. They are for visualization in the app, but not control;  they are intended to convey the information, "the vehicle was at this point, trying to move at this cruise speed when the message was sent" with as much certainty as practically possible. But there are no guarantees.

The frequency at which *ShotManager* sends these messages is currently 10Hz. At a minimum, in playback mode *ShotManager* will send this message:

* When the vehicle attaches to the path in response to the first [SOLO_SPLINE_SEEK](#solo_spline_seek) message received after entering Play mode.
* Each time the vehicle passes a Keypoint, including the beginning and end of the path
* When the vehicle starts or stops moving.
* When the vehicle’s parametric acceleration exceeds a threshold value:

The threshold is implementation-specific, exact value TBD (ideally, it should be "tuneable").


**SL version:** ???

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>54</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>8</td>
  </tr>
  <tr>
    <td>uPosition</td>
    <td>Float</td>
    <td>A parametric offset along the Path normalized to (0,1).</td>
  </tr>
  <tr>
    <td>cruiseState</td>
    <td>Int32</td>
    <td>Used by the app to determine the state of the cruise play/pause buttons.<ul>
    <li>-1: Cruising to the start of the cable (negative cruise speed).</li>
    <li>0 : Not moving/paused (cruise speed == 0). (DEFAULT)</li>
    <li>1 : Cruising to the end of the cable (positive cruise speed).</li>
    </ul></td>
  </tr>
</table>


#### SOLO_SPLINE_PATH_SETTINGS

* **Sent by:** App -> *ShotManager*. Optional.
* **Valid:** Valid only in [Play mode](#play-mode).

The app sends this message to configure various aspects of how *ShotManager* interprets the current Path. This message is optional -- if the app never sends it, *ShotManager* will use the assumed default values listed below. Values stay in effect until the Path is reset by a [SOLO_SPLINE_RECORD](#solo_spline_record) message.

**SL version:** ???

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>55</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>8</td>
  </tr>
  <tr>
    <td>cameraControl</td>
    <td>Int32</td>
    <td><ul>
<li>0 : *ShotManager* controls camera interpolation;  automatically points camera</li>
<li>1 : No camera interpolation - camera is controlled with Artoo only.</li>
(DEFAULT 0)</ul></td>
  </tr>
  <tr>
    <td>desiredTime</td>
    <td>Float</td>
    <td>The app-requested total cable completion time, in seconds.</td>
  </tr>
</table>



#### SOLO_SPLINE_DURATIONS

* **Sent by:** *ShotManager* -> App.
* **Valid:** Valid only in [Play mode](#play-mode).

Used by *ShotManager* to transmit time information about the currently defined Path. It is sent **at least once** after *ShotManager* enters play mode to define the time bounds for the Path.

Optionally, *ShotManager* can also resend the information any time previous values become invalid. For example, high winds or a low battery might mean that the previously reported maxUVelocity isn’t realistic;  *ShotManager* would re-send the message to advise the app to change its estimates.


**SL version:** ???


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 56
messageLength    | UInt32| 8
minTime | Float | The estimated time (in seconds) it will take to fly the entire path at maximum speed.
maxTime | Float | The estimated time (in seconds) it will take to fly the entire path at minimum speed.




### GoPro messages

#### GOPRO_SET_ENABLED

* **Sent by:** ???
* **Valid:** ???

Enable/disable GoPro communications altogether. This can be useful in dealing with a camera model that is incapable of handling communications. This value will be stored by *ShotManager* and persist between boots.

**SL version:** ???

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>5000</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>4</td>
  </tr>
  <tr>
    <td>enabled</td>
    <td>UInt32</td>
    <td>0 off, 1 on</td>
  </tr>
</table>


#### GOPRO_SET_REQUEST

* **Sent by:** App -> *ShotManager*
* **Valid:** ???

Wrapper for the MAVLink version. See [here](https://docs.google.com/document/d/1CcYOCZRw9C4sIQu4xDXjPMkxZYROmTLB0EtpZamnq74/edit#) for reference on this message. The app will send this to *ShotManager* via TCP, so that *ShotManager* can handle this without using the lossy MAVLink connection. This is a legacy request that will only be able to set the first byte of the request payload.

**SL version:** 1.1.12

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>5001</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>4</td>
  </tr>
  <tr>
    <td>command</td>
    <td>unsigned short</td>
    <td></td>
  </tr>
  <tr>
    <td>value</td>
    <td>unsigned short</td>
    <td></td>
  </tr>
</table>


#### GOPRO_RECORD

* **Sent by:** ???
* **Valid:** ???

Higher level call, allowing the app/Artoo to issue a record command in either video or stills mode. *ShotManager* will handle issuing the command

**SL version:** 1.1.12

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>5003</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>4</td>
  </tr>
  <tr>
    <td>on/off</td>
    <td>UInt32</td>
    <td>0: Stop recording
1: Start recording
2: Toggle recording</td>
  </tr>
</table>


#### GOPRO_STATE

* **Sent by:** *ShotManager* -> App
* **Valid:** ???

Attempt to encapsulate all state that an app might want to know about the GoPro in one packet. This is automatically sent from *ShotManager* to the app any time a change in its contents occurs. Otherwise the app can explicitly request it to be sent by sending *ShotManager* a [GOPRO_REQUEST_STATE](#gopro_request_state) packet (see below).

Because of a bug in earlier versions of the iOS app, the new *ShotManager* will actually send two packets: a V1 packet with the original field contents and a new V2 packet with the extended GoPro state.

**SL version:** 1.1.12 (Incomplete handling in SL version 1.1.12)

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>5005: V1 spec
5006: V2 spec</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>36</td>
  </tr>
  <tr>
    <td>Version</td>
    <td>UInt8</td>
    <td>Which version of the spec?

Version 1 only supplies data through capture mode. Version 2 adds additional fields.</td>
  </tr>
  <tr>
    <td>Model</td>
    <td>UInt8</td>
    <td>Model of the camera. Currently not supported.</td>
  </tr>
  <tr>
    <td>Status</td>
    <td>UInt8</td>
    <td>Status:
0: STATUS_NO_GOPRO
1: STATUS_INCOMPATIBLE_GOPRO
2: STATUS_GOPRO_CONNECTED
3: STATUS_ERROR</td>
  </tr>
  <tr>
    <td>Recording</td>
    <td>UInt8</td>
    <td>0: not recording
1: recording</td>
  </tr>
  <tr>
    <td>Capture Mode</td>
    <td>UInt8</td>
    <td>CAPTURE_MODE_VIDEO = 0
CAPTURE_MODE_PHOTO = 1
CAPTURE_MODE_BURST = 2 (Hero3+ only)
CAPTURE_MODE_TIMELAPSE = 3
CAPTURE_MODE_MULTISHOT = 4 (Hero4 only)</td>
  </tr>
  <tr>
    <td>NTSC/PAL</td>
    <td>UInt8</td>
    <td>0: NTSC
1: PAL</td>
  </tr>
  <tr>
    <td>Video Resolution</td>
    <td>UInt8</td>
    <td></td>
  </tr>
  <tr>
    <td>Video FPS</td>
    <td>UInt8</td>
    <td></td>
  </tr>
  <tr>
    <td>Video FOV</td>
    <td>UInt8</td>
    <td></td>
  </tr>
  <tr>
    <td>Video Low Light</td>
    <td>UInt8</td>
    <td>0: Off
1: On
requires compatible video settings</td>
  </tr>
  <tr>
    <td>Photo Resolution</td>
    <td>UInt8</td>
    <td></td>
  </tr>
  <tr>
    <td>Photo Burst Rate</td>
    <td>UInt8</td>
    <td></td>
  </tr>
  <tr>
    <td>Video Protune</td>
    <td>UInt8</td>
    <td>0: Off
1: On
requires compatible video settings</td>
  </tr>
  <tr>
    <td>Video White Balance</td>
    <td>UInt8</td>
    <td>Hero3 only.
Requires protune on.</td>
  </tr>
  <tr>
    <td>Video Color</td>
    <td>UInt8</td>
    <td>Hero3 only.
Requires protune on.</td>
  </tr>
  <tr>
    <td>Video Gain</td>
    <td>UInt8</td>
    <td>Hero3 only.
Requires protune on.</td>
  </tr>
  <tr>
    <td>Video Sharpness</td>
    <td>UInt8</td>
    <td>Hero3 Only
requires protune on</td>
  </tr>
  <tr>
    <td>Video Exposure</td>
    <td>UInt8</td>
    <td>Requires protune on.

Hero4 range only from -2.0 to 2.0. Hero3+ from -5.0 to 5.0. We only care about -2.0 to 2.0</td>
  </tr>
  <tr>
    <td>Gimbal Enabled</td>
    <td>UInt8</td>
    <td>0: Off
1: On</td>
  </tr>
  <tr>
    <td>Extra1</td>
    <td>UInt8</td>
    <td>Reserved for future use.</td>
  </tr>
  <tr>
    <td>Extra2</td>
    <td>UInt8</td>
    <td>Reserved for future use.</td>
  </tr>
  <tr>
    <td>Extra3</td>
    <td>UInt8</td>
    <td>Reserved for future use.</td>
  </tr>
  <tr>
    <td>Extra4</td>
    <td>UInt8</td>
    <td>Reserved for future use.</td>
  </tr>
  <tr>
    <td>Extra5</td>
    <td>UInt8</td>
    <td>Reserved for future use.</td>
  </tr>
  <tr>
    <td>Extra6</td>
    <td>UInt8</td>
    <td>Reserved for future use.</td>
  </tr>
  <tr>
    <td>Extra7</td>
    <td>UInt8</td>
    <td>Reserved for future use.</td>
  </tr>
  <tr>
    <td>Extra1</td>
    <td>UInt16</td>
    <td>Reserved for future use.</td>
  </tr>
  <tr>
    <td>Extra2</td>
    <td>UInt16</td>
    <td>Reserved for future use.</td>
  </tr>
  <tr>
    <td>Extra3</td>
    <td>UInt16</td>
    <td>Reserved for future use.</td>
  </tr>
  <tr>
    <td>Extra4</td>
    <td>UInt16</td>
    <td>Reserved for future use.</td>
  </tr>
  <tr>
    <td>Extra5</td>
    <td>UInt16</td>
    <td>Reserved for future use.</td>
  </tr>
</table>


#### GOPRO_REQUEST_STATE

* **Sent by:** App -> *ShotManager*
* **Valid:** ???

Requests that *ShotManager* send the app a [GOPRO_STATE](#gopro-state) packet

**SL version:** 1.2.0

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>5007</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>0</td>
  </tr>
</table>


#### GOPRO_SET_EXTENDED_REQUEST

* **Sent by:** App -> *ShotManager*
* **Valid:** ???

Wrapper for the MAVLink version. See [here](https://docs.google.com/document/d/1CcYOCZRw9C4sIQu4xDXjPMkxZYROmTLB0EtpZamnq74/edit#) for reference on this message. The app will send this to *ShotManager* via TCP, so that *ShotManager* can handle this without using the lossy MAVLink connection. This differs from the [GOPRO_SET_REQUEST](#gopro_set_request) in that all 4 payload bytes can be set.

**SL version:** 1.3

<table>
  <tr>
    <th>Field</th>
    <th>Type</th>
    <th>Value/Description</th>
  </tr>
  <tr>
    <td>messageType</td>
    <td>UInt32</td>
    <td>5009</td>
  </tr>
  <tr>
    <td>messageLength</td>
    <td>UInt32</td>
    <td>6</td>
  </tr>
  <tr>
    <td>command</td>
    <td>UInt16</td>
    <td></td>
  </tr>
  <tr>
    <td>value</td>
    <td>UInt8[4]</td>
    <td></td>
  </tr>
</table>

### GeoFence messages

#### GEOFENCE_SET_DATA

* **Sent by:** App -> *ShotManager*.
* **Valid:** Always

Sent from app to *ShotManager* to set geofence data. The data is encapsulated in a JSON blob. There are three keys in the JSON Blob, each of them is an array of polygon's information. They must be of equal sizes. *ShotManager* will validate this packet and respond with *GEOFENCE_SET_ACK* with either a positive ack (good data) or negative ack (bad data).

**version:** v2.4.0+


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 3000
messageLength    | UInt32| length of the following JSON blob
JSON blob        | N/A   | JSON blob payload

JSON Blob:

| Field          | Type       | Value/Description
---------------- | ----       | ------------
coord            | JSON Array | ordered list of polygon, which is in turn an ordered list of (lat, lon), counter-clockwise vertices of genfence polygon
subCoord         | JSON Array | ordered list of polygon, which is in turn an ordered list of (lat, lon), counter-clockwise vertices of geofence sub polygon
type             | JSON Array | ordered list of polygon types, 1 for exclusive geofence and 0 for inclusive geofence


Example:
```python
data = {
  'coord':    [
                [
                  [37.873391778802457, -122.30124440324217], 
                  [37.873425469262187, -122.30088420379124], 
                  [37.87289578293214, -122.30071240112851], 
                  [37.872942621197538, -122.30124440324217]
                ]
              ],
  'subCoord': [
                [
                  [37.873405777181389, -122.30090131123818], 
                  [37.872916521332435, -122.30074261865762], 
                  [37.872958695063687, -122.3012216429134], 
                  [37.873375815652267, -122.3012216429134]
                ]
              ],
  'type':     [
                0
              ]
        }
```


#### GEOFENCE_SET_ACK

* **Sent by:** App <- *ShotManager*.
* **Valid:** After *GEOFENCE_SET_DATA*, *GEOFENCE_UPDATE_POLY* or *GEOFENCE_CLEAR* is sent from App to *ShotManager*

Acknowledge from *ShotManager* to the App after message from the App. Can either be a positive ack (*ShotManager* took the change) or negative ack (*ShotManger* rejected the change).

**version:** v2.4.0+


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 3001
messageLength    | UInt32| 3
count            | UInt16| The total number of polygons existing on *ShotManger* right now)
valid            | Bool  | True: Positive ack / False: Negative ack


#### GEOFENCE_UPDATE_POLY

* **Sent by:** App -> *ShotManager*.
* **Valid:** When *ShotManager* already has polygon data

Update a polygon, either: 1. Update a vertex; 2. add a new vertex; 3. delete a vertex. The course of action is determined by the first byte after messaegLength. 
__This message is currently not used and is subject to change.__

**version:** v2.4.0+


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 3002
messageLength    | UInt32| 37
action           | UInt8 | action to be performed, see below
polygonIndex     | UInt16| Index of target polygon
vertexIndex      | UInt16| Index of target vertex
lat              | Double| latitude of new coordinate on polygon
lon              | Double| longitude of new coordinate on polygon
subLat           | Double| latitude of new coordinate on subpolygon
subLon           | Double| longitude of new coordinate on subpolygon

Action:

| Value | Description
------- | -----------
0       | Update Vertex
1       | Add Vertex
2       | Remove Vertex, the following four Double will be ignored in this case


#### GEOFENCE_CLEAR

* **Sent by:** App <-> *ShotManager*.
* **Valid:** Always

Either the App or *ShotManager* can send this message to indicate GeoFence has been cleared on their sides. When this message is sent from App to *ShotManager*, *ShotManager* will also send a *GEOFENCE_SET_ACK*.

**version:** v2.4.0+


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 3003
messageLength    | UInt32| 0


#### GEOFENCE_ACTIVATED

* **Sent by:** App <- *ShotManager*.
* **Valid:** Always

*ShotManager* will send this message to the App every time GeoFence is activating.

**version:** v2.4.0+


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 3004
messageLength    | UInt32| 0


### Site Scan Inspect (SOLO_INSPECT_) messages

#### SOLO_INSPECT_START

* **Sent by:** App -> *ShotManager*.
* **Valid:** Only once during an Inspect shot.

Sent by the app to *ShotManager* to notify that the inspect shot is ready to commence and the vehicle should climb to the provided **takeoffAlt**. Shotmanager will either takeoff or place the vehicle into *GUIDED* depending on whether the vehicle is already in the air or not.

**version:** v2.2.0+ 


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 10001
messageLength    | UInt32| 4
takeoffAlt | Float | Relative altitude from takeoff (in meters) that the vehicle should navigate to.


#### SOLO_INSPECT_SET_WAYPOINT

* **Sent by:** App -> *ShotManager*.
* **Valid:** Anytime during the active Inspect shot

Sent by the app to *ShotManager* to instruct Solo to navigate towards the provided waypoint.

**version:** v2.2.0+ 


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 10002
messageLength    | UInt32| 12
latitude | Float | Latitude in decimal degrees
longitude | Float | Longitude in decimal degrees
latitude | Float | Relative altitude from takeoff (in meters)


#### SOLO_INSPECT_MOVE_GIMBAL

* **Sent by:** App -> *ShotManager*.
* **Valid:** Anytime during the active Inspect shot

Sent by the app to *ShotManager* to instruct Solo to actuate gimbal to desired orientation.

**version:** v2.2.0+ 


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 10003
messageLength    | UInt32| 12
pitch | Float | Body-relative pitch in degrees (0 to -90)
roll | Float | Body-relative roll in degrees
yaw | Float | Earth frame Yaw (heading) in degrees (0 to 360)


#### SOLO_INSPECT_MOVE_VEHICLE

* **Sent by:** App -> *ShotManager*.
* **Valid:** Anytime during the active Inspect shot

Sent by the app to *ShotManager* to instruct Solo to move with a certain velocity (body-relative NED frame).

**version:** v2.2.0+ 


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 10004
messageLength    | UInt32| 12
vx | Float | Desired velocity in body-x (NED)
vy | Float | Desired velocity in body-y (NED)
vz | Float | Desired velocity in body-z (NED)

### Site Scan Scan (SOLO_SCAN_) messages

#### SOLO_SCAN_START

* **Sent by:** App -> *ShotManager*.
* **Valid:** Only once during a Scan shot.

Sent by the app to *ShotManager* to notify that the scan shot is ready to commence.

**version:** v2.2.0+ 


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 10101
messageLength    | UInt32| 0


### Site Scan Survey (SOLO_SURVEY_) messages


#### SOLO_SURVEY_START

* **Sent by:** App -> *ShotManager*.
* **Valid:** Only once during a Survey shot.

Sent by the app to *ShotManager* to notify that the survey shot is ready to commence.

**version:** v2.2.0+ 


| Field          | Type  | Value/Description
---------------- | ----  | ------------
messageType      | UInt32| 10201
messageLength    | UInt32| 0

