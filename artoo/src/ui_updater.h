#ifndef UI_UPDATER_H
#define UI_UPDATER_H

#include "ui_events.h"
#include "button.h"
#include "gfx.h"

class UiUpdater
{
public:
    UiUpdater();

    void init(Event::ID e);
    bool update();
    bool updateInProgress() const {
        return updateEvent == Event::SystemUpdateBegin;
    }

    bool onButtonEvent(Button *b, Button::Event e);

private:
    Event::ID updateEvent;

    void drawPrimaryMsg(unsigned y, const char *s1, const char *s2, const Gfx::FontAsset & f, uint16_t color);

    void drawUpdateBegin();
    void drawUpdateSuccess();
    void drawUpdateFailed();

    void promptToContinue();
};

#endif // UI_UPDATER_H
