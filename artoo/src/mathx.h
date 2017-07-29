#ifndef MATHX_H
#define MATHX_H

#include "stm32/common.h"

/*
 * math extras
 */

namespace mathx {

const double PI   = 3.141592653589793238463;
const float  PI_F = 3.14159265358979f;

double ALWAYS_INLINE radians(double d) {
    return d * PI / 180.0;
}

double ALWAYS_INLINE degrees(double r) {
    return r * 180.0 / PI;
}

float ALWAYS_INLINE sq(float v) {
    return v*v;
}

float metersPerSecToMph(float v);
float metersToFeet(float m);

} // namespace mathx

#endif // MATHX_H
