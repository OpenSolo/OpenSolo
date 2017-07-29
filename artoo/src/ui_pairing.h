#ifndef UI_PAIRING_H
#define UI_PAIRING_H

#include "ui_events.h"
#include "gfx.h"

#include "stm32/systime.h"

class UiPairing
{
public:
    UiPairing();

    void init();
    bool update();

    void onPairingEvent(Event::ID e) {
        event = e;
    }

private:
    Event::ID event;
    SysTime::Ticks msgTimeout;

    void drawPairing();
    void drawInProgress();
    void drawSuccess();
    void drawCanceled();
    void drawIncomplete();
};

#endif // UI_PAIRING_H
