
// Original code by Jason Short.

#include "stickaxis.h"
#include "ui.h"
#include "inputs.h"

#include "stm32/common.h"
#include "stm32/adc.h"

#include <math.h>
#include <limits.h>

StickAxis::StickAxis(Io::AdcID id, Direction d, uint16_t _dz) :
    rawID(id),
    dir(d),
    minVal(0xffff),
    trim(0x76a),
    maxVal(0),
    expo(0),
    lastVal(0),
    dz(_dz),
    expoPrecalc(0),
    calibrated(false)
{}

void StickAxis::init(const Params::StickCalibration &sc, const Params::StickConfig &c)
{
    setConfig(c);
    setCalibration(sc);
}

void StickAxis::update(uint16_t v)
{
    /*
     * Process a new incoming sample.
     */

    if (calibrated) {
        if (valueIsAcceptable(v)) {
            lastVal = v;
        } else {
            // alert the app of the stick input value discrepancy
            Inputs::onInvalidStickInput(rawID, v, trim, minVal, maxVal);
        }
    } else {
        // not calibrated, adjust extremes based on observed values
        lastVal = v;

        if (v < minVal) {
            minVal = v;
        }

        if (v > maxVal) {
            maxVal = v;
        }

        // always report uncalibrated sticks as an error
        Inputs::onInvalidStickInput(rawID, v, 0xffff, 0xffff, 0xffff);
    }
}

void StickAxis::setCalibration(const Params::StickCalibration &sc)
{
    if (sc.isValid()) {
        minVal = sc.minVal;
        trim = sc.trim;
        maxVal = sc.maxVal;

        calibrated = true;

    } else {
        calibrated = false;
    }
}

void StickAxis::setConfig(const Params::StickConfig &c)
{
    setExponent((c.expo == 0xff) ? defaultExpo() : c.expo);

    if (c.direction != 0xff) {
        setDirection(c.direction ? Forward : Reverse);
    }
}

unsigned StickAxis::defaultExpo() const
{
    /*
     * Set a default expo, per axis.
     * This will be overridden by stick config info in params.
     */

    switch (Inputs::mappedStickID(rawID)) {
    case Io::StickRoll:
    case Io::StickPitch:
        return 30;

    case Io::StickYaw:
        return 50;

    case Io::StickThro:
        return 40;

    case Io::StickGimbalY:
        return 100;

    default:
        return DefaultExpo;
    }
}

void StickAxis::setExponent(uint8_t e)
{
    expo = clamp(e, uint8_t(0), uint8_t(100));
    expoPrecalc = pow(4.0, (float)expo / 100.0);
}

bool StickAxis::valueIsAcceptable(uint16_t rawVal) const
{
    /*
     * check for pathologically out of range values,
     * suggests a re-cal is required.
     *
     * Will only give reasonable results when this axis has
     * been calibrated successfully.
     *
     * we specify a rough percentage beyond the calibrated range
     * that we consider invalid.
     */

    static const unsigned VALID_INPUT_PERCENT = 5;
    const int thresh = int32_t(maxVal - minVal) * VALID_INPUT_PERCENT / 100;

    if (rawVal < minVal) {
        // is there enough raw range to allow for a bad value?
        const int minThresh = int(minVal) - thresh;
        if (minThresh < 0) {
            return true;
        }
        return rawVal >= minThresh;

    } else if (rawVal > maxVal) {
        // is there enough raw range to allow for a bad value?
        const int maxThresh = int(maxVal) + thresh;
        if (maxThresh >= Adc::RawRange) {
            return true;
        }
        return rawVal <= maxThresh;
    }

    // within calibrated range, all good
    return true;
}

float StickAxis::angularValue() const
{
    /*
     *
     */

    float v;
    const uint16_t trimHigh = trim + dz;
    const uint16_t trimLow  = trim - dz;

    if (lastVal > trimHigh) {
        v = (float)(lastVal - trimHigh) / (float)(maxVal - trimHigh);

    } else if (lastVal < trimLow) {
        v = -((float)(trimLow - lastVal)) / (float)(trimLow - minVal);

    } else {
        // we're in the dead zone
        return 0.0f;
    }

    v = clamp(v * dir, -1.0f, 1.0f);

    if (v < 0) {
        return -(pow(-v, expoPrecalc));
    }

    return pow(v, expoPrecalc);
}

float StickAxis::linearValue() const
{
    /*
     * Return the input as a linear value, from 0.0-1.0.
     */

    float v = float(lastVal - minVal) / float(maxVal - minVal);
    v = clamp(v, 0.0f, 1.0f);

    if (dir == Forward) {
        return v;
    }
    return 1.0 - v;
}

bool StickAxis::hasInvalidInput() const {
    return Inputs::stickValueInvalid(rawID);
}
