#ifndef UI_H
#define UI_H

#include "ui_telemetry.h"
#include "ui_arming.h"
#include "ui_pairing.h"
#include "ui_gimbal.h"
#include "ui_alert.h"
#include "ui_splash.h"
#include "ui_power.h"
#include "ui_updater.h"
#include "ui_events.h"
#include "ui_fullscreenmodal.h"
#include "ui_topbar.h"
#include "powermanager.h"
#include "ringbuffer.h"
#include "machine.h"

#include "stm32/systime.h"

class Ui
{
public:

    enum State {
        PowerDown,
        Splash,
        WaitForSolo,
        Arming,
        Telem,
        Pairing,
        Gimbal,
        FullscreenAlert,
        Updater,
        Lockout,    // temp
        Shutdown,
    };

    Ui();

    static Ui instance;

    void init();
    void update();

    void setBacklightsForState(PowerManager::SysState s);

    State state() const {
        return currentState;
    }

    bool canProcessAlerts();

    void ALWAYS_INLINE pendEvent(Event::ID id) {
        if (events.full()) {
            DBG(("event queue full, event (%d) dropped!\n", id));
            return;
        }

        if (Event::isAlert(id) && !canProcessAlerts()) {
            return;
        }
        events.enqueue(id);
    }

    SysTime::Ticks ALWAYS_INLINE stateStartTime() const {
        return stateEnterTimestamp;
    }

    UiTelemetry telem;
    UiArming arming;
    UiPairing pairing;
    UiGimbal gimbal;
    UiSplash splash;
    UiPower power;
    UiUpdater updater;
    UiAlertManager alertManager;
    UiFullScreenModal fullscreenmodal;
    UiTopBar topBar;

    static const unsigned PrimaryMsgY = 130;
    static void writePrimaryMsg(const char * first, const char * rest, const Gfx::FontAsset & font,
                                uint16_t * color_fg, uint16_t * color_bg, unsigned y = PrimaryMsgY);

    static const unsigned DefaultFlyBtnY = 88;
    static const unsigned DefaultKillSwitchY = 85;
    // offset to align text within fly btn img with rendered text
    static const unsigned FlyBtnTextOffset = 6;
    static void writeFlyBtnInstructions(const char *pre, const char *post,
                                        unsigned y = DefaultFlyBtnY);
    static void writeKillSwitchInstructions(const char *pre, const char *post,
                                        unsigned y = DefaultKillSwitchY);

    // common UI element params
    static const unsigned HintBoxY = 185;
    static const unsigned HintBoxBorderWeight = 2;
    static const unsigned HintBoxMargin = 20;
    static const unsigned HintBoxYLine1of1 = HintBoxY + 20;
    static const unsigned HintBoxYLine1of2 = HintBoxY + 9;
    static const unsigned HintBoxYLine2of2 = HintBoxYLine1of2 + 18;

private:
    static const unsigned MaxFrameRate = 30;

    // this currently provides an 8-bit id for all events
    // which is enough for now... I fear the day that we need to
    // increase this :)
    RingBuffer<32> events;
    State currentState;
    State pendingState;
    SysTime::Ticks stateEnterTimestamp;
    SysTime::Ticks lastRender;

    void processEvents();
    void processEvent(Event::ID id);
    void processAlert(Event::ID id);
    void initFullscreenAlert(Event::ID id);
    bool canTransition(State from, State to);
    uint32_t ALWAYS_INLINE BIT(State s) {
        return (1 << s);
    }

    void drawWaitingForSolo();
    void drawLockout();

    State determineState();
};

#endif // UI_H
