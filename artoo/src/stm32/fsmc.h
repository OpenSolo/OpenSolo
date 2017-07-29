#ifndef FSMC_H
#define FSMC_H

#include "hw.h"
#include "gpio.h"

class Fsmc
{
public:
    static const unsigned Bank1Base = 0x60000000U;  // NOR / PSRAM
    static const unsigned Bank2Base = 0x70000000U;  // NAND flash
    static const unsigned Bank3Base = 0x80000000U;  // NAND flash
    static const unsigned Bank4Base = 0x90000000U;  // PC card

    enum BCRFlags {
        MBKEN           = (1 << 0),
        MUXEN           = (1 << 1),
        MTYP_SRAM_ROM   = (0 << 2),
        MTYP_PSRAM      = (1 << 2),
        MTYP_NOR        = (2 << 2),
        MWID_8BIT       = (0 << 4),
        MWID_16BIT      = (1 << 4),
        FACCEN          = (1 << 6),
        BURSTEN         = (1 << 8),
        WAITPOL         = (1 << 9),
        WRAPMOD         = (1 << 10),
        WAITCFG         = (1 << 11),
        WREN            = (1 << 12),
        WAITEN          = (1 << 13),
        EXTMOD          = (1 << 14),
        ASYNCWAIT       = (1 << 15),
        CBURSTRW        = (1 << 19),
    };

    enum BTRFlags {
        AccessModeA = 0x0,
        AccessModeB = 0x1,
        AccessModeC = 0x2,
        AccessModeD = 0x3,
    };

    enum Bank {
        Bank1 = 0,
        Bank2 = 1,
        Bank3 = 2,
        Bank4 = 3,
    };

    struct NorSramTimingInit {
        NorSramTimingInit(uint8_t addSet, uint8_t addHold, uint8_t dataSet, uint8_t busTurn, uint8_t clkDiv, uint8_t dataLat, uint8_t accMod) :
            word(addSet |
                 (addHold << 4) |
                 (dataSet << 8) |
                 (busTurn << 16) |
                 (clkDiv << 20) |
                 (dataLat << 24) |
                 (accMod << 28))
        {}

        uint32_t word;
    };

    struct Config {
        uint32_t bcrFlags;
        NorSramTimingInit timing;
        Bank bank;
    };

    Fsmc(); // do not implement

    static void initNorSram(GPIOPin dataPins[], unsigned numDataPins, GPIOPin ctrlPins[], unsigned numCtrlPins, const Config & config);

private:

};

#endif // FSMC_H
