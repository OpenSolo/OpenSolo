#include "manualoverride.h"
#include "buttonmanager.h"
#include "haptic.h"

bool ManualOverride::enabled;

void ManualOverride::onButtonEvent(Button *b, Button::Event e)
{
    UNUSED(b);
    UNUSED(e);

    if (enabled) {
        return;
    }

    // we're not yet enabled,
    // look for a an override button combo
    if (ButtonManager::button(Io::ButtonA).isHeldLong() &&
        ButtonManager::button(Io::ButtonB).isHeldLong() &&
        ButtonManager::button(Io::ButtonFly).isHeldLong() &&
        ButtonManager::button(Io::ButtonRTL).isHeldLong() &&
        ButtonManager::button(Io::ButtonLoiter).isHeldLong())
    {
        Haptic::startPattern(Haptic::SingleMedium);
        enabled = true;
    }
}
