#ifndef BUTTON_EVENT_MESSAGE_H
#define BUTTON_EVENT_MESSAGE_H

#include <stdint.h>
#include <iostream>

struct __attribute((__packed__)) ButtonEventMessage {
    // These four fields are expected to be the only data and in this order,
    // so the address of the structure can be interpreted as a 12-byte char
    // array with the fields in native byte order (little-endian on ARM).
    uint64_t timestamp;
    uint8_t id;
    uint8_t event;
    uint16_t allButtons;

    // match artoo/src/io.h
    enum ButtonId {
        ButtonPower,
        ButtonFly,
        ButtonRTL,
        ButtonLoiter,
        ButtonA,
        ButtonB,
        ButtonPreset1,
        ButtonPreset2,
        ButtonCameraClick,
        ButtonMax
    };

    inline const char *idName(void) const
    {
        static const char *names[] = {
            "Power", "Fly", "RTL", "Loiter", "A", "B", "Preset1", "Preset2", "CameraClick",
        };
        if (id >= 0 && id < ButtonMax)
            return names[id];
        else
            return "INVALID";
    }

    // match artoo/src/button.h
    enum ButtonEvent { Press, Release, ClickRelease, ShortHold, Hold, LongHold, DoubleClick, HoldRelease, LongHoldRelease, EventMax };

    inline const char *eventName(void) const
    {
        static const char *names[] = {
            "Press", "Release", "ClickRelease", "ShortHold", "Hold", "LongHold", "DoubleClick", "HoldRelease", "LongHoldRelease",
        };
        if (event >= 0 && event < EventMax)
            return names[event];
        else
            return "INVALID";
    }

    ButtonEventMessage(void)
    {
        timestamp = 0;
        id = 0;
        event = 0;
        allButtons = 0;
    }

    ButtonEventMessage(uint64_t ts, const char *rawMsg)
    {
        timestamp = ts;
        // rawMsg is ButtonEvent in artoo/src/buttonmanager.h
        id = rawMsg[0];
        event = rawMsg[1];
        allButtons = rawMsg[2] | (rawMsg[3] << 8); // little endian
    }
};

std::ostream &operator<<(std::ostream &os, const struct ButtonEventMessage &msg);

#endif // BUTTON_EVENT_MESSAGE_H
