#ifndef IDLETIMEOUT_H
#define IDLETIMEOUT_H

#include "tasks.h"
#include "button.h"

class IdleTimeout
{
public:

    static void reset();
    static void tick();

    static void onButtonEvent(Button * b, Button::Event e);

private:
    IdleTimeout(); // don't implement

    // shutdown after 10 minutes of no user input
    static const unsigned IDLE_WARN     = Tasks::HEARTBEAT_HZ * 60 * 10;
    static const unsigned IDLE_TIMEOUT  = IDLE_WARN + Tasks::HEARTBEAT_HZ * 7;

    static bool enabled();

    static unsigned ticker;
    static bool userDisabled;
};

#endif // IDLETIMEOUT_H
