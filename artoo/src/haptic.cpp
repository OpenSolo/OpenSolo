#include "haptic.h"
#include "tasks.h"
#include "powermanager.h"

SysTime::Ticks Haptic::stopDeadline;
Haptic::PatternData Haptic::pat;

const uint16_t Haptic::UhUhPattern[] = {
    30,
    80 | OffMask,
    15
};

const uint16_t Haptic::SingleShortPattern[] = {
    20,
};

const uint16_t Haptic::SingleMediumPattern[] = {
    40,
};

const uint16_t Haptic::SingleLongPattern[] = {
    80,
};

const uint16_t Haptic::LightDoublePattern[] = {
    50,
    100 | OffMask,
    50,
};

const uint16_t Haptic::LightTriplePattern[] = {
    50,
    100 | OffMask,
    50,
    100 | OffMask,
    50,
};

const uint16_t Haptic::HeavyTriplePattern[] = {
    100,
    200 | OffMask,
    100,
    200 | OffMask,
    100,
};

void Haptic::init()
{
    VIB_GPIO.setControl(GPIOPin::OUT_2MHZ);
    stop();
}

void Haptic::startPattern(Pattern p)
{
    if (PowerManager::state() != PowerManager::Running) {
        return;
    }

    if (playing()) {
        return;
    }

    switch (p) {
    case SingleShort:
        pat.set(SingleShortPattern, arraysize(SingleShortPattern));
        break;

    case SingleMedium:
        pat.set(SingleMediumPattern, arraysize(SingleMediumPattern));
        break;

    case SingleLong:
        pat.set(SingleLongPattern, arraysize(SingleLongPattern));
        break;

    case UhUh:
        pat.set(UhUhPattern, arraysize(UhUhPattern));
        break;

    case LightDouble:
        pat.set(LightDoublePattern, arraysize(LightDoublePattern));
        break;

    case LightTriple:
        pat.set(LightTriplePattern, arraysize(LightTriplePattern));
        break;

    case HeavyTriple:
        pat.set(HeavyTriplePattern, arraysize(HeavyTriplePattern));
        break;

    default:
        return;
    }

    nextEntry();
}

void Haptic::stop()
{
    Tasks::cancel(Tasks::Haptic);
    pat.cancel();
    motorOff();
}

void Haptic::task()
{
    /*
     * Called periodically to see if it's time
     * to play the next entry.
     *
     * If still waiting for the next entry, reschedule ourselves.
     */

    if (SysTime::now() < stopDeadline) {
        Tasks::trigger(Tasks::Haptic);
        return;
    }

    nextEntry();
}

bool Haptic::playing()
{
    /*
     * Is a pattern still in progress?
     */

    return (!pat.done() || motorIsOn());
}

void Haptic::nextEntry()
{
    if (pat.done()) {
        stop();
        return;
    }

    uint16_t e = pat.next();

    if (e & OffMask) {
        motorOff();
    } else {
        motorOn();
    }

    stopDeadline = SysTime::now() + SysTime::msTicks(e & ~OffMask);
    Tasks::trigger(Tasks::Haptic);
}
