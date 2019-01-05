#include "analyzervehicle_copter.h"

using namespace AnalyzerVehicle;

bool Copter::param_default(const char *name, float &ret)
{
    if (_frame_type == frame_type_quad) {
        if (_param_defaults_quad[name]) {
            ret = _param_defaults_quad[name];
            return true;
        }
    }
    if (_param_defaults[name]) {
        ret = _param_defaults[name];
        return true;
    }
    return Base::param_default(name, ret);
}

/* I think there's an argument for moving the following into Analyzer: */

bool Copter::is_flying()
{
    if (!is_armed()) {
        // we hope we're not flying, anyway!
        return false;
    }

    if (!any_motor_running_fast()) {
        return false;
    }

    return true;
}

bool Copter::any_motor_running_fast()
{
    for (uint8_t i = 1; i < _num_motors; i++) {
        if (_servo_output[i] > is_flying_motor_threshold) {
            return true;
        }
    }
    return false;
}

std::set< uint8_t > Copter::motors_clipping_high()
{
    std::set< uint8_t > ret;
    char label[] = "RCx_MAX";
    for (uint8_t i = 1; i <= _num_motors; i++) {
        label[2] = '0' + i;
        float max;
        if (param(label, max)) {
            uint16_t delta = abs((int32_t)_servo_output[i] - (uint16_t)max);
            if ((float)delta / max < .05) { // within 5%
                ret.insert(i);
            }
        }
    }
    return ret;
}

std::set< uint8_t > Copter::motors_clipping_low()
{
    std::set< uint8_t > ret;
    char label[] = "RCx_MIN";
    for (uint8_t i = 1; i <= _num_motors; i++) {
        label[2] = '0' + i;
        float min;
        if (param(label, min)) {
            if (_servo_output[i] < (uint16_t)min ||
                _servo_output[i] - min < 105) { // FIXME: constant
                ret.insert(i);
            }
            // uint16_t delta = abs((int32_t)_servo_output[i] - (uint16_t)min);
            // ::fprintf(stderr, "%d delta=%d (%f)\n", i, delta, (float)delta/min);
            // if ((float)delta/min < .05) {
            //     ::fprintf(stderr, "%d clipping low \n", i);
            //     ret.insert(i);
            // }
        }
    }
    return ret;
}

void Copter::set_frame_type(copter_frame_type frame_type)
{
    _frame_type = frame_type;
    switch (frame_type) {
    case frame_type_quad:
        _num_motors = 4;
        break;
    case frame_type_y6:
        _num_motors = 6;
        break;
    case invalid:
        ::fprintf(stderr, "Invalid frame type");
        abort();
    }
}

bool Copter::exceeding_angle_max()
{
    float angle_max; // convert from centidegrees
    if (param_with_defaults("ANGLE_MAX", angle_max)) {
        angle_max /= 100;
        if (fabs(att().roll()) > angle_max) {
            return true;
        }
        if (fabs(att().pitch()) > angle_max) {
            return true;
        }
    }
    return false;
}

void Copter::set_frame(const char *frame_config_string)
{
    if (strstr(frame_config_string, "QUAD")) {
        set_frame_type(AnalyzerVehicle::Copter::frame_type_quad);
    } else if (strstr(frame_config_string, "Y6")) {
        set_frame_type(AnalyzerVehicle::Copter::frame_type_y6);
    } else {
        ::fprintf(stderr, "Unknown frame (%s)\n", frame_config_string);
        abort();
    }
}
