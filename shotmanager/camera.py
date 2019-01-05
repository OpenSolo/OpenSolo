# functions to retrieve camera pitch and yaw
# These are factored out so we can handle things like
# whether we have a gimbal or not in one location

import math

def getYaw( vehicle ):
    # do we have a gimbal?  If so, get the yaw from it
    # can't do until we have pointing working on our gimbal

    """
    For now, gimbal yaw reporting is not the way to go.  We will use vehicle yaw reporting in all cases

    if vehicle.mount_status[1] != None:
        return vehicle.mount_status[1]
    else:
    	return math.degrees( vehicle.attitude.yaw )
    """
    return math.degrees( vehicle.attitude.yaw )


def getPitch( vehicle ):
    if vehicle.mount_status[0]:
        return vehicle.mount_status[0]
    else:
        return 0.0