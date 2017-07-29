#ifndef UIALERT_H
#define UIALERT_H

#include "ui_events.h"
#include "gfx.h"
#include "tasks.h"
#include "stm32/systime.h"
#include "button.h"

class UiAlertManager
{
public:
    UiAlertManager();

    static const unsigned NO_TIMEOUT = 0;

    enum Behavior {
        UndefinedBehavior,           // mainly used for error
        FullScreenModal,
        HintBoxBanner,
        FullScreenThenHintBox,
    };

    enum Severity {
        White,
        Green,
        Orange,
        Red,
    };
    
    enum HapticSeverity {
        NoHaptic,
        LowHaptic,
        MedHaptic,
        HighHaptic,
    };

    enum DismissBtn {
        DismissNone,
        DismissA,
        DismissFly,
    };

    bool init(Event::ID id);
    void sysHeartbeat();
    bool canReplaceCurrentAlert(Event::ID id) const;
    bool complete(SysTime::Ticks start) const;
    void dismiss();
    bool onButtonEvent(Button *b, Button::Event e);

    // declarative config for alerts
    struct Alert {
        Severity severity;
        HapticSeverity hapticSeverity;
        Behavior behavior;
        unsigned durationMillis;
        DismissBtn dismissBtn;
        const char *warningFirst;
        const char *warningRest;
        const char *contextMsg;
        const char *confirmation;

        //const Gfx::FontAsset & warningFont() const;
        uint16_t severityColor() const;

        bool needsBannerDisplay() const {
            return behavior == FullScreenThenHintBox || behavior == HintBoxBanner;
        }

        bool needsFullscreenDisplay() const {
            return behavior == FullScreenModal || behavior == FullScreenThenHintBox;
        }

        void startHaptic() const;

        bool buttonWillDismiss(const Button *b, const Button::Event e) const;
        bool shouldConsumeEvent(const Button *b, const Button::Event e) const;
    };

    static const Alert alerts[];

    Event::ID currentEvent() const {
        return event;
    }

    bool hasAlert() const {
        return alertIsDefinedFor(event);
    }
    const Alert & currentAlert() const;

    unsigned currentAlertTimeout() const {
        return currentAlert().durationMillis;
    }

    bool currentAlertNeedsFullscreen();
    bool currentAlertNeedsBanner();
    bool currentAlertVehiclePreArm();
    bool currentAlertRecovery();

    void dismissInvalidStickAlerts();

    const Alert & getAlert(Event::ID id) const;

private:
    static const unsigned PERIODIC_NOTIFY_INTERVAL = Tasks::HEARTBEAT_HZ * 1.5;

    bool periodicHapticEnabled() const;
    bool alertIsDefinedFor(Event::ID id) const;

    Event::ID event;
    unsigned periodicNotificationCounter;
};

#endif // UIALERT_H
