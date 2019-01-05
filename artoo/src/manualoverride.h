#ifndef _MANUAL_OVERRIDE_H
#define _MANUAL_OVERRIDE_H

#include "button.h"

/*
 * Manual override manages state that is used to trigger
 * a manual flight mode, even when there's no mobile app
 * to configure button functions - ie, during manufacturing.
 *
 * When enabled, button event reporting is suppressed, and
 * we trigger an AltHold mode change request on A button
 * click events.
 */

class ManualOverride
{
public:
    ManualOverride(); // not implemented

    static void onButtonEvent(Button *b, Button::Event e);
    static inline bool isEnabled() {
        return enabled;
    }

private:
    static bool enabled;
};

#endif // _MANUAL_OVERRIDE_H
