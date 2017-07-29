SERVER_PORT = 5507

RC_FREQUENCY = 50.0

# if this is 0, don't skip any RC packets.
# if 1, skip every other one, and so forth
RC_SKIP_MULTIPLE = 1
UPDATE_RATE = RC_FREQUENCY / (RC_SKIP_MULTIPLE + 1)
UPDATE_TIME = 1.0 / UPDATE_RATE

MAX_SPEED = 8.0

# don't allow waypoints this close to each other
WAYPOINT_NEARNESS_THRESHOLD = 2.5

# cm / s from APM
DEFAULT_WPNAV_SPEED_VALUE = 500.0

# in seconds
BRAKE_LENGTH = 1.5

NUM_TICKS_FOR_BRAKE = int( BRAKE_LENGTH * UPDATE_RATE )

# this is FLY mode - see pymavlink/mavutil.py:mode_mapping_acm
DEFAULT_APM_MODE = 5

# default altitude limit
DEFAULT_FENCE_ALT_MAX = 46 #meters, ~150 feet
DEFAULT_FENCE_ENABLE = 0 # Disabled by default, as the failure mode is safer. Better to not stop the copter from climbing than to force it to descend when entering a shot.

# Spektrum channels order
THROTTLE = 0
ROLL = 1
PITCH = 2
YAW = 3
FILTERED_PADDLE = 5
RAW_PADDLE = 7

RTL_SPEED = 10