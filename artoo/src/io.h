#ifndef IO_DEFS_H
#define IO_DEFS_H

#include "board.h"

namespace Io {

/*
 * Neutral space to declare i/o enumerations,
 * primarily to avoid circular includes.
 */

enum ButtonID {
    ButtonPower,        // S1
    ButtonFly,          // S2
    ButtonRTL,          // S3
    ButtonLoiter,       // S4
    ButtonA,            // S5
    ButtonB,            // S6
    ButtonPreset1,      // S7
    ButtonPreset2,      // S8
    ButtonCameraClick,  // S9
};

// first 4 IDs in the order that SPKT/DSM expects
enum StickID {
    StickThro,
    StickRoll,
    StickPitch,
    StickYaw,
    StickGimbalY,
    StickGimbalRate
};

enum AdcID {
    AdcStick0,
    AdcStick1,
    AdcStick2,
    AdcStick3,
    AdcGimbalY,
    AdcGimbalRate,
#if (BOARD >= BOARD_BB03)
    AdcAmbientLight,
    AdcCellTherm,
    AdcCellID,
    AdcCellBottom,
    AdcCellTop,
#endif
    AdcCount    // must be last
};

}

#endif // IO_DEFS_H
