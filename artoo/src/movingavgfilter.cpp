#include "movingavgfilter.h"

#include <limits.h>

MovingAvgFilter::MovingAvgFilter() :
    avg(0)
{
}

void MovingAvgFilter::update(int32_t measurement, uint16_t alpha)
{
    /*
     * Lightweight fixed point filter.
     */

    // 100% weight on most recent sample? store it directly
    if (alpha == USHRT_MAX) {
        avg = measurement;
        return;
    }

    int64_t tmp = (int64_t)measurement * (alpha + 1) + avg * (USHRT_MAX - alpha);
    avg = (tmp + 32768) / 65536;
}
