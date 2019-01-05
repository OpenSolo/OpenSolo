#ifndef CAMERA_CONTROL_H
#define CAMERA_CONTROL_H

#include "tween.h"
#include "params.h"
#include "button.h"
#include "movingavgfilter.h"
#include "stm32/common.h"

class CameraControl
{
public:
    static constexpr float MAX_ANGLE = 90;
    static constexpr float MIN_ANGLE = 0;
    static const unsigned MAX_PRESET_MILLIS = 90 * 1000;
    static const unsigned MIN_PRESET_MILLIS = 3 * 1000;

    static constexpr float INIT_ANGLE = 80;

    CameraControl() :
        positionTween(),
        rateTween(),
        rateDialFilt(),
        cameraAngle(0),
        cameraRate(0),
        minSweepMillis(0),
        maxSweepMillis(0),
        inputActive(false),
        sweepSeconds(0),
        nextSweepSeconds(0),
        sweepSecStableCount(0),
        rateDialInputDetected(false),
        lastGimbalWriteTime(0)
    {}

    static CameraControl instance;

    void init();
    void fiftyHzLoop();

    enum PresetID {
        Preset1,
        Preset2
    };

    void task();

    void capturePreset(PresetID id);
    void beginPreset(PresetID id);

    void returnToInit();

    bool isActive() const {
        // paddle or preset is active
        return inputActive || (!positionTween.isDone());
    }

    float angle() const {
        return cameraAngle;
    }

    Params::sweeptime_t minSweep() const {
        return minSweepMillis;
    }

    Params::sweeptime_t maxSweep() const {
        return maxSweepMillis;
    }

    uint16_t targetPosition() const {
        return calcTargetPosition(cameraAngle);
    }

    uint16_t targetPositionDefault() const {
        return calcTargetPosition(defaultCameraAngle);
    }

    unsigned presetSweepMillis() const;
    unsigned presetSweepMillisMax() const;
    unsigned smoothedPresetSweepSeconds() const {
        return sweepSeconds;
    }

    void setSweepConfig(const Params::SweepConfig &c);

    // only intended to be called by ButtonManager
    void onButtonEvt(Button *b, Button::Event evt);

    void onGimbalAngleChanged();

private:
    static constexpr float Preset1Default = 90.0;
    static constexpr float Preset2Default = 0.0;

    // what is currently driving positionTween?
    enum PosTweenSource {
        PosTweenNone,
        PosTweenPreset,         // a preset animation
        PosTweenGimbalFollower, // the gimbal position
        PosTweenReturnInit,     // resetting to init position
    };

    static const Params::sweeptime_t MinSweepSecDefault = 3;
    static const Params::sweeptime_t MaxSweepSecDefault = 90;

    // tune this to set an overall speed for the camera
    static constexpr float cameraGain = 45.0f;

    static constexpr float defaultCameraAngle = 45.0f;

    // should we compute an interval based on how far we have to go?
    // simple approach is just to be constant for now, assuming
    // we won't often be too far from the actual angle.
    static const unsigned GimbalFollowerInterval = 250;

    // we need to wait after user input has stopped before we can start
    // reading the reported angle again, since we only have access to
    // the gimbal's current position, and not its target position
    static const unsigned GimbalFollowLockoutTime = 3000;

    static const unsigned GimbalReturnToInitInterval = 3000;

    static ALWAYS_INLINE PresetID buttonToPreset(Io::ButtonID id) {
        // NB: relies on layout of Io::ButtonID
        return static_cast<PresetID>(id - Io::ButtonPreset1);
    }

    static uint16_t calcTargetPosition(float cameraAngle) {
        return 1000 + (cameraAngle / MAX_ANGLE) * 520;
    }

    void beginEaseToTarget(float targetAngle, unsigned millis, PosTweenSource pts);

    unsigned sweepMillis(float a1, float a2) const;

    float updateCameraRate(float inputRate) const;
    float maxRate(float inputRate) const;

    struct PositionTween {

        Tween tween;
        uint32_t time;
        PosTweenSource src;

        bool isDone() const {
            return tween.isDone(time);
        }

        void init(float initial, float target, float dur, PosTweenSource pts) {
            tween.init(initial, target, dur);
            time = 0;
            src = pts;
        }

        void reset() {
            tween.reset();
            time = 0;
            src = PosTweenNone;
        }

        float step() {
            return tween.easeInOutQuad(time++);
        }

    } positionTween;

    Tween rateTween;

    MovingAvgFilter rateDialFilt;

    float cameraAngle;
    float cameraRate;
    Params::sweeptime_t minSweepMillis;
    Params::sweeptime_t maxSweepMillis;
    bool inputActive;

    unsigned sweepSeconds;
    unsigned nextSweepSeconds;
    unsigned sweepSecStableCount;
    bool rateDialInputDetected;

    SysTime::Ticks lastGimbalWriteTime;
};

#endif // CAMERA_CONTROL_H
