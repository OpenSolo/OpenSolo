#ifndef TWEEN_H
#define TWEEN_H

#include "stm32/common.h"

/*
 * Easing curves taken from Robert Penner's
 * popular book: http://www.robertpenner.com/easing
 *
 * The different easing curves define functions that return
 * values on the curve for a given point in time.
 */

class Tween {
public:
    void init(float initialValue, float targetValue, float _duration);

    float easeInOutQuad(float time) const;
    float easeOutCirc(float delta) const;
    float easeInOutExpo(float time, unsigned e) const;

    ALWAYS_INLINE bool isDone(float time) const {
        return time >= duration;
    }

    void reset() {
        startValue = 0;
        change = 0;
        duration = 0;
    }

private:
    // these values only change in init()
    float startValue;   // start value of the entity being tweened
    float change;       // 'distance' between start and target value
    float duration;     // duration of tween, in same time units as 'time'
};

#endif // TWEEN_H
