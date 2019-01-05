#include "params.h"
#include "flightmanager.h"

#include <string.h>
#include "stm32/mcuflash.h"

Params Params::sys;

void Params::load()
{
    /*
     * Read the params object out of flash.
     * Uninitialized bytes will be set to 0xff.
     */

    memcpy(&storedValues, reinterpret_cast<const void*>(ParamsPageAddr), sizeof(storedValues));
}

bool Params::save()
{
    /*
     * Write our stored values to storage.
     * In order to write even one new value, we must erase the entire page.
     *
     * Should only be called on a periodic basis by fiftyHzWork()
     * or during shutdown.
     */

    if (!dirty) {
        return true;
    }

    McuFlash::unlock();

    if (!McuFlash::erasePage(ParamsPageAddr)) {
        return false;
    }

    const uint16_t *ptr = reinterpret_cast<const uint16_t *>(&storedValues);
    unsigned addr = ParamsPageAddr;
    const unsigned end = addr + sizeof(storedValues);

    McuFlash::beginProgramming();
    while (addr < end) {
        if (!McuFlash::programHalfWord(*ptr, addr)) {
            McuFlash::endProgramming();
            return false;
        }
        addr += sizeof(uint16_t);
        ptr++;
    }
    McuFlash::endProgramming();

    McuFlash::lock();

    return true;
}

void Params::periodicWork()
{
    /*
     * Called periodically in task context.
     * Sync our params if needed every SYNC_MILLIS.
     */

    if (FlightManager::instance.armed()) {
        // We never want to sync when the vehicle is armed,
        // since the process of writing to internal flash can stall
        // the CPU long enough to drop bytes over the UART.
        return;
    }

    const SysTime::Ticks now = SysTime::now();
    if (now > syncDeadline) {
        if (!save()) {
            DBG(("error syncing params\n"));
        }
        syncDeadline = now + SysTime::msTicks(SYNC_MILLIS);
        dirty = false;
    }
}

bool Params::isInitialized(const void *p, unsigned len)
{
    /*
     * For each param element, we consider it to be initialized
     * if any of its bytes have been programmed to a value other
     * than the uninitialized value of 0xff;
     */

    // must be half-word aligned
    ASSERT((len & 0x1) == 0);
    if (len & 0x1) {
        return false;
    }

    const uint16_t *bp = static_cast<const uint16_t *>(p);
    for ( ; len > 0; bp++, len -= sizeof(uint16_t)) {
        if (*bp != 0xffff) {
            return true;
        }
    }

    // all bytes were uninitialized
    return false;
}
