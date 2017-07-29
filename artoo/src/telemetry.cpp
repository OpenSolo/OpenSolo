#include "telemetry.h"
#include "flightmanager.h"

bool Telemetry::isEkfGpsOk(uint16_t flags)
{
    // TODO: Hack: have to define this here while MAVLink libraries/headers get updated
    const uint16_t EKF_GPS_GLITCHING = 1 << 15;  // Hackattack: changed from 14 to 15 with new bit introduced

    if (((flags & EKF_GPS_GLITCHING) > 0)) {
        return false;
    }

    // logic lifted from position_ok() in ardupilot/ArduCopter/system.pde

    if (FlightManager::instance.armed()) {
        return ((flags & EKF_POS_HORIZ_ABS) > 0) && ((flags & EKF_CONST_POS_MODE) == 0);
    }

    return ((flags & EKF_POS_HORIZ_ABS) > 0) || ((flags & EKF_PRED_POS_HORIZ_ABS) > 0);
}
