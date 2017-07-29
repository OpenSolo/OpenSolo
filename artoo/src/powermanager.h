#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include "button.h"
#include "hostprotocol.h"
#include "board.h"

class PowerManager
{
public:
    PowerManager(); // do not implement

    enum SysState {
        Boot,       // battery check or charger connected notification
        Idle,       // asleep/charging
        Running,    // normal operation
    };

    static void init();
    static void waitForCompleteStartup();
    static void onButtonEvt(Button *b, Button::Event evt);
    static bool producePacket(HostProtocol::Packet &p);
    static void shutdown();
    static void onShutdownSequenceComplete();
    static void updatePowerDown();
    static void onExtendedShutdown();

    static bool rcIsDischarged();

    static SysState state() {
        return sysState;
    }

    static ALWAYS_INLINE bool imx6Enabled() {
        return PWR_IMX6_GPIO.isOutputHigh();
    }

private:
    static const unsigned POWER_STATUS_MILLIS = 4000;
    static const uint16_t UART_WAKEUP_KEY = 0x8765;

    enum BootSource {
        BootSrcPowerButton,
        BootSrcCharger,
    };

    static ALWAYS_INLINE void enableIMX6() {
        PWR_IMX6_GPIO.setHigh();
    }

    static ALWAYS_INLINE void disableIMX6() {
        PWR_IMX6_GPIO.setLow();
    }

    static ALWAYS_INLINE void boardPowerEnable() {
        PWR_KEEP_ON_GPIO.setHigh();
    }
    static ALWAYS_INLINE void boardPowerDisable() {
        PWR_KEEP_ON_GPIO.setLow();
    }

    static void enterRunningState();
    static bool canShutDown();
    static void shutdownAfterDelay(unsigned millis);

    static bool notifyShutdown;
    static SysState sysState;
};

#endif // POWER_MANAGER_H
