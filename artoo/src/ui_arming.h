#ifndef UI_ARMING_H
#define UI_ARMING_H

#include "button.h"
#include "ui_holdprogressbar.h"
#include "gfx.h"

#include "stm32/systime.h"

class UiArming
{
public:
    UiArming();

    static const Gfx::FontAsset & InstructionFont;

    void init();
    void update();

    void onFlyButtonEvt(Button *b, Button::Event evt);
    void onArmFailed();
    void onTakeoffFailed();
    void onArmStateChanged() {
        armStateDirty = true;
    }

private:
    static const unsigned ARMED_LED_BLINK_MILLIS = 100;

    bool progressClearPending;

    void writeWaitingForGps();
    void writeInstructions();
    void drawArmingProgress();
    void clearArmingProgress();

    bool armStateDirty;
    bool waitingForGps;
    unsigned progressW;
    SysTime::Ticks blinkTicker;
    UiHoldProgressBar progressBar;
};

#endif // UI_ARMING_H
