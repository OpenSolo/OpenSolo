
/*
 * application entry point.
 * early board init happens in setup.cpp
 */

#include "stm32/sys.h"
#include "stm32/gpio.h"
#include "stm32/systime.h"
#include "stm32/mcuflash.h"
#include "stm32/rcc.h"
#include "stm32/pwr.h"
#include "stm32/bkp.h"

#include "ui.h"
#include "inputs.h"
#include "tasks.h"
#include "haptic.h"
#include "buzzer.h"
#include "cameracontrol.h"
#include "hostprotocol.h"
#include "buttonmanager.h"
#include "battery.h"
#include "powermanager.h"
#include "board.h"

int main()
{
    // enable power manager first, to ensure we stay turned on
    PowerManager::init();
    Rcc::latchAndClearResetFlags();

    Pwr::init();
    Pwr::enableVoltageDetector(Pwr::PVD_2_4V);

    Bkp::init();

    // EXTI lines for buttons
    NVIC.irqEnable(IVT.EXTI0);
    NVIC.irqEnable(IVT.EXTI1);
    NVIC.irqEnable(IVT.EXTI2);
    NVIC.irqEnable(IVT.EXTI3);
    NVIC.irqEnable(IVT.EXTI4);
    NVIC.irqEnable(IVT.EXTI9_5);
    NVIC.irqEnable(IVT.EXTI15_10);

    // ADC
    NVIC.irqEnable(IVT.DMA1_Channel1);

    // UART rx
    NVIC.irqEnable(IVT.HOST_UART);

    SysTime::init(Tasks::heartbeat);

#if (BOARD >= BOARD_BB03)
    Battery::instance.init();
#endif

    // before other subsystems that depend on params
    Params::sys.load();

    HostProtocol::instance.init();
    ButtonManager::init();
    Ui::instance.init();

    CameraControl::instance.init();
    FlightManager::instance.init();

    // ensure our ADC values are initialized as soon as possible
    Inputs::init();
    Haptic::init();

    PowerManager::waitForCompleteStartup();

    // for now, initial values in backup registers are only
    // available during boot. cleared as we enter the task loop.
    Bkp::reset();

    for (;;) {
        if (!Tasks::work()) {
            Sys::waitForInterrupt();
        }
    }

    return 0;
}
