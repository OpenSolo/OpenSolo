#include "bkp.h"
#include "pwr.h"
#include "rcc.h"

void Bkp::init()
{
    // enable PWR and BKP domains
    RCC.APB1ENR |= ((1 << 27) | (1 << 28));

    // enable access to backup registers
    PWR.CR |= Pwr::CR_DBP;
}

void Bkp::reset()
{
    /*
     * Clear all backup data registers,
     * reset value is 0x0000.
     */

    RCC.BDCR |= Rcc::BDCR_BDRST;
    RCC.BDCR &= ~Rcc::BDCR_BDRST;
}
