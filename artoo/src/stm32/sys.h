#ifndef SYS_H
#define SYS_H

#include <stdint.h>
#include "common.h"

class Sys
{
public:
    Sys();  // do not implement

    static const unsigned CPU_HZ = 72000000;

    // STM32's internal unique ID.
    static const uint8_t* const UniqueId;
    static const unsigned UniqueIdLen = 12;

    static ALWAYS_INLINE void waitForInterrupt() {
        __asm__ __volatile__ ("wfi");
    }

    static ALWAYS_INLINE void waitForEvent() {
        __asm__ __volatile__ ("wfe");
    }
};

#endif // SYS_H
