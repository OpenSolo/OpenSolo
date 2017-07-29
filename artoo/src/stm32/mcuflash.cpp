#include "mcuflash.h"

bool McuFlash::eraseOptionBytes(bool enableRDP)
{
    /*
     * Clear out all the option bytes.
     * Specify RDP while we're at it, since its default state (erased) results
     * in it being enabled.
     */

    if (waitForPreviousOperation() != StatusComplete) {
        return false;
    }

    unlockOptionBytes();

    // erase option bytes
    FLASH.CR |= CR_OPTER;   // option byte erase
    FLASH.CR |= CR_STRT;    // STRT: start the erase operation
    Status status = waitForPreviousOperation();
    FLASH.CR &= ~CR_OPTER;  // disable option byte erase
    if (status != StatusComplete) {
        return false;
    }

    // keep readout protect disabled so we can program option bytes
    FLASH.CR |= CR_OPTPG;
    FLASH_OB.RDP = enableRDP ? 0 : RDP_DISABLE_KEY;
    status = waitForPreviousOperation();
    FLASH.CR &= ~CR_OPTPG;

    return status == StatusComplete;
}

bool McuFlash::setOptionByte(OptionByte ob, uint16_t value)
{
    if (waitForPreviousOperation() != StatusComplete) {
        return false;
    }

    unlockOptionBytes();

    // program option bytes
    FLASH.CR |= CR_OPTPG;   // Option byte programming
    uint32_t optionByteAddr = reinterpret_cast<uint32_t>(&FLASH_OB);
    optionByteAddr += (ob * sizeof(uint16_t));

    beginProgramming();
    programHalfWord(value, optionByteAddr);
    Status status = waitForPreviousOperation();
    FLASH.CR &= ~CR_OPTPG;  // disable option byte programming
    endProgramming();

    return status == StatusComplete;
}

bool McuFlash::programHalfWord(uint16_t halfword, uint32_t address)
{
    /*
     * Flash hardware programs one half word at a time.
     * beginProgramming() must have been called prior.
     */

    if (waitForPreviousOperation() != StatusComplete) {
        return false;
    }

    *reinterpret_cast<volatile uint16_t*>(address) = halfword;

    return true;
}

McuFlash::Status McuFlash::waitForPreviousOperation()
{
    // wait for busy - it is reset when an error occurs,
    // or when the operation is complete
    while (FLASH.SR & SR_BSY) {
        ;
    }

    if (FLASH.SR & SR_PGERR) {
        return StatusProgrammingErr;
    }

    if (FLASH.SR & SR_WRPRTERR) {
        return StatusWriteProtectErr;
    }

    return StatusComplete;
}

bool McuFlash::erasePage(uint32_t address)
{
    if (waitForPreviousOperation() != StatusComplete) {
        return false;
    }

    FLASH.CR |= CR_PER;     // page erase
    FLASH.AR = address;
    FLASH.CR |= CR_STRT;    // STRT: start the erase operation
    Status status = waitForPreviousOperation();
    FLASH.CR &= ~CR_PER;    // disable page erase

    return status == StatusComplete;
}
