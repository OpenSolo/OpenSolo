#ifndef TELEMETRY_H
#define TELEMETRY_H

#include "stm32/common.h"

#include <limits.h>

/*
 * Common struct to collect the telem values
 * that various modules are interested in.
 */

struct Telemetry {

    // values for mavlink_gps_raw_int_t - mavlink doesn't appear to define these anywhere?
    enum GpsFixType {
        GpsNoFix0       = 0,
        GpsNoFix1       = 1,
        GpsTwoDFix      = 2,
        GpsThreeDFix    = 3,
        GpsDGps         = 4,
        GpsRtk          = 5,
    };

    static const uint16_t EKF_UNINIT = 0xffff;

    static ALWAYS_INLINE bool isGPSLevelFix(uint8_t gps) {
        return gps >= GpsTwoDFix;
    }

    static bool isEkfGpsOk(uint16_t flags);

    int8_t battLevel;   // 0 - 100, represents percent
    uint8_t gpsFix;     // one of GpsFixType
    int8_t rssi;
    uint8_t numSatellites;

    float altitude;
    float airSpeed;
    float groundSpeed;

    uint16_t ekfFlags;

    int8_t flightBatteryDisplay() const {
        // if uninitialized, show as 0
        return clamp(battLevel, int8_t(0), int8_t(100));
    }

    bool flightBatteryInitialized() const {
        return battLevel != -1;
    }

    bool rssiInitialized() const {
        return rssi != SCHAR_MAX;
    }

    bool numSatellitesInitialized() const {
        return numSatellites != 0xff;
    }

    bool ekfFlagsInitialized() const {
        return ekfFlags != 0xffff;
    }

    bool hasGpsFix() const {
#if 1
        return isEkfGpsOk(ekfFlags);
#else
        return isGPSLevelFix(gpsFix);
#endif
    }

    void clear() {
        battLevel = -1;         // uninitialized
        rssi = SCHAR_MAX;       // uninitialized
        numSatellites = 0xff;   // uninitialized
        ekfFlags = EKF_UNINIT;  // uninitialized
        altitude = 0;
        airSpeed = 0;
        groundSpeed = 0;
    }
};

#endif // TELEMETRY_H
