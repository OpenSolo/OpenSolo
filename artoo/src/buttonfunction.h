#ifndef BUTTON_FUNCTION_H
#define BUTTON_FUNCTION_H

#include "io.h"
#include "button.h"

#include "stm32/common.h"

class ButtonFunction {
public:
    // in sync with github.com/OpenSolo/sololink/blob/master/app/shots/shots.py
    enum ShotID {
        ShotNone            = -1,
        ShotSelfie          = 0,
        ShotSpotlock        = 1,
        ShotCableCam        = 2,
        ShotInfiniCable     = 3,
        ShotRecord          = 4,
    };

    enum FunctionState {
        FuncEnabled     = (1 << 0),
        FuncHilighted   = (1 << 1),
    };

    struct Config {
        static const unsigned MAX_DESCRIPTOR = 19;
        static const unsigned MIN_LEN = 5;  // 4 bytes header and at least one byte of descriptor

        uint8_t buttonID;
        uint8_t buttonEvt;
        int8_t shotID;
        uint8_t state;
        char descriptor[MAX_DESCRIPTOR + 1];

        bool ALWAYS_INLINE enabled() const {
            return state & FuncEnabled;
        }

        bool ALWAYS_INLINE hilighted() const {
            return state & FuncHilighted;
        }
    };

    static ALWAYS_INLINE bool validId(Io::ButtonID id) {
        return id >= Io::ButtonLoiter && id <= Io::ButtonB;
    }

    static ButtonFunction::Config & get(Io::ButtonID id);
    static void onButtonEvent(Button *b, Button::Event e);
    static void onButtonExtEvent(Button *b, Button::Event e);
};

#endif // BUTTON_FUNCTION_H
