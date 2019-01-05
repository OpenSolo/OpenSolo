#include "buttonmanager.h"
#include "powermanager.h"
#include "flightmanager.h"
#include "cameracontrol.h"
#include "vehicleconnector.h"
#include "dsm.h"
#include "ui.h"
#include "tasks.h"
#include "idletimeout.h"
#include "manualoverride.h"
#include "board.h"

#include "stm32/sys.h"
#include "stm32/hwtimer.h"

uint16_t ButtonManager::buttonPressMask;

// must match order of ButtonID
Button ButtonManager::buttons[] = {
    Button(BTN_PWR_GPIO,        LED_BLUE_S1_GPIO,   LED_WHITE_S1_GPIO, Io::ButtonPower, Button::ActiveLow),
    Button(BTN_FLY_GPIO,        LED_BLUE_S2_GPIO,   LED_WHITE_S2_GPIO, Io::ButtonFly),
    Button(BTN_RTL_GPIO,        LED_BLUE_S3_GPIO,   LED_WHITE_S3_GPIO, Io::ButtonRTL),
    Button(BTN_LOITER_GPIO,     LED_BLUE_S4_GPIO,   LED_WHITE_S4_GPIO, Io::ButtonLoiter),
    Button(BTN_A_GPIO,          LED_BLUE_S5_GPIO,   LED_WHITE_S5_GPIO, Io::ButtonA),
    Button(BTN_B_GPIO,          LED_BLUE_S6_GPIO,   LED_WHITE_S6_GPIO, Io::ButtonB),
    Button(BTN_PRESET1_GPIO,    LED_GPIO_NONE,      LED_GPIO_NONE,     Io::ButtonPreset1),
    Button(BTN_PRESET2_GPIO,    LED_GPIO_NONE,      LED_GPIO_NONE,     Io::ButtonPreset2),
    Button(BTN_CAM_CLICK_GPIO,  LED_GPIO_NONE,      LED_GPIO_NONE,     Io::ButtonCameraClick)
};

unsigned ButtonManager::eventIdx;
RingBuffer<8> ButtonManager::pendingEventIdxs;
ButtonManager::ButtonEvent ButtonManager::events[7];

void ButtonManager::init()
{
    ////////////////////////////////////
    // button gpio init

    buttons[Io::ButtonPower].init(true);
    buttons[Io::ButtonFly].init(true);
    buttons[Io::ButtonRTL].init(true);
    buttons[Io::ButtonLoiter].init(true);
    buttons[Io::ButtonA].init(true);
    buttons[Io::ButtonB].init(true);
    buttons[Io::ButtonPreset1].init(true);
    buttons[Io::ButtonPreset2].init(true);
    buttons[Io::ButtonCameraClick].init(true);


    ////////////////////////////////////
    // button backlight init

    HwTimer ledTimer(&LED_PWM_TIM);
    GPIOPin dimmer = LED_PWM_GPIO;

    const unsigned hz = 120;

    AFIO.MAPR |= (0x3 << 10);     // 'full remap' TIM3 to PC6-9

    ledTimer.init(Sys::CPU_HZ / 1000 / hz, 1000);
    ledTimer.configureChannelAsOutput(LED_PWM_CH,
                                       HwTimer::ActiveLow,
                                       HwTimer::Pwm1,
                                       HwTimer::SingleOutput);
    setBacklight(0);    // we'll enable this once the display backlight comes up
    ledTimer.enableChannel(LED_PWM_CH);

    // must configure output as open collector,
    // since the pullup will pull our hi-z state up to 5V
    // instead of 3.3V if we were to drive it directly.
    dimmer.setControl(GPIOPin::OUT_ALT_OPEN_50MHZ);

    ////////////////////////////////////
    // button functions

    for (unsigned i = 0; i < arraysize(Params::sys.storedValues.buttonConfigs); ++i){
        Io::ButtonID id = static_cast<Io::ButtonID>(Io::ButtonLoiter + i);
        ButtonFunction::Config & cfg = ButtonFunction::get(id);

        if (!Params::isInitialized(&cfg, sizeof cfg)) {
            cfg.buttonID = id;
            cfg.buttonEvt = Button::ClickRelease;
            cfg.shotID = ButtonFunction::ShotNone;
            strncpy(cfg.descriptor, "None", strlen("None") + 1);
        }
    }
}

bool ButtonManager::setButtonFunction(Io::ButtonID id, const ButtonFunction::Config *c)
{
    if (ButtonFunction::validId(id)) {
        Button & btn = button(id);
        ButtonFunction::Config & cfg = ButtonFunction::get(id);
        memcpy(&cfg, c, sizeof cfg);

        if (cfg.descriptor[0] == '\0') {
            // XXX: no descriptor indicates this button isn't currently mapped to a function
        }

        btn.setGreenLed(cfg.hilighted());

        return true;
    }

    return false;
}

void ButtonManager::setBacklight(unsigned percent)
{
    /*
     * set brightness level, 0-100.
     */

    ASSERT(percent <= 100);

    HwTimer ledTimer(&LED_PWM_TIM);
    uint16_t duty = percent / 100.0f * ledTimer.period();
    ledTimer.setDuty(LED_PWM_CH, duty);
}

void ButtonManager::isr(Io::ButtonID id)
{
    /*
     * An edge has been detected on a button input, in ISR context.
     *
     * 1. allow the button to do its housekeeping in isr()
     * 2. update our mask of pressed buttons
     * 3. dispatch events for individual buttons as appropriate.
     */

    Button &b = buttons[id];
    if (b.isPressed()) {
        buttonPressMask |= (1 << id);
    } else {
        buttonPressMask &= ~(1 << id);
    }

    if (!b.isr()) {
        return;
    }

    if (buttonPressMask) {
        Tasks::trigger(Tasks::ButtonHold);
    }
}

void ButtonManager::task()
{
    /*
     * Called periodically once a button is being pressed
     * to determine if it has been held long enough to be
     * considered a hold.
     *
     * Called from heartbeat ISR context.
     */

    // latch a single copy as buttonPressMask may continue to
    // be modified in ISRs
    uint16_t pressMask = buttonPressMask;

    for (unsigned i = 0; pressMask && i < arraysize(buttons); ++i, pressMask >>= 1) {
        if (pressMask & 0x01) {
            buttons[i].pollForHold();
        }
    }

    // buttons still pressed? re-schedule ourselves
    if (buttonPressMask) {
        Tasks::trigger(Tasks::ButtonHold);
    }
}

void ButtonManager::dispatchEvt(Button *b, Button::Event evt)
{
    /*
     * Send button events to interested parties.
     *
     * Some handlers indicate they've handled the event,
     * in which case we should stop propagating to subsequent handlers.
     */

    if (evt == Button::Press) {
        IdleTimeout::reset();
    }

    ManualOverride::onButtonEvent(b, evt);
    IdleTimeout::onButtonEvent(b, evt);

    if (Ui::instance.updater.onButtonEvent(b, evt)) {
        return;
    }

    if (Ui::instance.alertManager.onButtonEvent(b, evt)) {
        return;
    }

    switch (b->id()) {
    case Io::ButtonPower:
        FlightManager::instance.onPowerButtonEvt(b, evt);
        PowerManager::onButtonEvt(b, evt);
        break;

    case Io::ButtonFly:
        if (Ui::instance.state() == Ui::Arming) {
            Ui::instance.arming.onFlyButtonEvt(b, evt);
        }
        FlightManager::instance.onFlyButtonEvt(b, evt);
        break;

    case Io::ButtonRTL:
        FlightManager::instance.onRtlButtonEvt(b, evt);
        break;

    case Io::ButtonLoiter:
        ButtonFunction::onButtonExtEvent(b, evt);
        FlightManager::instance.onPauseButtonEvt(b, evt);
        Dsm::instance.onLoiterButtonEvt(b, evt);
        ButtonFunction::onButtonEvent(b, evt);
        break;

    case Io::ButtonA:
        ButtonFunction::onButtonExtEvent(b, evt);
        FlightManager::instance.onAButtonEvt(b, evt);
        VehicleConnector::instance.onButtonEvent(b, evt);
        ButtonFunction::onButtonEvent(b, evt);
        break;

    case Io::ButtonB:
        ButtonFunction::onButtonExtEvent(b, evt);
        FlightManager::instance.onBButtonEvt(b, evt);
        VehicleConnector::instance.onButtonEvent(b, evt);
        ButtonFunction::onButtonEvent(b, evt);
        break;

    case Io::ButtonPreset1:
        ButtonFunction::onButtonExtEvent(b, evt);
        CameraControl::instance.onButtonEvt(b, evt);
        break;

    case Io::ButtonPreset2:
        ButtonFunction::onButtonExtEvent(b, evt);
        CameraControl::instance.onButtonEvt(b, evt);
        break;

    case Io::ButtonCameraClick:
        ButtonFunction::onButtonExtEvent(b, evt);
        CameraControl::instance.onButtonEvt(b, evt);
        break;
    }

    if (ManualOverride::isEnabled()) {
        // suppress button events such that when we're overriding
        // into manual mode, it's not possible for sololink
        // to treat inadvertent button presses as mode change commands
        return;
    }

    if ( evt == Button::Release || (evt == Button::DoubleClick)  ||
       (evt == Button::Hold) || (evt == Button::ShortHold) ) {
        return; // Not sending these events to Solo since they aren't used.
    }

    // store event for forwarding
    if (pendingEventIdxs.full()) {
        DBG(("button event dropped\n"));
        return;
    }

    ButtonEvent &be = events[eventIdx];
    be.id = b->id();
    be.event = evt;
    be.allButtonsMask = buttonPressMask;

    pendingEventIdxs.enqueue(eventIdx);
    eventIdx = (eventIdx + 1) % arraysize(events);
    HostProtocol::instance.requestTransaction();
}

void ButtonManager::onFlightModeChanged(FlightManager::FlightMode fm)
{
    // XXX: will need to be smarter once we can edit the
    //      function of the A and B buttons...
    button(Io::ButtonLoiter).setLed(fm == FlightManager::LOITER);
    button(Io::ButtonRTL).setLed(fm == FlightManager::RTL);
}

bool ButtonManager::producePacket(HostProtocol::Packet &p)
{
    if (pendingEventIdxs.empty()) {
        return false;
    }

    ButtonEvent &be = events[pendingEventIdxs.dequeue()];

    p.delimitSlip();
    p.appendSlip(HostProtocol::ButtonEvent);
    p.append(be.bytes, sizeof be);
    p.delimitSlip();

    return true;
}

void ButtonManager::shutdown()
{
    /*
     * we're shutting down - disable all visual elements.
     */

    for (unsigned i = 0; i < arraysize(buttons); ++i) {
        buttons[i].greenLedOff();
    }

    // disable all buttons other than power
    ButtonManager::button(Io::ButtonA).disableIRQ();
    ButtonManager::button(Io::ButtonB).disableIRQ();
    ButtonManager::button(Io::ButtonLoiter).disableIRQ();
    ButtonManager::button(Io::ButtonFly).disableIRQ();
    ButtonManager::button(Io::ButtonRTL).disableIRQ();
    ButtonManager::button(Io::ButtonPreset1).disableIRQ();
    ButtonManager::button(Io::ButtonPreset1).disableIRQ();
    ButtonManager::button(Io::ButtonFly).disableIRQ();
    ButtonManager::button(Io::ButtonCameraClick).disableIRQ();

    setBacklight(0);
}
