#include "fsmc.h"
#include "gpio.h"

void Fsmc::initNorSram(GPIOPin dataPins[], unsigned numDataPins, GPIOPin ctrlPins[], unsigned numCtrlPins, const Config &config)
{
    RCC.AHBENR |= (1 << 8);

    // data lines are configured alternate function, push pull
    for (unsigned i = 0; i < numDataPins; ++i) {
        dataPins[i].setControl(GPIOPin::OUT_ALT_50MHZ);
    }

    // ctrl lines are configured alternate function, push pull
    for (unsigned i = 0; i < numCtrlPins; ++i) {
        ctrlPins[i].setControl(GPIOPin::OUT_ALT_50MHZ);
    }

    volatile FSMCChipSel_t *ctrl = &FSMC.chipSel[config.bank];
    ctrl->BCR = config.bcrFlags;
    ctrl->BTR = config.timing.word;

    if (config.bcrFlags & EXTMOD) {
        // XXX: support extended mode some day if we need to
    } else {
        // leave timing config at its reset value, since we are not using extended mode.
        FSMC.writeTiming[config.bank].BWTR = 0x0FFFFFFF;
    }

    // turn it on
    ctrl->BCR |= MBKEN;
}
