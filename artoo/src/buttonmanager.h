#ifndef BUTTON_MANAGER_H
#define BUTTON_MANAGER_H

#include "button.h"
#include "flightmanager.h"
#include "hostprotocol.h"
#include "ringbuffer.h"
#include "buttonfunction.h"

class ButtonManager
{
public:
    ButtonManager(); // do not implement

    static void init();
    static bool setButtonFunction(Io::ButtonID id, const ButtonFunction::Config * c);
    static void setBacklight(unsigned percent);

    static void onFlightModeChanged(FlightManager::FlightMode fm);

    static bool producePacket(HostProtocol::Packet &p);

    // only intended to be called from exti.cpp
    static void isr(Io::ButtonID id);

    // only intended to be called from tasks.cpp
    static void task();

    static Button & button(Io::ButtonID id) {
        return buttons[id];
    }

    static ALWAYS_INLINE uint16_t pressMask() {
        return buttonPressMask;
    }

    static void dispatchEvt(Button *b, Button::Event evt);

    static void shutdown();

private:
    union ButtonEvent {
        uint8_t bytes[0];
        struct {
            uint8_t id;
            uint8_t event;
            uint16_t allButtonsMask;
        };
    };

    static Button buttons[];
    static uint16_t buttonPressMask;    // buttons currently being pressed

    static unsigned eventIdx;
    static RingBuffer<8> pendingEventIdxs;
    static ButtonEvent events[7];
};

#endif // BUTTON_MANAGER_H
