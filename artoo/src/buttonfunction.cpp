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
