#ifndef BOARD_BB02_H
#define BOARD_BB02_H

/*
 * Pin and I/O definitions.
 */

////////////////////////////////////////
//              Inputs
////////////////////////////////////////

#define BTN_PWR_GPIO        GPIOPin(&GPIOA, 0)
#define BTN_FLY_GPIO        GPIOPin(&GPIOF, 7)
#define BTN_RTL_GPIO        GPIOPin(&GPIOE, 1)
#define BTN_LOITER_GPIO     GPIOPin(&GPIOE, 2)
#define BTN_A_GPIO          GPIOPin(&GPIOE, 3)
#define BTN_B_GPIO          GPIOPin(&GPIOE, 4)
#define BTN_PRESET1_GPIO    GPIOPin(&GPIOE, 5)
#define BTN_PRESET2_GPIO    GPIOPin(&GPIOE, 6)
#define BTN_CAM_CLICK_GPIO  GPIOPin(&GPIOC, 13)

#define ROLL_GPIO           GPIOPin(&GPIOC, 0)
#define ROLL_ADC_CH         10
#define PITCH_GPIO          GPIOPin(&GPIOC, 1)
#define PITCH_ADC_CH        11
#define THRO_GPIO           GPIOPin(&GPIOC, 2)
#define THRO_ADC_CH         12
#define YAW_GPIO            GPIOPin(&GPIOC, 3)
#define YAW_ADC_CH          13
#define GIMBAL_Y_GPIO       GPIOPin(&GPIOC, 4)
#define GIMBAL_Y_ADC_CH     14
#define GIMBAL_RATE_GPIO    GPIOPin(&GPIOC, 5)
#define GIMBAL_RATE_ADC_CH  15

#define BATT_LVL_GPIO       GPIOPin(&GPIOB, 0)
#define BATT_LVL_ADC_CH     8


////////////////////////////////////////
//              Outputs
////////////////////////////////////////

#define LED_BLUE_S1_GPIO    GPIOPin(&GPIOG, 11)
#define LED_BLUE_S2_GPIO    GPIOPin(&GPIOG, 10)
#define LED_BLUE_S3_GPIO    GPIOPin(&GPIOG, 2)
#define LED_BLUE_S4_GPIO    GPIOPin(&GPIOG, 3)
#define LED_BLUE_S5_GPIO    GPIOPin(&GPIOG, 4)
#define LED_BLUE_S6_GPIO    GPIOPin(&GPIOG, 5)

#define LED_WHITE_S1_GPIO   GPIOPin(&GPIOG, 9)
#define LED_WHITE_S2_GPIO   GPIOPin(&GPIOG, 8)
#define LED_WHITE_S3_GPIO   GPIOPin(&GPIOG, 7)
#define LED_WHITE_S4_GPIO   GPIOPin(&GPIOG, 6)
#define LED_WHITE_S5_GPIO   GPIOPin(&GPIOG, 13)
#define LED_WHITE_S6_GPIO   GPIOPin(&GPIOG, 12)

// arbitrary unconnected gpio to indicate LED control is not available
#define LED_GPIO_NONE       GPIOPin(&GPIOG, 15)

#define VIB_GPIO            GPIOPin(&GPIOA, 1)

#define LED_PWM_TIM         TIM3
#define LED_PWM_CH          3
#define LED_PWM_GPIO        GPIOPin(&GPIOC, 8)

#define BUZZ_PWM_TIM        TIM2
#define BUZZ_PWM_CH         3
#define BUZZ_PWM_GPIO       GPIOPin(&GPIOA, 2)


#define PWR_IMX6_GPIO       GPIOPin(&GPIOC, 14)
#define PWR_KEEP_ON_GPIO    GPIOPin(&GPIOC, 15)

////////////////////////////////////////
//              Comms
////////////////////////////////////////

#define HOST_UART           USART1
#define HOST_UART_TX_GPIO   GPIOPin(&GPIOA, 9)
#define HOST_UART_RX_GPIO   GPIOPin(&GPIOA, 10)
#define HOST_UART_DMA_TX_CH DMA1_Channel4


////////////////////////////////////////
//              Display
////////////////////////////////////////

#define DISPLAY_GPIO_NOE    GPIOPin(&GPIOD, 4)
#define DISPLAY_GPIO_NWE    GPIOPin(&GPIOD, 5)
#define DISPLAY_GPIO_CS     GPIOPin(&GPIOD, 7)
#define DISPLAY_GPIO_DC     GPIOPin(&GPIOF, 0)
#define DISPLAY_GPIO_RST    GPIOPin(&GPIOF, 1)

#define DISPLAY_GPIO_D0     GPIOPin(&GPIOD, 14)
#define DISPLAY_GPIO_D1     GPIOPin(&GPIOD, 15)
#define DISPLAY_GPIO_D2     GPIOPin(&GPIOD, 0)
#define DISPLAY_GPIO_D3     GPIOPin(&GPIOD, 1)
#define DISPLAY_GPIO_D4     GPIOPin(&GPIOE, 7)
#define DISPLAY_GPIO_D5     GPIOPin(&GPIOE, 8)
#define DISPLAY_GPIO_D6     GPIOPin(&GPIOE, 9)
#define DISPLAY_GPIO_D7     GPIOPin(&GPIOE, 10)
#define DISPLAY_GPIO_D8     GPIOPin(&GPIOE, 11)
#define DISPLAY_GPIO_D9     GPIOPin(&GPIOE, 12)
#define DISPLAY_GPIO_D10    GPIOPin(&GPIOE, 13)
#define DISPLAY_GPIO_D11    GPIOPin(&GPIOE, 14)
#define DISPLAY_GPIO_D12    GPIOPin(&GPIOE, 15)
#define DISPLAY_GPIO_D13    GPIOPin(&GPIOD, 8)
#define DISPLAY_GPIO_D14    GPIOPin(&GPIOD, 9)
#define DISPLAY_GPIO_D15    GPIOPin(&GPIOD, 10)

#endif // BOARD_BB02_H
