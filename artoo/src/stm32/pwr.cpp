#include "pwr.h"
#include "sys.h"
#include "gpio.h"

void Pwr::enableVoltageDetector(uint8_t pls)
{
    /*
     * Set the voltage detector threshold to pls
     * (must be a value in PVDLevel),
     * and enable the voltage detector.
     */

    const unsigned PlsBitOffset = 5;
    const uint32_t PlsMask = 0x7 << PlsBitOffset;

    uint32_t cr = PWR.CR & ~PlsMask;
    cr |= (pls << PlsBitOffset) & PlsMask;
    PWR.CR = cr | CR_PVDE;
}

bool Pwr::voltageDetectorIsBelowThresh()
{
    return PWR.CSR & CSR_PVDO;
}

void Pwr::stop(StopConfig cfg)
{
    /*
     * Enter STM32 'stop' low power mode.
     *
     * We have the option to put the regulator in low power mode,
     * and to wake up on either interrupt or event.
     *
     * A pin should be configured as a wake up source correspondingly,
     * to generate either an interrupt or event.
     */

    // disable SRAM and FLITF clocks
    RCC.AHBENR &= ~((1 << 2) | (1 << 4));

    // clear standby and wakeup flags,
    // do not select standy mode, and apply the regulator
    // setting from cfg
    PWR.CR |= (CR_CSBF | CR_CWUF);
    PWR.CR &= ~(CR_PDDS | CR_LPDS);
    if (cfg & StopDisableReg) {
        PWR.CR |= CR_LPDS;
    }

    // Set SLEEPDEEP bit of Cortex System Control Register
    NVIC.sysControl |= SLEEPDEEP;

    if (cfg & StopOnWFI) {
        Sys::waitForInterrupt();
    } else {
        Sys::waitForEvent();
    }

    // continues here once wake up source has triggered
}

void Pwr::standby()
{
    /*
     * Enter the STM32 'standby' low power mode,
     * the lowest power mode available.
     * We're essentially off, from a UI perspective.
     */

    enableWakeupPin();

    // set standby mode, clear standy and wakeup flags
    PWR.CR |= (CR_PDDS | CR_CSBF | CR_CWUF);

    // Set SLEEPDEEP bit of Cortex System Control Register
    NVIC.sysControl |= SLEEPDEEP;

    asm volatile ("dsb");   // ensure memory has been written before we go to sleep

    Sys::waitForInterrupt();

    // After waking up from Standby mode,
    // program execution restarts in the same way as after a Reset
}
