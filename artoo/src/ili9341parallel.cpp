#include "ili9341parallel.h"
#include "tasks.h"
#include "board.h"

#include "stm32/sys.h"
#include "stm32/hwtimer.h"

ILI9341Parallel ILI9341Parallel::lcd;
SysTime::Ticks ILI9341Parallel::lastTeIsr;

ILI9341Parallel::ILI9341Parallel() :
    display(reinterpret_cast<FsmcInterface*>(Fsmc::Bank1Base))
{
}

static void delay(unsigned millis)
{
    // helper for init.
    SysTime::Ticks deadline = SysTime::now() + SysTime::msTicks(millis);
    while (SysTime::now() < deadline) {
        Sys::waitForInterrupt();
    }
}


void ILI9341Parallel::init()
{
    /*
     * XXX: double check relevant timing characteristics.
     */
    static const Fsmc::Config cfg = {
        Fsmc::MTYP_SRAM_ROM |
            Fsmc::MWID_16BIT |
            Fsmc::WREN,
        Fsmc::NorSramTimingInit(1, 0, 5, 0, 0, 0, 0),
        Fsmc::Bank1,
    };

    GPIOPin dataPins[] = {
        DISPLAY_GPIO_D0,
        DISPLAY_GPIO_D1,
        DISPLAY_GPIO_D2,
        DISPLAY_GPIO_D3,
        DISPLAY_GPIO_D4,
        DISPLAY_GPIO_D5,
        DISPLAY_GPIO_D6,
        DISPLAY_GPIO_D7,
        DISPLAY_GPIO_D8,
        DISPLAY_GPIO_D9,
        DISPLAY_GPIO_D10,
        DISPLAY_GPIO_D11,
        DISPLAY_GPIO_D12,
        DISPLAY_GPIO_D13,
        DISPLAY_GPIO_D14,
        DISPLAY_GPIO_D15
    };

    GPIOPin ctrlPins[] = {
        DISPLAY_GPIO_NOE,
        DISPLAY_GPIO_NWE,
        DISPLAY_GPIO_CS,
        DISPLAY_GPIO_DC
    };

    GPIOPin te = DISPLAY_GPIO_TE;
    te.setControl(GPIOPin::IN_PULL);
    te.irqInit();
    te.irqSetRisingEdge();
    te.irqEnable();

#if (BOARD >= BOARD_DVT)
    // XXX: LED_PWM_TIM is init'd in buttonmanager.cpp
    //      could break that out to a common module at some point...
    HwTimer tim(&LED_PWM_TIM);
    tim.configureChannelAsOutput(DISPLAY_LED_PWM_CH,
                                 HwTimer::ActiveLow,
                                 HwTimer::Pwm1,
                                 HwTimer::SingleOutput);
#else
    DISPLAY_LED_GPIO.setControl(GPIOPin::OUT_2MHZ);
#endif

    disableBacklight();

    DISPLAY_GPIO_RST.setControl(GPIOPin::OUT_2MHZ);

    reset();

    Fsmc::initNorSram(dataPins, arraysize(dataPins), ctrlPins, arraysize(ctrlPins), cfg);

    static const uint8_t initseq[] = {
        /*
         * init values from tianma for the TM024HDH71
         */
        4, CMD_POWER_CONTROL_B,             0x00, 0xDB, 0x30,
        5, CMD_POWER_ON_SEQ_CONTROL,        0x64, 0x03, 0x12, 0x81,
        6, CMD_POWER_CONTROL_A,             0x39, 0x2C, 0x00, 0x34, 0x02,
        2, CMD_PUMP_RATIO_CONTROL,          0x20,
        3, CMD_DRIVER_TIMING_CONTROL_B,     0x00, 0x00,
        2, CMD_MEMORY_ACCESS_CONTROL,       (SWITCH_XY | FLIP_Y),
        3, CMD_DISPLAY_FUNCTION_CONTROL,    0x0A, 0xA2,
        2, CMD_POWER_CONTROL_1,             0x2B,
        2, CMD_POWER_CONTROL_2,             0x10,
        3, CMD_VCOM_CONTROL_1,              0x35, 0x32,
        2, CMD_VCOM_CONTROL_2,              0xBD,
        2, CMD_ENABLE_3_GAMMA_CONTROL,      0x00,
        4, CMD_INTERFACE_CONTROL,           0x01, 0x31, 0x00,
        2, CMD_COLMOD_PIXEL_FORMAT_SET,     0x55,
        3, CMD_FRAME_RATE_CONTROL_NORMAL,   0x00, 0x19,
        5, CMD_BLANKING_PORCH_CONTROL,      0x04, 0x04, 0x0A, 0x14,
        4, CMD_DRIVER_TIMING_CONTROL_A,     0x85, 0x10, 0x7A,
        2, CMD_DISPLAY_INVERSION_CONTROL,   0x00,
        2, CMD_TEARING_EFFECT_LINE_ON,      0x00,
        16, CMD_POSITIVE_GAMMA_CORRECTION,  0x00, 0x21, 0x1E, 0x0B, 0x0F, 0x09, 0x4C, 0xC5, 0x3B, 0x09, 0x0B, 0x04, 0x16, 0x17, 0x00,
        16, CMD_NEGATIVE_GAMMA_CORRECTION,  0x0F, 0x1E, 0x21, 0x04, 0x10, 0x07, 0x34, 0x76, 0x44, 0x06, 0x14, 0x0B, 0x27, 0x38, 0x0F,
        1, CMD_SLEEP_OUT,
        0
    };
    sendCommandTable(initseq);
    delay(120);
    writeCmd(CMD_DISPLAY_ON);
}

void ILI9341Parallel::reset()
{
    /*
     * reset the display by toggling its reset line
     * in the required pattern.
     */

    GPIOPin rst = DISPLAY_GPIO_RST;

    rst.setHigh();
    delay(10);

    rst.setLow();
    delay(10);

    rst.setHigh();
    delay(150);
}

void ILI9341Parallel::enableBacklight()
{
    /*
     * Attach the backlight gpio to the timer peripheral
     * so it can be driven via PWM.
     */

#if (BOARD >= BOARD_DVT)

    DISPLAY_LED_GPIO.setControl(GPIOPin::OUT_ALT_OPEN_50MHZ);
    HwTimer(&LED_PWM_TIM).enableChannel(DISPLAY_LED_PWM_CH);

    setBacklight(100);

#else
    DISPLAY_LED_GPIO.setHigh();
#endif
}

void ILI9341Parallel::disableBacklight()
{
    /*
     * Reconfigure the backlight gpio as standard open drain
     * so we can keep its output constant.
     */

#if (BOARD >= BOARD_DVT)

    HwTimer(&LED_PWM_TIM).disableChannel(DISPLAY_LED_PWM_CH);
    setBacklight(0);

    GPIOPin bklight = DISPLAY_LED_GPIO;
    bklight.setHigh();
    bklight.setControl(GPIOPin::OUT_OPEN_2MHZ);

#else
    DISPLAY_LED_GPIO.setLow();
#endif
}

void ILI9341Parallel::setBacklight(unsigned percent)
{
    /*
     * Set the pwm driving the LED backlight to the given percent.
     */

    ASSERT(percent <= 100);

    HwTimer tim(&LED_PWM_TIM);
    uint16_t duty = percent * tim.period() / 100;
    tim.setDuty(DISPLAY_LED_PWM_CH, duty);
}

void ILI9341Parallel::shutdown()
{
#if (BOARD >= BOARD_BB03)
    DISPLAY_GPIO_TE.irqDisable();
#endif
    disableBacklight();
    Tasks::cancel(Tasks::DisplayRender);
}

void ILI9341Parallel::tearingEffectIsr()
{
    /*
     * Once the tearing line goes high,
     * we have a chance to write to the display
     * while it is not rendering from GRAM. This helps
     * avoid desynced display updates, assuming we're done
     * updating GRAM before the display starts another refresh.
     */

#if (BOARD >= BOARD_BB03)
    GPIOPin te = DISPLAY_GPIO_TE;
    if (te.irqPending()) {
        te.irqAcknowledge();
        Tasks::trigger(Tasks::DisplayRender);
        lastTeIsr = SysTime::now();
    }
#endif
}

void ILI9341Parallel::sendCommandTable(const uint8_t *p)
{
    for (;;) {
        uint8_t len = *p++;
        if (len == 0) {
            break;
        }

        writeCmd(*p++);
        len--;

        while (len--) {
            writeData(*p++);
        }
    }
}

void ILI9341Parallel::setOrientation(uint8_t flags)
{
    writeCmd(CMD_MEMORY_ACCESS_CONTROL);
    writeData(flags);
}

void ILI9341Parallel::setRect(const Gfx::Rect & r)
{
    uint16_t bottomRightX = r.x + r.width - 1;
    uint16_t bottomRightY = r.y + r.height - 1;

    writeCmd(CMD_COLUMN_ADDRESS_SET);
    writeData(r.x >> 8);
    writeData(r.x & 0xFF);
    writeData(bottomRightX >> 8);
    writeData(bottomRightX & 0xFF);

    writeCmd(CMD_PAGE_ADDRESS_SET);
    writeData(r.y >> 8);
    writeData(r.y & 0xFF);
    writeData(bottomRightY >> 8);
    writeData(bottomRightY & 0xFF);
}

void ILI9341Parallel::fill(uint16_t color, unsigned count)
{
    writeCmd(CMD_MEMORY_WRITE);
    for (unsigned i = 0; i < count; ++i) {
        writeData(color);
    }
}
