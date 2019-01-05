#ifndef RCC_H
#define RCC_H

#include "hw.h"
#include "common.h"

class Rcc
{
public:
    enum CrBits {
        CR_PLL_RDY          = (1 << 25),
        CR_PLL_ON           = (1 << 24),
        CR_CSS_ON           = (1 << 19),
        CR_HSE_BYP          = (1 << 18),
        CR_HSE_RDY          = (1 << 17),
        CR_HSE_ON           = (1 << 16),
        CR_HSI_CAL_MASK     = 0xff,
        CR_HSI_CAL_POS      = 8,
        CR_HSI_TRIM_MASK    = 0x1f,
        CR_HSI_TRIM_POS     = 3,
        CR_HSI_RDY          = (1 << 1),
        CR_HSI_ON           = (1 << 0),
    };

    enum CsrBits {
        CSR_LPWR_RSTF   = (1 << 31),    // low power reset
        CSR_WWDG_RSTF   = (1 << 30),    // window watchdog reset
        CSR_IWDG_RSTF   = (1 << 29),    // indpendent watchdog reset
        CSR_SFT_RSTF    = (1 << 28),    // software reset
        CSR_POR_RSTF    = (1 << 27),    // POR/PDR reset
        CSR_PIN_RSTF    = (1 << 26),    // NRST pin reset
        CSR_RMVF        = (1 << 24),    // clear reset flags
        CSR_LSI_RDY     = (1 << 1),     // low speed internal osc ready
        CSR_LSION       = (1 << 0),     // low speed internal osc enable
    };

    enum BdcrBits {
        BDCR_BDRST          = (1 << 16),    // backup dowmain software reset
        BDCR_RTCEN          = (1 << 15),    // rtc enable
        BDCR_RTCSEL_MASK    = 0x3,
        BDCR_RTCSEL_POS     = 8,
        BDCR_LSEBYP         = (1 << 2),     // external low speed osc bypass
        BDCR_LSERDY         = (1 << 1),     // external low speed osc ready
        BDCR_LSEON          = (1 << 0),     // external low speed osc enable
    };

    static void latchAndClearResetFlags();

    static uint32_t csr() {
        return latchedCSR;
    }

    static bool pinReset() {
        // test for presence of pin reset, and absence of power & software reset
        // assumes latchAndClearResetFlags() has already been called
        return (latchedCSR & (CSR_PIN_RSTF | CSR_SFT_RSTF | CSR_POR_RSTF)) == CSR_PIN_RSTF;
    }

    static bool swReset() {
        return latchedCSR & (CSR_SFT_RSTF);
    }

private:
    static uint32_t latchedCSR;
};

#endif // RCC_H
