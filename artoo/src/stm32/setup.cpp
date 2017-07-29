
/*
 * Low level hardware setup for the STM32 board.
 */

#include "hw.h"
#include "gpio.h"

#include <string.h>
#include <stdio.h>

// for HW testing - enables system clock output on PA8. disabled by default.
//#define ENABLE_MCO

#ifdef ENABLE_MCO
    #define MCO_VAL 0x07
#else
    #define MCO_VAL 0x00
#endif

/* One function in the init_array segment */
typedef void (*initFunc_t)(void);

/* Addresses defined by our linker script */
extern unsigned     __bss_start;
extern unsigned     __bss_end;
extern unsigned     __data_start;
extern unsigned     __data_end;
extern unsigned     __data_src;
extern initFunc_t   __init_array_start;
extern initFunc_t   __init_array_end;

extern int  main()  __attribute__((noreturn));

// we don't link against newlib c runtime,
// so must initialize monitor handles explicitly for semihosting
extern "C" void initialise_monitor_handles(void);

extern "C" void _start()
{
    /*
     * Set up clocks:
     *   - 12 MHz HSE (xtal) osc
     *   - PLL x6 => 72 MHz
     *   - SYSCLK at 72 MHz
     *   - HCLK at 36 MHz
     *   - APB1 at 36 MHz (no divisor)
     *   - APB2 at 36 MHz (no divisor)
     *
     * Other things that depend on our clock setup:
     *
     *   - UART configuration. See APB2RATE & APB1RATE in usart.cpp
     *
     *   - SysTick frequency, in systime.cpp. The Cortex-M3's
     *     system clock is 1/8th the AHB clock.
     */

    // system runs from HSI on reset - make sure this is on and stable
    // before we switch away from it
    RCC.CR |= (1 << 0); // HSION
    while (!(RCC.CR & (1 << 1))); // wait for HSI ready

    RCC.CR &=  (0x1F << 3)  |   // HSITRIM reset value
            (1 << 0);        // HSION
    RCC.CFGR = 0;       // reset
    // Wait until HSI is the source.
    while ((RCC.CFGR & (3 << 2)) != 0x0);

    // fire up HSE
    RCC.CR |= (1 << 16); // HSEON
    while (!(RCC.CR & (1 << 17))); // wait for HSE to be stable

    // fire up the PLL
    RCC.CFGR |= (4 << 18) |             // PLLMUL - x6
            (0 << 17)     |             // PLL XTPRE
            (1 << 16);                  // PLLSRC - HSE
    RCC.CR   |= (1 << 24);              // turn PLL on
    while (!(RCC.CR & (1 << 25)));      // wait for PLL to be ready

    // configure all the other buses
    RCC.CFGR =
            (MCO_VAL << 24)           | // MCO - mcu clock output
            (4 << 18)                 | // PLLMUL - x6
            (0 << 17)                 | // PLL XTPRE
            (1 << 16)                 | // PLLSRC - HSE
            (2 << 14)                 | // ADCPRE - div6, ADCCLK is 14Mhz max
            (0 << 11)                 | // PPRE2 - APB2 prescaler, no divisor
            (4 << 8)                  | // PPRE1 - APB1 prescaler, divide by 2
            (0 << 4);                   // HPRE - AHB prescaler, no divisor

    /*
     * Select appropriate flash wait states, based on SYSCLK:
     *
     *  000 - zero wait state, if 0 < SYSCLK <= 24 MHz
     *  001 - one wait state,  if 24 MHz < SYSCLK <= 48 MHz
     *  010 - two wait states, if 48 MHz < SYSCLK <= 72 MHz
     */

    FLASH.ACR |= (1 << 1);   // two wait states since we're @ 72MHz

    // switch to PLL as system clock
    RCC.CFGR |= (2 << 0);
    while ((RCC.CFGR & (3 << 2)) != (2 << 2));   // wait till we're running from PLL

    // reset all peripherals
    RCC.APB1RSTR = 0xFFFFFFFF;
    RCC.APB1RSTR = 0;
    RCC.APB2RSTR = 0xFFFFFFFF;
    RCC.APB2RSTR = 0;

    // Enable gpio clocks
    RCC.APB2ENR = 0x000001fd;    // GPIO/AFIO

#ifdef ENABLE_MCO
    // debug the clock output - MCO
    GPIOPin(&GPIOA, 8).setControl(GPIOPin::OUT_ALT_50MHZ);
#endif

    /*
     * Initialize data segments (In parallel with oscillator startup)
     */

    memset(&__bss_start, 0, (uintptr_t)&__bss_end - (uintptr_t)&__bss_start);
    memcpy(&__data_start, &__data_src,
           (uintptr_t)&__data_end - (uintptr_t)&__data_start);

    /*
     * Run C++ global constructors.
     *
     * Best-practice for these is to keep them limited to only
     * initializing data: We shouldn't be talking to hardware, or
     * doing anything long-running here. Think of it as a way to
     * programmatically unpack data from flash to RAM, just like we
     * did above with the .data segment.
     */

    for (initFunc_t *p = &__init_array_start; p != &__init_array_end; p++)
        p[0]();

#ifdef SEMIHOSTING
    initialise_monitor_handles();
#endif

    main();
}
