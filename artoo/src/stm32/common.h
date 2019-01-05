#ifndef COMMON_H
#define COMMON_H

#include <stdint.h>
#include <math.h>

#ifndef arraysize
#define arraysize(a)   (sizeof(a) / sizeof((a)[0]))
#endif

#define ALWAYS_INLINE   inline __attribute__ ((always_inline))

#define UNUSED(x)   (void)x

/*
 * Debug printing - only available when built for semihosting.
 * Enable semihosting by editing the top level Tupfile of this project.
 */

#ifdef SEMIHOSTING
#include <stdio.h>
#include <assert.h>
#define DBG(_x) printf _x
#define ASSERT(_x)  assert(_x)
#else
#define DBG(_x)
#define ASSERT(_x)
#endif // SEMIHOSTING

// Produces a 'size of array is negative' compile error when the assert fails
#define STATIC_ASSERT(_x)  ((void)sizeof(char[1 - 2*!(_x)]))

#ifndef MIN
#define MIN(a,b)        ((a)<(b)?(a):(b))
#define MAX(a,b)        ((a)>(b)?(a):(b))
#endif

template <typename T> ALWAYS_INLINE T clamp(T value, T low, T high)
{
    /*
     * Helper to clamp a value between low and high limits.
     */

    if (value < low) {
        return low;
    }

    if (value > high) {
        return high;
    }

    return value;
}

/*
 * Scale 'value' between the ranges specified by minIn/maxIn and minOut/maxOut.
 *
 * 'value' is expected to be in the range minIn - maxIn.
 */
template <typename T> ALWAYS_INLINE T scale(T value, T minIn, T maxIn, T minOut, T maxOut)
{
    ASSERT(minIn <= value && value <= maxIn);

    T rangeIn = (maxIn - minIn);
    ASSERT(rangeIn);
    T rangeOut = (maxOut - minOut);
    return (((value - minIn) * rangeOut) / rangeIn) + minOut;
}

static ALWAYS_INLINE bool isWithin(float v1, float v2, float range)
{
    return fabs(v1 - v2) < range;
}

#endif // COMMON_H
