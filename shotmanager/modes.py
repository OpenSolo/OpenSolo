#!/usr/bin/env python

# mode names - These are what Artoo displays

MODE_NAMES = {
	-1 : "None\0",
    0 : 'Stabilize\0',
    1 : 'Acro\0',
    2 : 'FLY: Manual\0',
    3 : 'Autonomous\0',
    4 : 'Takeoff\0',
    5 : 'FLY\0',
    6 : 'Return Home\0',
    7 : 'Circle\0',
    8 : 'Position\0',
    9 : 'Land\0',
    10 : 'OF_LOITER\0',
    11 : 'Drift\0',
    13 : 'Sport\0',
    14 : 'Flip\0',
    15 : 'Auto-tune\0',
    16 : 'Position Hold\0',
    17 : 'Brake\0',
    18 : 'Throw\0',
    19 : 'ADS-B AVOID\0',
    20 : 'GUIDED NO GPS\0',
    21 : 'SMART RTL\0', 
    }

# DroneKit uses APM's mode names.  Here is a helper function to
# go from DroneKit's name to APM mode index
def getAPMModeIndexFromName( modeName, vehicle ):
    # most of these names are in pymavlink's mode mapping.
    # But not all!
    # Here we handle cases that aren't
    # if it's a mode that's not in mavlink's mapping, it's formatted
    # like Mode(12)
    if "Mode(" in modeName:
        try:
            return int(modeName[5:-1])
        except:
            return -1
    elif modeName in vehicle._mode_mapping:
        return vehicle._mode_mapping[modeName]
    else:
        return -1
