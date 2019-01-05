#include "buzzer.h"
#include "board.h"

#include "stm32/gpio.h"

void Buzzer::init(unsigned hz)
{
    HwTimer buzzTimer(&BUZZ_PWM_TIM);
    GPIOPin buzzPin = BUZZ_PWM_GPIO;

    buzzTimer.init(72000 / hz, 1000);
    buzzTimer.configureChannelAsOutput(BUZZ_PWM_CH,
                                       HwTimer::ActiveHigh,
                                       HwTimer::Pwm1,
                                       HwTimer::SingleOutput);
    buzzTimer.setDuty(BUZZ_PWM_CH, 0x50);
    buzzPin.setControl(GPIOPin::OUT_ALT_2MHZ);

#if (BOARD >= BOARD_BB03)
    // TIM2 partial remap
    AFIO.MAPR |= (0x2 << 8);
#endif
}

void Buzzer::setFrequency(unsigned hz)
{
    HwTimer(&BUZZ_PWM_TIM).setPeriod(72000 / hz, 1000);
}

void Buzzer::play()
{
    HwTimer(&BUZZ_PWM_TIM).enableChannel(BUZZ_PWM_CH);
}

void Buzzer::stop()
{
    HwTimer(&BUZZ_PWM_TIM).disableChannel(BUZZ_PWM_CH);
}
