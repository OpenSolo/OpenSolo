#ifndef _MOVING_AVG_FILTER_H
#define _MOVING_AVG_FILTER_H

#include "stm32/common.h"

class MovingAvgFilter
{
public:
    MovingAvgFilter();

    static ALWAYS_INLINE uint16_t Alpha(float a) {
        return a * 0xffff;
    }

    void update(int32_t measurement, uint16_t alpha);
    inline int32_t average() const {
        return avg;
    }

private:
    int32_t avg;
};

#endif // _MOVING_AVG_FILTER_H
