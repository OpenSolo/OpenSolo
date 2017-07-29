#ifndef PARAMS_H
#define PARAMS_H

#include "buttonfunction.h"
#include "tasks.h"

#include "stm32/mcuflash.h"
#include "stm32/systime.h"
#include "stm32/common.h"

/*
 * Params manages configuration data that must be stored
 * persistently, such as calibration and presets.
 */

class Params
{
public:

    // single instance of Params - made static so ISRs that would like to
    // update params data can do so, then request a save() at some later date.
    static Params sys;

    typedef uint32_t sweeptime_t;

    // only intended to be accessed as a member of storedValues
    struct StickCalibration {
        uint16_t minVal;
        uint16_t trim;
        uint16_t maxVal;

        ALWAYS_INLINE bool isValid() const {
            return isInitialized(this, sizeof(struct StickCalibration));
        }
    };

    // only intended to be accessed as a member of storedValues
    struct CameraPreset {
        float targetPos;

        ALWAYS_INLINE bool isValid() const {
            return isInitialized(this, sizeof(struct CameraPreset));
        }
    };

    // only intended to be accessed as a member of storedValues
    struct SweepConfig {
        sweeptime_t minSweepSec;
        sweeptime_t maxSweepSec;

        ALWAYS_INLINE bool isValid() const {
            return isInitialized(this, sizeof(struct SweepConfig));
        }
    };

    // only intended to be accessed as a member of storedValues
    struct StickConfig {
        uint8_t input;      // which ADC input to use for this stick
        uint8_t direction;  // forward (non-zero) / reverse (zero)
        uint8_t expo;
        uint8_t reserved1;
        uint32_t reserved2;

        ALWAYS_INLINE bool isValid() const {
            return isInitialized(this, sizeof(struct StickConfig));
        }
    };

    // memory that will be persisted to/read from flash
    struct StoredValues {
        StickCalibration sticks[6]; // ordered per Io::StickID
        CameraPreset presets[2];    // ordered per CameraControl::PresetID
        StickConfig rcSticks[6];    // which sticks to use for throttle, yaw, pitch, roll
        ButtonFunction::Config buttonConfigs[3];
        SweepConfig sweepConfig;    // camera sweep params
    } storedValues;

    void load();
    bool save();
    void mark() {
        dirty = true;
    }

    void periodicWork();

    static bool isInitialized(const void *m, unsigned len);

private:
    // we store our data in the last page of internal flash
    static const unsigned ParamsPageAddr = McuFlash::END_ADDR - McuFlash::PAGE_SIZE;

    // sync params once a second
    static const unsigned SYNC_MILLIS = 1000;

    bool dirty;
    SysTime::Ticks syncDeadline;
};

#endif // PARAMS_H
