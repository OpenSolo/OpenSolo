#include "powermanager.h"
#include "buttonmanager.h"
#include "ui.h"
#include "battery.h"
#include "haptic.h"
#include "ili9341parallel.h"
#include "params.h"
#include "board.h"
#include "resources-gen.h"

#include "stm32/sys.h"
#include "stm32/systime.h"
#include "stm32/gpio.h"
#include "stm32/rcc.h"
#include "stm32/pwr.h"

bool PowerManager::notifyShutdown;
PowerManager::SysState PowerManager::sysState;

void PowerManager::init()
{
    /*
     * configure our output pins,
     * enable the keep-on asap so we stay alive,
     * and we'll turn on the iMX6 board once we fully start up.
     */

    GPIOPin keepOn = PWR_KEEP_ON_GPIO;
    keepOn.setControl(GPIOPin::OUT_2MHZ);
    boardPowerEnable();

    GPIOPin imx6 = PWR_IMX6_GPIO;
    imx6.setControl(GPIOPin::OUT_2MHZ);
    disableIMX6();

    sysState = Boot;
}

void PowerManager::waitForCompleteStartup()
{
    /*
     * Called once during system init.
     *
     * if the user clicks the power button,
     * we show the battery level for 4 seconds and then shutdown.
     *
     * if the user holds the power button either from power on,
     * or at any time during those 4 seconds, we continue starting up.
     */

    if (Rcc::pinReset()) {
        // if we woke up from NRST being pressed,
        // assume we were bootloaded and don't wait for button press
        enterRunningState();
        return;
    }

    Battery &batt = Battery::instance;

    // run the task loop briefly to allow the battery to initialize.
    // if battery is not connected, don't bother waiting for it.
    if (batt.batteryIsPresent()) {
        while (!batt.isInitialized()) {
            if (!Tasks::work()) {
                Sys::waitForInterrupt();
            }
        }
    }

    // by default, we assume that we've been booted by the power button
    BootSource bootSource = BootSrcPowerButton;

    if (batt.chargerIsPresent()) {
        // did we startup because we reset ourselves out of idle?
        if (!Rcc::swReset()) {
            bootSource = BootSrcCharger;
        }

    } else {
        if (Pwr::voltageDetectorIsBelowThresh()) {
            shutdown();
            return;
        }

        // charger is not connected - do we have enough batt to start up?
        if (batt.level() <= Battery::CRITICALLY_LOW_PERCENT) {
            Ui::instance.power.drawBatteryTooLowToStart();
            Ui::instance.setBacklightsForState(sysState);
            shutdownAfterDelay(POWER_STATUS_MILLIS);
            return;
        }
    }

    // if we woke up because we detected uart traffic,
    // skip battery check and go straight to splash screen.
    if (Rcc::swReset() && BKP.DR1 == UART_WAKEUP_KEY) {
        enterRunningState();
        return;
    }

    Button &btn = ButtonManager::button(Io::ButtonPower);

    const SysTime::Ticks BatteryCheckInterval = SysTime::msTicks(4000);
    // XXX: would prefer this to be HoldMillis rather than LongHold Millis,
    //      but this is a workaround to the power rail crapping out before the RC delay
    //      to the imx6 has completed. in that case, the display can lose power and
    //      get stuck on a white (uninitialized) screen.
    const SysTime::Ticks CompleteStartupInterval = SysTime::msTicks(Button::LongHoldMillis);

    bool drawn = false;
    if (bootSource == BootSrcCharger) {
        Ui::instance.power.drawChargerConnected();
        Ui::instance.setBacklightsForState(sysState);
        drawn = true;
    }

    while (SysTime::now() < BatteryCheckInterval || btn.isPressed()) {

        /*
         * if the imx6 has somehow booted and is already sending us uart traffic,
         * assume we should just boot up.
         *
         * this means we can boot in cases where the user has not actually
         * performed the hold-power-to-boot gesture, but the most important
         * bit is to ensure that we're not in a state in which the imx6 has
         * booted and we haven't.
         */
        if (HostProtocol::instance.connected()) {
            enterRunningState();
            return;
        }

        if (btn.pressDuration() >= CompleteStartupInterval) {
            enterRunningState();

            // ensure this button hold doesn't shut us down once tasks start running
            btn.suppressCurrentHoldEvent();
            Haptic::startPattern(Haptic::SingleShort);
            return;
        }

        if (!drawn && !btn.isPressed()) {
            Ui::instance.power.drawBatteryCheck();
            Ui::instance.setBacklightsForState(sysState);
            drawn = true;
        }

        Sys::waitForInterrupt();
    }

    shutdown();
}

void PowerManager::enterRunningState()
{
    /*
     * Called during startup, once we determine that we're
     * not just showing a battery check screen.
     *
     * We now want to fire up the imx6 and let the UI know.
     */

    enableIMX6();
    sysState = Running;
    Ui::instance.pendEvent(Event::SystemEnteredRunningState);

    HostProtocol::instance.enableTX();
}

bool PowerManager::canShutDown()
{
    /*
     * Decline to shut down if we're updating.
     *
     * otherwise, if we've enabled the imx6, we must have heard from it before
     * we can plausibly shut it down, otherwise it may miss our shutdown command.
     *
     * The main scenario in which we might not have heard from the imx6
     * is when it's still booting. If after a generous duration of time we still
     * haven't heard something, we assume it's better to shut down than to stay on forever.
     */

    if (imx6Enabled()) {

        if (Ui::instance.state() == Ui::Updater) {
            return false;
        }

        static const unsigned GENEROUS_IMX6_BOOT_SECONDS = 40;
        if (SysTime::now() > SysTime::sTicks(GENEROUS_IMX6_BOOT_SECONDS)) {
            return true;
        }

        return HostProtocol::instance.connected();
    }

    return true;
}

void PowerManager::shutdownAfterDelay(unsigned millis)
{
    // helper to shutdown after showing some power related ui

    while (SysTime::now() < SysTime::msTicks(millis)) {
        Sys::waitForInterrupt();
    }

    shutdown();
}

void PowerManager::onButtonEvt(Button *b, Button::Event evt)
{
    if (b->id() != Io::ButtonPower) {
        return;
    }

    // if we're idle/charging and we get a power button press,
    // reset the system to wake up as usual
    if (sysState == Idle) {
        if (evt == Button::Press) {
            NVIC.systemReset();
        }

    } else {
        if (evt == Button::LongHold) {
            if (canShutDown()) {
                // edge case: we're already shutting down,
                // and the user is holding power for some reason?
                if (Ui::instance.state() != Ui::Shutdown) {
                    Haptic::startPattern(Haptic::SingleShort);
                }
                Tasks::trigger(Tasks::Shutdown);
            }
        }
    }
}

bool PowerManager::producePacket(HostProtocol::Packet &p)
{
    if (notifyShutdown) {
        p.delimitSlip();
        p.appendSlip(HostProtocol::ShutdownRequest);
        p.delimitSlip();
        notifyShutdown = false;

        // mark that we expect the host to go away,
        // don't consider it reconnected till we hear form it again
        HostProtocol::instance.onHostDisconnected();
        return true;
    }

    return false;
}

void PowerManager::shutdown()
{
    /*
     * Called from task context to shutdown the system,
     * or go to idle if the charger is connected.
     *
     * kill visible elements (backlights),
     * and release the power enable line.
     */

    if (!canShutDown()) {
        return;
    }

    notifyShutdown = true;
    HostProtocol::instance.requestTransaction();

    Params::sys.save();
    ButtonManager::shutdown();

    // do we need to show a shutdown sequence?
    // if not, fast forward past it
    if (sysState == Running) {
        Ui::instance.pendEvent(Event::SystemShutdown);
    } else {
        onShutdownSequenceComplete();
    }

    if (Battery::instance.chargerIsPresent()) {
        /*
         * We'd ideally go into standby here, but we need to stay awake
         * enough to continue sampling ADCs and managing the battery charging.
         */
        return;
    }
}

void PowerManager::onShutdownSequenceComplete()
{
    /*
     * Called once any user facing shutdown info is complete,
     * either from UI, or from ourselves if UI was skipped.
     *
     * Leave chg_enable as is, since if the charger is connected,
     * it will keep us alive and continue to be mmanaged by battery.cpp,
     * otherwise charger is not there and we'll just shut down.
     */

    sysState = Idle;

    HostProtocol::instance.disableTX();
    Ui::instance.setBacklightsForState(sysState);

    disableIMX6();
    boardPowerDisable();
}

void PowerManager::updatePowerDown()
{
    /*
     * Called from the UI update loop when we're
     * in the PowerDown state.
     *
     * If for some reason, we hear from the imx6, wake back up.
     */

    if (HostProtocol::instance.connected()) {
        BKP.DR1 = UART_WAKEUP_KEY;
        NVIC.systemReset();
    }
}

bool PowerManager::rcIsDischarged()
{
    /*
     * During shutdown, we want to wait until the RC circuit
     * is fully discharged before powering off, to avoid the
     * case in which the imx6 can be immediately woken up
     * as soon as we power off.
     *
     * In fact, we need to be able to handle that case anyway,
     * but this increases the likelihood that the entire system
     * is in agreement about its shutdown state.
     */

    static const unsigned DISCHARGE_MILLIS = 2500;
    const Button & b = ButtonManager::button(Io::ButtonPower);

    if (b.isPressed()) {
        return false;
    }

    const SysTime::Ticks timeSinceLastRelease = SysTime::now() - b.releasedAt();
    return timeSinceLastRelease > SysTime::msTicks(DISCHARGE_MILLIS);
}

void PowerManager::onExtendedShutdown()
{
    /*
     * The system has detected that it's alive significantly beyond
     * the point it expected to shutdown.
     *
     * This can happen if the charger gets connected while we're shutting down,
     * such that we stay alive even though we've released PWR_KEEP_ON.
     */

    if (!Battery::instance.chargerIsPresent()) {
        NVIC.systemReset();
    }
}
