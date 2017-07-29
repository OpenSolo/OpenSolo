#ifndef _UI_BOTTOMBOX_H
#define _UI_BOTTOMBOX_H

#include "ui_events.h"
#include "gfx.h"
#include "buttonfunction.h"
#include "ui_alert.h"

#include "stm32/systime.h"

class UiBottomBox
{
public:
    UiBottomBox();

    enum Interactivity { // TODO: depending if we want "Press B to dismiss" type messages, we might need this later, otherwise take this and corresponding code out
        NoUserInput,
        UserDismiss
    };

    enum DisplayState {
        DisplayNone,
        DisplayArming,
        DisplayGimbal,
        DisplayTelem,
        //DisplayAlert,
        //DisplayBackgroundAlert
    };

    enum DrawFunction {
        DrawNothing,
        DrawABButtons,
        DrawGimbalPresets,
        DrawGimbalNotConnected,
        DrawAlert,
        DrawPersistentAlert,
        DrawInvalidFlightControls,
        DrawInvalidCameraControls
    };

    void init(DisplayState state);
    void update();
    void onEvent(Event::ID id);
    void onButtonFunctionsChanged() {
        buttonFunctionsDirty = true;
    }

    void onGimbalFunctionsChanged() {
        gimbalFunctionsDirty = true;
    }

    void updateAlertParams();

private:

    bool alertFunctionsDirty;
    bool buttonFunctionsDirty;
    bool gimbalFunctionsDirty;
    bool persistFunctionsDirty;
    Event::ID event;
    SysTime::Ticks alertStateTransition;
    unsigned alertWaitDurationMillis;
    bool alertNotify;
    DisplayState displayState;
    DrawFunction defaultDrawFunction;
    DrawFunction activeDrawFunction;

    struct Msg {
        Event::ID event;
        Interactivity interactivity;
        unsigned durationMillis;
        const char *content_line1;
        const char *content_line2;
    };

    static const Msg msgs[];
    static const uint8_t MSG_INVALID = 0;
    bool isValid(const Msg &msg){
        return msg.event != msgs[MSG_INVALID].event;
    }

    const UiBottomBox::Msg & findMsg(Event::ID id);

    void drawFunction(DrawFunction fn);

    void clear(uint16_t color = 0x0);
    void setDefaultDisplay();
    void dirtyDisplay();
    void switchToDefaultDisplay();
    void defaultDraw();
    void drawBottomBox();
    void drawGimbalNotConnected();
    void drawPersistentAlert(Event::ID id);
    void drawAlertMsg(const UiAlertManager::Alert & alert, const Msg & msg);
    void drawBannerMsg(const char* content_line1, const char* content_line2, const UiAlertManager::Severity severity);
    void drawBannerMsg(const char* content_line1, const char* content_line2, const uint16_t color, const Gfx::FontAsset &font);
    void drawButtons();
    void drawHintBoxAndCamera();

    const Gfx::ImageAsset & btnImgForConfig(Io::ButtonID id, const ButtonFunction::Config & cfg);
    void drawAlertContextMsg(uint16_t y, Event::ID id, const Gfx::FontAsset &font);
    void drawButtonFunction(unsigned imgX, unsigned imgY,
                            unsigned strX, unsigned strY,
                            Io::ButtonID id);

    bool alertComplete() const;
    ALWAYS_INLINE bool checkAlert() const {
        return (event != Event::None);
    }
};

#endif // _UI_BOTTOMBOX_H
