#include "tasks.h"
#include "params.h"
#include "cameracontrol.h"
#include "hostprotocol.h"
#include "inputs.h"
#include "buttonmanager.h"
#include "flightmanager.h"
#include "sologimbal.h"
#include "powermanager.h"
#include "ui.h"
#include "idletimeout.h"
#include "haptic.h"
#include "lockout.h"
#include "ili9341parallel.h"

#include "board.h"
#include "stm32/gpio.h"

uint32_t Tasks::pendingMask = 0;

void Tasks::invoke(unsigned id)
{
    /*
     * Dispatch to the appropriate handler for the given id.
     */

    switch (id) {
    case HostProtocol:
        HostProtocol::instance.task();
        break;

    case FiftyHzHeartbeat:
        Inputs::fiftyHzWork();
        if (PowerManager::state() == PowerManager::Running) {
            FlightManager::instance.sysHeartbeat();
            SoloGimbal::instance.sysHeartbeat();
            Ui::instance.alertManager.sysHeartbeat();
            CameraControl::instance.fiftyHzLoop();
            Params::sys.periodicWork();
            IdleTimeout::tick();
        }
        HostProtocol::instance.requestTransaction();

        /*
         * Normally, the display's TE isr drives our ui update.
         * If we're in a PCBA fixture at the factory, the display
         * may not be connected so we need to drive the update loop
         * by some other means.
         */
        if (ILI9341Parallel::lcd.ticksSinceLastTE() > SysTime::sTicks(1)) {
            Ui::instance.update();
        }
#if (BOARD == BOARD_BB02)
        // display updates are driven by the TE isr on BB02.5
        // but we just try for 50Hz on BB02 since we don't
        // have access to any synchronization info
        Ui::instance.update();
#endif
        break;

    case DisplayRender:
        Ui::instance.update();
        break;

    case ButtonHold:
        ButtonManager::task();
        break;

    case Haptic:
        Haptic::task();
        break;

    case Camera:
        CameraControl::instance.task();
        break;

    case Shutdown:
        PowerManager::shutdown();
        break;

    default:
        break;
    }
}

void Tasks::heartbeat()
{
    /*
     * Called periodically by the systick ISR at HEARTBEAT_HZ.
     */

    trigger(FiftyHzHeartbeat);
}

bool Tasks::work()
{
    /*
     * We sample pendingMask exactly once, and use this to quickly make
     * the determination of whether any work is to be done or not.
     *
     * In the interest of simplicity, we don't currently support
     * calling Tasks::work from within a handler. Could change if necessary.
     */

    // Quickest possible early-exit
    uint32_t tasks = pendingMask;
    if (!tasks) {
        return false;
    }

    // Clear only the bits we managed to capture above
    Atomic::And(pendingMask, ~tasks);

    do {
        unsigned idx = Intrinsic::CLZ(tasks);
        invoke(idx);
        tasks &= ~Intrinsic::LZ(idx);
    } while (tasks);

    return true;
}
