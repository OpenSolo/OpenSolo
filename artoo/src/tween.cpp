#include "tween.h"

#include <math.h>

void Tween::init(float initialValue, float targetValue, float _duration)
{
    startValue = initialValue;
    change = targetValue - initialValue;
    duration = _duration;
}

float Tween::easeInOutQuad(float time) const
{
    time /= duration / 2;

    if (time < 1) {
        return ((change / 2) * (time * time)) + startValue;
    }

    time--;
    return ((-change / 2) * (time * (time - 2) - 1)) + startValue;
}

float Tween::easeInOutExpo(float time, unsigned e) const
{
    time /= duration / 2;

    if (time < 1) {
        return change/2.0 * pow(time, e) + startValue;
    }

    return change/2 * (pow(time - 2.0, e) + 2.0) + startValue;
}

float Tween::easeOutCirc(float delta) const
{
    return sqrt(1 - ((delta - 1) * (delta - 1)));
}
