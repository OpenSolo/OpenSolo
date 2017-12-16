#include "buttonfunction.h"
#include "haptic.h"
#include "flightmanager.h"
#include "params.h"

ButtonFunction::Config & ButtonFunction::get(Io::ButtonID id) {
    ASSERT(validId(id));
    return Params::sys.storedValues.buttonConfigs[id - Io::ButtonLoiter];
}

void ButtonFunction::onButtonEvent(Button *b, Button::Event e)
{
    /*
     * If a button function button was pressed and it's disabled,
     * provide a little haptic feedback.
     *
     * If the vehicle is not connected, don't bother,
     * since this feedback is mainly intended to communicate
     * that an action that *could* be available is not at the moment.
     */

    if (!FlightManager::instance.linkIsConnected()) {
        return;
    }

    if (!validId(b->id())) {
        return;
    }

    if (e != Button::ClickRelease) {
        return;
    }

    if (!get(b->id()).enabled()) {
        Haptic::startPattern(Haptic::UhUh);
    }
}

void ButtonFunction::onButtonExtEvent(Button *b, Button::Event e)
{
    // Provides short haptic feedback at the hold and long hold durations
    // so the user knows they've held the button for the proper durations.
    UNUSED(b);
    if ( e == Button::LongHold || e == Button::Hold ) {
        Haptic::startPattern(Haptic::SingleShort);
    }
}
