#ifndef STICKAXIS_H
#define STICKAXIS_H

#include "params.h"
#include "stm32/common.h"

/*
 * A StickAxis represents a single continuous control axis
 * on one of the input sticks.
 *
 * Original code by Jason Short.
 */

class StickAxis
{
public:
    // dead zones for RC channels are handled on the vehicle
    static const unsigned RcChannelDeadZone = 1;
    // gimbal pitch needs a real dead zone, since we're handling it ourselves
    static const unsigned GimbalPitchDeadZone = 250;

    enum Direction {
        Reverse = -1,
        Forward = 1
    };

    StickAxis(Io::AdcID id, Direction d, uint16_t _dz);

    void init(const Params::StickCalibration &sc, const Params::StickConfig &c);
    void setCalibration(const Params::StickCalibration &sc);
    void setConfig(const Params::StickConfig &c);
    void update(uint16_t v);

    Io::AdcID ALWAYS_INLINE getRawID() const {
        return rawID;
    }

    void setDirection(Direction d) {
        dir = d;
    }
    Direction direction() const {
        return dir;
    }

    void setDeadZone(uint16_t _dz) {
        dz = _dz;
    }
    uint16_t deadZone() const {
        return dz;
    }

    void setExponent(uint8_t e);
    uint8_t exponent() const {
        return expo;
    }

    uint16_t ALWAYS_INLINE rawValue() const {
        return lastVal;
    }

    float angularValue() const;
    static ALWAYS_INLINE unsigned toPPM(float v) {
        /*
         * convert an angular value to PPM if desired.
         * range is from 1000 - 2000.
         */
        return 1500 + (v * 500.0f);
    }

    uint16_t ALWAYS_INLINE angularPPMValue() const {
        return toPPM(angularValue());
    }

    uint16_t ALWAYS_INLINE angularPPMDefault() const {
        return toPPM(0);
    }

    uint16_t ALWAYS_INLINE scaledAngularValue() const {
        // 0 - 1000
        return 500 + (angularValue() * 500.0);
    }

    uint16_t ALWAYS_INLINE scaledAngularDefault() const {
        return 500;
    }

    float linearValue() const;

    uint16_t ALWAYS_INLINE scaledLinearValue() const {
        // 0 - 1000
        return linearValue() * 1000.0;
    }

    uint16_t ALWAYS_INLINE scaledLinearDefault() const {
        return 500;
    }

    bool hasInvalidInput() const;

private:
    static const unsigned DefaultExpo = 2;

    Io::AdcID rawID;
    Direction dir;

    uint16_t minVal;    // lowest value seen
    uint16_t trim;      // calibrated mid-point of our stick
    uint16_t maxVal;    // highest value seen
    uint8_t  expo;
    uint16_t lastVal;   // most recent ADC sample

    uint16_t dz;        // dead zone around trim
    float    expoPrecalc;

    bool calibrated;    // was calibration successfully applied?

    unsigned defaultExpo() const;

    bool valueIsAcceptable(uint16_t rawVal) const;
};

#endif // STICKAXIS_H
