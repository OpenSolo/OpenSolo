#ifndef HAPTIC_H
#define HAPTIC_H

/*
 * Provides control of our simple on/off haptic vibration motor.
 */

#include "board.h"

#include "stm32/gpio.h"
#include "stm32/systime.h"

class Haptic
{
public:
    Haptic(); // do not implement

    enum Pattern {
        SingleShort,
        SingleMedium,
        SingleLong,
        UhUh,
        LightDouble,
        LightTriple,
        HeavyTriple,
    };

    static void init();
    static void startPattern(Pattern p);
    static bool playing();
    static void stop();

    static void task();

private:
    static const uint16_t OffMask = 0x8000;

    struct PatternData {
        const uint16_t *entries;
        unsigned len;

        void set(const uint16_t *e, unsigned l) {
            entries = e;
            len = l;
        }

        void cancel() {
            len = 0;
        }

        ALWAYS_INLINE uint16_t next() {
            uint16_t e = *entries++;
            len--;
            return e;
        }

        ALWAYS_INLINE bool done() const {
            return len == 0;
        }
    };

    static void nextEntry();

    static void ALWAYS_INLINE motorOn() {
        VIB_GPIO.setHigh();
    }
    static void ALWAYS_INLINE motorOff() {
        VIB_GPIO.setLow();
    }
    static bool ALWAYS_INLINE motorIsOn() {
        return VIB_GPIO.isOutputHigh();
    }

    static SysTime::Ticks stopDeadline;
    static PatternData pat;

    static const uint16_t UhUhPattern[];
    static const uint16_t SingleShortPattern[];
    static const uint16_t SingleMediumPattern[];
    static const uint16_t SingleLongPattern[];
    static const uint16_t LightDoublePattern[];
    static const uint16_t LightTriplePattern[];
    static const uint16_t HeavyTriplePattern[];
};

#endif // HAPTIC_H
