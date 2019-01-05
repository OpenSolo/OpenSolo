#include "rcc.h"

uint32_t Rcc::latchedCSR;

void Rcc::latchAndClearResetFlags()
{
    latchedCSR = RCC.CSR;
    RCC.CSR |= CSR_RMVF;
}
