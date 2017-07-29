#ifndef PWR_H
#define PWR_H

#include "hw.h"
#include "common.h"

class Pwr
{
public:
    Pwr(); // do not implement

    enum StopConfig {
        StopOnWFI       = (1 << 0), // enter stop via WFI if set, otherwise via WFE
        StopDisableReg  = (1 << 1), // disable regulator in stop mode if set, otherwise leave enabled
    };

    // values for the PLS field of PWR.CR
    enum PVDLevel {
        PVD_2_2V = 0x0,
        PVD_2_3V = 0x1,
        PVD_2_4V = 0x2,
        PVD_2_5V = 0x3,
        PVD_2_6V = 0x4,
        PVD_2_7V = 0x5,
        PVD_2_8V = 0x6,
        PVD_2_9V = 0x7,
    };

    enum CRBits {
        CR_LPDS = (1 << 0), // Low-power deepsleep
        CR_PDDS = (1 << 1), // Power down deepsleep
        CR_CWUF = (1 << 2), // Clear wakeup flag
        CR_CSBF = (1 << 3), // Clear standby flag
        CR_PVDE = (1 << 4), // Power voltage detector enable
        CR_DBP  = (1 << 8)
    };

    enum CSRBits {
        CSR_WUF  = (1 << 0),    // Wakeup flag
        CSR_SBF  = (1 << 1),    // Standby flag
        CSR_PVDO = (1 << 2),    // PVD output
        CSR_EWUP = (1 << 8),    // Enable WKUP pin
    };

    static ALWAYS_INLINE void init() {
        RCC.APB1ENR |= (1 << 28); // PWREN
        disableWakeupPin();
    }

    static void enableVoltageDetector(uint8_t pls);
    static bool voltageDetectorIsBelowThresh();

    static void stop(StopConfig cfg);
    static void standby();

    static bool wokeFromStandby() {
        return PWR.CSR & CSR_SBF;
    }

private:
    static const uint32_t SLEEPDEEP = 0x00000004;

    static ALWAYS_INLINE void enableWakeupPin() {
        PWR.CSR |= CSR_EWUP;
    }

    static ALWAYS_INLINE void disableWakeupPin() {
        PWR.CSR &= ~CSR_EWUP;
    }
};

#endif // PWR_H
