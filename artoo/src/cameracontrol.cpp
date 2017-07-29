
// Adapted from code by Jason Short

#include "cameracontrol.h"
#include "inputs.h"
#include "haptic.h"
#include "idletimeout.h"
#include "ui.h"
#include "sologimbal.h"

#include <math.h>
#include <float.h>

CameraControl CameraControl::instance;

void CameraControl::init()
{
    cameraAngle = INIT_ANGLE;

    positionTween.reset();
    rateTween.init(0, 45, 45);

    Params::StoredValues & sv = Params::sys.storedValues;
    if (!(sv.presets[Preset1].isValid() && sv.presets[Preset2].isValid())) {
        sv.presets[Preset1].targetPos = Preset1Default;
        sv.presets[Preset2].targetPos = Preset2Default;
    }

    if (!sv.sweepConfig.isValid()) {
        sv.sweepConfig.minSweepSec = MinSweepSecDefault;
        sv.sweepConfig.maxSweepSec = MaxSweepSecDefault;
    }

    setSweepConfig(sv.sweepConfig);
}

void CameraControl::capturePreset(PresetID id)
{
    Params::sys.storedValues.presets[id].targetPos = cameraAngle;

    Params::sys.mark();
    Haptic::startPattern(Haptic::SingleMedium);
    Ui::instance.pendEvent(Event::GimbalInput);
}

void CameraControl::fiftyHzLoop()
{
    /*
     * Intended to be called at 50Hz
     */

    StickAxis &gimbalRate = Inputs::stick(Io::StickGimbalY);
    float inputRate = gimbalRate.angularValue();

    if (rateDialInputDetected) {
        rateDialInputDetected = false;
        Ui::instance.pendEvent(Event::GimbalInput);
    }

    bool newInputActive = (inputRate != 0.0f);
    if (inputActive != newInputActive) {
        inputActive = newInputActive;
        if (inputActive) {
            lastGimbalWriteTime = SysTime::now();
            Ui::instance.pendEvent(Event::GimbalInput);
        }
    }

    // exit if the user inputs
    if (inputActive) {
        positionTween.reset();
        IdleTimeout::reset();
    }

    float newAngle;

    if (!positionTween.isDone()) {
        newAngle = positionTween.step();
        lastGimbalWriteTime = SysTime::now();

    } else {
        cameraRate = updateCameraRate(inputRate);
        newAngle = cameraAngle + cameraRate * .02;
    }

    newAngle = clamp(newAngle, MIN_ANGLE, MAX_ANGLE);
    if (inputActive && !Ui::instance.gimbal.isSuppressed()) {
        if (!isWithin(cameraAngle, newAngle, FLT_EPSILON)) {
            // can use == here since the value is explicitly set via clamp()
            if ((newAngle == MIN_ANGLE) || (newAngle == MAX_ANGLE)) {
                Haptic::startPattern(Haptic::SingleShort);
            }
        }
    }
    cameraAngle = newAngle;
}

void CameraControl::task()
{
    /*
     * Called from task context, do periodic work.
     *
     * Primarily, look for user input on the rate dial.
     */

    static const unsigned STABLE_THRESH = 15;

    unsigned millis = presetSweepMillis();
    rateDialFilt.update((millis + 500) / 1000, MovingAvgFilter::Alpha(0.7));

    unsigned seconds = rateDialFilt.average();

    if (seconds == sweepSeconds) {
        sweepSecStableCount = 0;
        return;
    }

    if (seconds == nextSweepSeconds) {
        if (++sweepSecStableCount >= STABLE_THRESH) {
            sweepSecStableCount = 0;
            sweepSeconds = seconds;
            rateDialInputDetected = true;
        }
    } else {
        nextSweepSeconds = seconds;
        sweepSecStableCount = 0;
    }
}

void CameraControl::onButtonEvt(Button *b, Button::Event evt)
{
    switch (b->id()) {
    case Io::ButtonPreset1:
    case Io::ButtonPreset2:
        switch (evt) {
        case Button::ClickRelease:
            beginPreset(buttonToPreset(b->id()));
            break;

        case Button::Hold:
            capturePreset(buttonToPreset(b->id()));
            break;

        default:
            break;
        }
        break;
    default:
        break;
    }
}

void CameraControl::onGimbalAngleChanged()
{
    /*
     * The gimbal is controlled by artoo in 2 ways mainly:
     * rate control from the paddle, and preset animations.
     * If neither of these are active, we assume the gimbal
     * is being controlled by something else (cable cam, etc).
     * In this case, we follow the angle reported by the gimbal.
     */

    const SoloGimbal & sg = SoloGimbal::instance;

    if (!sg.angleIsValid()) {
        return;
    }

    /*
     * defer to user input
     *
     * HACK - wait a period of time after user input before we start
     * following again, since user input can take some time before the
     * gimbal reaches the requirested position. Since we don't have
     * exclusive access to the gimbal, we don't know whether somebody
     * else is controlling it, so we can't just wait for it to reach
     * our requested position.
     */
    if (SysTime::now() - lastGimbalWriteTime < SysTime::msTicks(GimbalFollowLockoutTime)) {
        return;
    }

    // defer to ongoing preset animation
    if (!positionTween.isDone()) {
        if (positionTween.src != PosTweenGimbalFollower) {
            return;
        }
    }

    // XXX: the camera UI reports angle incorrectly.
    //      apply an offset to be consistent with camera UI,
    //      but should ultimately update camera UI to reflect
    //      gimbal reality.
    float a = sg.reportedAngle() - SoloGimbal::ANGLE_MIN;
    beginEaseToTarget(a, GimbalFollowerInterval, PosTweenGimbalFollower);
}

void CameraControl::returnToInit()
{
    if (isActive()) {
        return;
    }

    beginEaseToTarget(INIT_ANGLE, GimbalReturnToInitInterval, PosTweenReturnInit);
}

unsigned CameraControl::presetSweepMillis() const
{
    /*
     * return the time in milliseconds to sweep between our 2 presets.
     */

    Params::CameraPreset &p1 = Params::sys.storedValues.presets[Preset1];
    Params::CameraPreset &p2 = Params::sys.storedValues.presets[Preset2];

    ASSERT(p1.isValid() && p2.isValid());

    return clamp(sweepMillis(p1.targetPos, p2.targetPos), (unsigned)minSweepMillis, (unsigned)maxSweepMillis);
}

unsigned CameraControl::presetSweepMillisMax() const
{
    /*
     * For the given presets, what is the maximum preset sweep time,
     * regardless of the rate dial?
     */

    Params::CameraPreset &p1 = Params::sys.storedValues.presets[Preset1];
    Params::CameraPreset &p2 = Params::sys.storedValues.presets[Preset2];

    ASSERT(p1.isValid() && p2.isValid());

    float distanceScale = fabs(p1.targetPos - p2.targetPos) / MAX_ANGLE;
    return minSweepMillis + (distanceScale * (maxSweepMillis - minSweepMillis));
}

unsigned CameraControl::sweepMillis(float a1, float a2) const
{
    /*
     * Calculate the time in milliseconds it will take to sweep
     * between the given angles.
     */

    float rate = Inputs::stick(Io::StickGimbalRate).linearValue();
    float maxTime = minSweepMillis + (rate * (maxSweepMillis - minSweepMillis));

    float distanceScale = fabs(a1 - a2) / MAX_ANGLE;

    return maxTime * distanceScale;
}

void CameraControl::setSweepConfig(const Params::SweepConfig &c)
{
    minSweepMillis = c.minSweepSec*1000;
    maxSweepMillis = c.maxSweepSec*1000;
}

void CameraControl::beginPreset(PresetID id)
{
    /*
     * A preset has been triggered.
     *
     * Configure our position tween to run from the current camera angle
     * to the angle specified by the preset, at a speed specified by
     * a snapshot of the rate slider.
     */

    Params::CameraPreset &preset = Params::sys.storedValues.presets[id];
    if (!preset.isValid()) {
        return;
    }

    unsigned duration = sweepMillis(preset.targetPos, cameraAngle);
    beginEaseToTarget(preset.targetPos, duration, PosTweenPreset);

    Ui::instance.pendEvent(Event::GimbalInput);
}

void CameraControl::beginEaseToTarget(float targetAngle, unsigned millis, PosTweenSource pts)
{
    /*
     * Use the position tween to ease from the current angle
     * to the given target in 'millis' milliseconds.
     */

    // don't bother if we're already close enough
    if (isWithin(cameraAngle, targetAngle, 1.0f)) {
        return;
    }

    const float updateInterval = 1000 / 50;   // running @ 50Hz
    const float duration = millis / updateInterval;

    positionTween.init(cameraAngle, targetAngle, duration, pts);
}

float CameraControl::updateCameraRate(float inputRate) const
{
    /*
     * Update the camera rate, based on the current stick input.
     */
    
    float desiredRate = maxRate(inputRate) * (inputRate * cameraGain);

    // limit acceleration
    if (desiredRate > cameraRate) {
        desiredRate = MIN(cameraRate + 6, desiredRate);
    } else if (desiredRate < cameraRate) {
        desiredRate = MAX(cameraRate - 6, desiredRate);
    }

    return desiredRate;
}

float CameraControl::maxRate(float inputRate) const
{
    /*
     * Calculate a new maximum rate for the camera.
     *
     * The camera's max allowed rate is related to is position.
     * It is fastest in the middle of its range of travel (45 degrees)
     * and eases down its rate circularly towards either edge.
     */

    float newSpeed;
    float margin = 30;

    // up
    if (cameraAngle < margin && inputRate < 0) {
        newSpeed = rateTween.easeOutCirc(cameraAngle / margin);

    // down
    } else if (cameraAngle > 90 - margin && inputRate > 0) {
        newSpeed = rateTween.easeOutCirc((90 - cameraAngle) / margin);
        
    } else {
        newSpeed = 1;
    }

    return newSpeed;
}
