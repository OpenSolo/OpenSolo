#include "geo.h"

#include <math.h>
#include "mathx.h"

namespace geo {

double arcInRadians(const Coord2D & a, const Coord2D & b)
{
    /*
     * Calculates the arc between two points
     * http://en.wikipedia.org/wiki/Haversine_formula
     */

    double latArc = mathx::radians(a.lat() - b.lat());
    double lngArc = mathx::radians(a.lng() - b.lng());

    double latH = sin(latArc * 0.5);
    latH *= latH;

    double lngH = sin(lngArc * 0.5);
    lngH *= lngH;

    double tmp = cos(mathx::radians(a.lat())) * cos(mathx::radians(b.lat()));
    return 2.0 * asin(sqrt(latH + tmp * lngH));
}

double distanceInMeters(const Coord2D & a, const Coord2D & b)
{
    /*
     * compute the distance between 2 coordinates.
     */

    return EARTH_RADIUS_IN_METERS * arcInRadians(a, b);
}

} // namespace geo
