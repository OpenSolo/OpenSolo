#ifndef COORD_2D_H
#define COORD_2D_H

#include "stm32/common.h"

class Coord2D
{
public:
    Coord2D() :
        latitude(0),
        longitude(0)
    {}

    Coord2D(double _lat, double _lng) :
        latitude(_lat),
        longitude(_lng)
    {}

    void ALWAYS_INLINE set(double _lat, double _lng) {
        latitude = _lat;
        longitude = _lng;
    }

    double ALWAYS_INLINE lat() const {
        return latitude;
    }

    double ALWAYS_INLINE lng() const {
        return longitude;
    }

    bool isEmpty() const {
        return latitude == 0 && longitude == 0;
    }

    void clear() {
        latitude = 0;
        longitude = 0;
    }

private:
    double latitude;    // x
    double longitude;   // y
};

#endif // COORD_2D_H
