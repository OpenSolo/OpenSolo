#include "mathx.h"

namespace mathx {

static const float kFeetPerMeter = 3.28083989501;

float metersPerSecToMph(float v) {
    return v * kFeetPerMeter * 3600 / 5280;
}

float metersToFeet(float m) {
    return m * kFeetPerMeter;
}

}
