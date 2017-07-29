#ifndef UIFULLSCREENMODAL_H
#define UIFULLSCREENMODAL_H

#include "ui_events.h"
#include "ui_alert.h"
#include "gfx.h"
#include "stm32/systime.h"

class UiFullScreenModal
{
public:
    UiFullScreenModal();

    void init();
    void dismiss() {
        event = Event::None;
    }

    void onEvent(Event::ID id);
    bool complete() const;

private:

    Event::ID event;
    SysTime::Ticks startTimestamp;
    SysTime::Ticks timeOut;

    inline void drawSingleIcon(const Gfx::ImageAsset & img);
    inline void drawIcons(Event::ID id);
    inline void drawAlertText(const UiAlertManager::Alert & a); 
};

#endif // UIFULLSCREENMODAL_H
