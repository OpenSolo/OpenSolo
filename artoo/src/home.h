#ifndef HOME_H
#define HOME_H

#include "geo.h"

#include "mavlink/c_library/common/mavlink.h"
#include "mavlink/c_library/ardupilotmega/mavlink.h"

/*
 * Simple helper to encapsulate the vehicle's home location.
 *
 * Should be updated to match the first (index 0) waypoint
 * of the vehicle.
 */

class Home
{
public:
    Home();

    const Coord2D & loc() const {
        return location;
    }

    float altitude() const {
        return alt;
    }

    bool update(const mavlink_mission_item_t & mi);

private:
    Coord2D location;
    float alt;
};

#endif // HOME_H
