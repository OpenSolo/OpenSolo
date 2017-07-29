#!/usr/bin/env python

# definitions of packets that go from the App to Artoo or App to Solo and vice versa.
# All packets are of the form (in little endian)
# 32-bit type identifier
# 32-bit length
# n bytes value
# https://docs.google.com/a/3drobotics.com/document/d/1rA1zs3T7X1n9ip9YMGZEcLCW6Mx1RR1bNlh9gF0i8nM/edit#heading=h.tcfcw63p9sfk

# packet type definitions
# Solo-App messages
# NOTE: Make sure this stays in sync with the app's definitions!  Those are in iSolo/networking/SoloPacket.swift
SOLO_MESSAGE_HEADER_LENGTH = 8

# Sends Solo's current shot to the app
SOLO_MESSAGE_GET_CURRENT_SHOT = 0
SOLO_MESSAGE_SET_CURRENT_SHOT = 1

# send a location
SOLO_MESSAGE_LOCATION = 2
# record a position (for cable cam)
SOLO_RECORD_POSITION = 3
SOLO_CABLE_CAM_OPTIONS = 4
SOLO_MESSAGE_GET_BUTTON_SETTING = 5
SOLO_MESSAGE_SET_BUTTON_SETTING = 6
SOLO_PAUSE = 7

SOLO_FOLLOW_OPTIONS = 19
SOLO_FOLLOW_OPTIONS_V2 = 119
SOLO_SHOT_OPTIONS = 20
SOLO_SHOT_ERROR = 21
SOLO_PANO_OPTIONS = 22
SOLO_ZIPLINE_OPTIONS = 23
SOLO_REWIND_OPTIONS = 24
SOLO_PANO_STATE = 25
SOLO_HOME_LOCATION = 26
SOLO_POWER_STATE = 27
SOLO_ZIPLINE_LOCK = 28

SOLO_SPLINE_RECORD = 50
SOLO_SPLINE_PLAY = 51
SOLO_SPLINE_POINT = 52
SOLO_SPLINE_SEEK = 53
SOLO_SPLINE_PLAYBACK_STATUS = 54
SOLO_SPLINE_PATH_SETTINGS = 55
SOLO_SPLINE_DURATIONS = 56
SOLO_SPLINE_ATTACH = 57

# Artoo-App messages start at 100


# Shot manager to app messages start at 1000
SOLO_MESSAGE_SHOTMANAGER_ERROR = 1000
# recorded waypoint contents
SOLO_CABLE_CAM_WAYPOINT = 1001

# IG shots.
## IG Inspect - app to shotmanager
SOLO_INSPECT_START = 10001
SOLO_INSPECT_SET_WAYPOINT = 10002
SOLO_INSPECT_MOVE_GIMBAL = 10003
SOLO_INSPECT_MOVE_VEHICLE = 10004

## IG Scan
SOLO_SCAN_START = 10101

## IG Survey
SOLO_SURVEY_START = 10201

# Geo Fence
GEOFENCE_SET_DATA = 3000
GEOFENCE_SET_ACK = 3001
GEOFENCE_UPDATE_POLY = 3002
GEOFENCE_CLEAR = 3003
GEOFENCE_ACTIVATED = 3004

# Gopro control messages
GOPRO_SET_ENABLED = 5000
GOPRO_SET_REQUEST = 5001
GOPRO_RECORD = 5003
GOPRO_V1_STATE = 5005
GOPRO_V2_STATE = 5006
GOPRO_REQUEST_STATE = 5007
GOPRO_SET_EXTENDED_REQUEST = 5009


# enums for packet types
# failure to enter a shot due to poor ekf
SHOT_ERROR_BAD_EKF = 0
# can't enter shot if we're not armed
SHOT_ERROR_UNARMED = 1
#can't enter shot if we're RTL
SHOT_ERROR_RTL = 2

# status error codes for spline point message
SPLINE_ERROR_NONE = 0
SPLINE_ERROR_MODE = -1
SPLINE_ERROR_DUPLICATE = -2