#include "home.h"

Home::Home() :
    location(),
    alt(0)
{
}

bool Home::update(const mavlink_mission_item_t & mi)
{
    /*
     * Update our location based on the given mission item.
     */

    // not the first waypoint?
    if (mi.seq != 0) {
        return false;
    }

    bool changed = false;

    if (location.isEmpty() || location.lat() != mi.x || location.lng() != mi.y) {
        location.set(mi.x, mi.y);
        changed = true;
    }

    if (alt != mi.z) {
        alt = mi.z;
        changed = true;
    }

    return changed;
}
