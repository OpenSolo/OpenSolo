#ifndef MCU_FLASH_H
#define MCU_FLASH_H

/*
 * Routines for managing the internal MCU flash on the STM32.
 * Typical endurance is minimum 10 kcycles.
 */

#include "hw.h"

class McuFlash
{
public:

    // high-density line specific values
    static const unsigned PAGE_SIZE = 2048;
    static const unsigned NUM_PAGES = 128;

    static const uint32_t START_ADDR = 0x8000000;
    static const uint32_t END_ADDR = START_ADDR + (NUM_PAGES * PAGE_SIZE);

    enum CrBits {
        CR_PG       = (1 << 0),
        CR_PER      = (1 << 1),
        CR_MER      = (1 << 2),
        CR_OPTPG    = (1 << 4),
        CR_OPTER    = (1 << 5),
        CR_STRT     = (1 << 6),
        CR_LOCK     = (1 << 7),
        CR_OPTWRE   = (1 << 9),
        CR_ERRIE    = (1 << 10),
        CR_EOPIE    = (1 << 12),
    };

    enum SrBits {
        SR_BSY      = (1 << 0),
        SR_PGERR    = (1 << 2),
        SR_WRPRTERR = (1 << 4),
        SR_EOP      = (1 << 5),
    };

    static inline bool isLocked() {
        return FLASH.CR & CR_LOCK;
    }

    static inline void unlock() {
        FLASH.KEYR = KEY1;
        FLASH.KEYR = KEY2;
    }

    static inline void lock() {
        FLASH.CR |= CR_LOCK;
    }

    static inline void unlockOptionBytes() {
        FLASH.OPTKEYR = KEY1;
        FLASH.OPTKEYR = KEY2;
    }

    /*
     * Programming (synchronous for now):
     *  - beginProgramming()
     *  - one or more calls to programHalfWord()
     *  - endProgramming()
     */
    static inline void beginProgramming() {
        FLASH.CR |= CR_PG;
    }

    static bool programHalfWord(uint16_t halfword, uint32_t address);

    static inline void endProgramming() {
        waitForPreviousOperation();
        FLASH.CR &= ~CR_PG;
    }

    /*
     * Erasing must occur a page at a time.
     */
    static bool erasePage(uint32_t address);

    static bool readOutProtectionIsEnabled() {
        return (FLASH.OBR & (1 << 1)) != 0;
    }

    enum OptionByte {
        OptionRDP,
        OptionUSER,
        OptionDATA0,
        OptionDATA1,
        OptionWRP0,
        OptionWRP1,
        OptionWRP2,
        OptionWRP3,
    };

    static bool eraseOptionBytes(bool enableRDP = false);
    static bool setOptionByte(OptionByte ob, uint16_t value);

private:
    static const uint16_t RDP_DISABLE_KEY = 0x00A5;
    static const uint32_t KEY1 = 0x45670123;
    static const uint32_t KEY2 = 0xCDEF89AB;

    enum Status {
        StatusComplete,
        StatusProgrammingErr,
        StatusWriteProtectErr
    };

    static Status waitForPreviousOperation();
};

#endif // MCU_FLASH_H
