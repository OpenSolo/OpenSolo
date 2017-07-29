
#include "stm32/vectors.h"
#include "stm32/gpio.h"
#include "board.h"

#include "buttonmanager.h"
#include "ili9341parallel.h"

/*
 * Some EXTI vectors serve more than one EXTI line - this serves as a neutral
 * spot to dispatch the pending interrupts.
 *
 * I/O mappings are in board.h
 */

IRQ_HANDLER ISR_EXTI0()
{
    ButtonManager::isr(Io::ButtonPower);
}

IRQ_HANDLER ISR_EXTI1()
{
    ButtonManager::isr(Io::ButtonRTL);
}

IRQ_HANDLER ISR_EXTI2()
{
    ButtonManager::isr(Io::ButtonLoiter);
}

IRQ_HANDLER ISR_EXTI3()
{
    ButtonManager::isr(Io::ButtonA);
}

IRQ_HANDLER ISR_EXTI4()
{
    ButtonManager::isr(Io::ButtonB);
}

IRQ_HANDLER ISR_EXTI9_5()
{
    ButtonManager::isr(Io::ButtonPreset1);
    ButtonManager::isr(Io::ButtonPreset2);
    ButtonManager::isr(Io::ButtonFly);

    ILI9341Parallel::tearingEffectIsr();
}

IRQ_HANDLER ISR_EXTI15_10()
{
    ButtonManager::isr(Io::ButtonCameraClick);
}
