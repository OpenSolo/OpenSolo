#ifndef GEO_H
#define GEO_H

#include "coord2d.h"

/*
 * helpers for geo related tasks.
 * lifted from droidplanner.
 */

namespace geo
{
    const double EARTH_RADIUS_IN_METERS = 6372797.560856;

    double arcInRadians(const Coord2D & a, const Coord2D & b);
    double distanceInMeters(const Coord2D & a, const Coord2D & b);
}

#endif // GEO_H
