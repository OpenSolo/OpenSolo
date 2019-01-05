#ifndef ILI9341_PARALLEL_H
#define ILI9341_PARALLEL_H

#include "stm32/fsmc.h"
#include "stm32/systime.h"
#include "gfx.h"
#include "board.h"

class ILI9341Parallel
{
public:
    static const unsigned HEIGHT   = 240;
    static const unsigned WIDTH    = 320;

    ILI9341Parallel();

    static ILI9341Parallel lcd;

    void init();
    void reset();
    static void tearingEffectIsr();

    SysTime::Ticks ticksSinceLastTE() const {
        return SysTime::now() - lastTeIsr;
    }

    void enableBacklight();
    void disableBacklight();
    void setBacklight(unsigned percent);

    void shutdown();

    enum Orientation {
        SWITCH_XY  = (1 << 5),
        FLIP_X     = (1 << 6),
        FLIP_Y     = (1 << 7),
    };

    void setOrientation(uint8_t flags); // flags a la Orientation
    void setRect(const Gfx::Rect & r);

    void drawPixel(uint16_t color) {
        writeCmd(CMD_MEMORY_WRITE);
        writeData(color);
    }

    void ALWAYS_INLINE drawPixelAtCursor(uint16_t color) {
        writeData(color);
    }

    void ALWAYS_INLINE skipPixel() {
        /*
         * This is a little cheesy, but reading and re-writing
         * a background pixel is much faster than calling setWindow()
         * for each pixel.
         *
         * If there were a way to increment the write cursor without
         * writing, that would be ideal, but this is the best workaround
         * I've found so far.
         */
        writeData(readData());
    }

    void ALWAYS_INLINE beginDrawingRegion(const Gfx::Rect & r) {
        setRect(r);
        writeCmd(CMD_MEMORY_WRITE);
        // assume calls to drawPixel() follow
    }

    void fill(uint16_t color, unsigned count);

private:
    enum Command {
        // Level 1 Commands
        CMD_NOP                             = 0x00,
        CMD_SOFTWARE_RESET                  = 0x01,
        CMD_READ_DISP_ID                    = 0x04,
        CMD_READ_DISP_STATUS                = 0x09,
        CMD_READ_DISP_MADCTRL               = 0x0B,
        CMD_READ_DISP_PIXEL_FORMAT          = 0x0C,
        CMD_READ_DISP_IMAGE_FORMAT          = 0x0D,
        CMD_READ_DISP_SIGNAL_MODE           = 0x0E,
        CMD_READ_DISP_SELF_DIAGNOSTIC       = 0x0F,
        CMD_ENTER_SLEEP_MODE                = 0x10,
        CMD_SLEEP_OUT                       = 0x11,
        CMD_PARTIAL_MODE_ON                 = 0x12,
        CMD_NORMAL_DISP_MODE_ON             = 0x13,
        CMD_DISP_INVERSION_OFF              = 0x20,
        CMD_DISP_INVERSION_ON               = 0x21,
        CMD_GAMMA_SET                       = 0x26,
        CMD_DISPLAY_OFF                     = 0x28,
        CMD_DISPLAY_ON                      = 0x29,
        CMD_COLUMN_ADDRESS_SET              = 0x2A,
        CMD_PAGE_ADDRESS_SET                = 0x2B,
        CMD_MEMORY_WRITE                    = 0x2C,
        CMD_COLOR_SET                       = 0x2D,
        CMD_MEMORY_READ                     = 0x2E,
        CMD_PARTIAL_AREA                    = 0x30,
        CMD_VERT_SCROLL_DEFINITION          = 0x33,
        CMD_TEARING_EFFECT_LINE_OFF         = 0x34,
        CMD_TEARING_EFFECT_LINE_ON          = 0x35,
        CMD_MEMORY_ACCESS_CONTROL           = 0x36,
        CMD_VERT_SCROLL_START_ADDRESS       = 0x37,
        CMD_IDLE_MODE_OFF                   = 0x38,
        CMD_IDLE_MODE_ON                    = 0x39,
        CMD_COLMOD_PIXEL_FORMAT_SET         = 0x3A,
        CMD_WRITE_MEMORY_CONTINUE           = 0x3C,
        CMD_READ_MEMORY_CONTINUE            = 0x3E,
        CMD_SET_TEAR_SCANLINE               = 0x44,
        CMD_GET_SCANLINE                    = 0x45,
        CMD_WRITE_DISPLAY_BRIGHTNESS        = 0x51,
        CMD_READ_DISPLAY_BRIGHTNESS         = 0x52,
        CMD_WRITE_CTRL_DISPLAY              = 0x53,
        CMD_READ_CTRL_DISPLAY               = 0x54,
        CMD_WRITE_CONTENT_ADAPT_BRIGHTNESS  = 0x55,
        CMD_READ_CONTENT_ADAPT_BRIGHTNESS   = 0x56,
        CMD_WRITE_MIN_CAB_LEVEL             = 0x5E,
        CMD_READ_MIN_CAB_LEVEL              = 0x5F,
        CMD_READ_ID1                        = 0xDA,
        CMD_READ_ID2                        = 0xDB,
        CMD_READ_ID3                        = 0xDC,

        // Level 2 Commands
        CMD_RGB_SIGNAL_CONTROL              = 0xB0,
        CMD_FRAME_RATE_CONTROL_NORMAL       = 0xB1,
        CMD_FRAME_RATE_CONTROL_IDLE_8COLOR  = 0xB2,
        CMD_FRAME_RATE_CONTROL_PARTIAL      = 0xB3,
        CMD_DISPLAY_INVERSION_CONTROL       = 0xB4,
        CMD_BLANKING_PORCH_CONTROL          = 0xB5,
        CMD_DISPLAY_FUNCTION_CONTROL        = 0xB6,
        CMD_ENTRY_MODE_SET                  = 0xB7,
        CMD_BACKLIGHT_CONTROL_1             = 0xB8,
        CMD_BACKLIGHT_CONTROL_2             = 0xB9,
        CMD_BACKLIGHT_CONTROL_3             = 0xBA,
        CMD_BACKLIGHT_CONTROL_4             = 0xBB,
        CMD_BACKLIGHT_CONTROL_5             = 0xBC,
        CMD_BACKLIGHT_CONTROL_6             = 0xBD,
        CMD_BACKLIGHT_CONTROL_7             = 0xBE,
        CMD_BACKLIGHT_CONTROL_8             = 0xBF,
        CMD_POWER_CONTROL_1                 = 0xC0,
        CMD_POWER_CONTROL_2                 = 0xC1,
        CMD_VCOM_CONTROL_1                  = 0xC5,
        CMD_VCOM_CONTROL_2                  = 0xC7,
        CMD_POWER_CONTROL_A                 = 0xCB,
        CMD_POWER_CONTROL_B                 = 0xCF,
        CMD_NVMEM_WRITE                     = 0xD0,
        CMD_NVMEM_PROTECTION_KEY            = 0xD1,
        CMD_NVMEM_STATUS_READ               = 0xD2,
        CMD_READ_ID4                        = 0xD3,
        CMD_POSITIVE_GAMMA_CORRECTION       = 0xE0,
        CMD_NEGATIVE_GAMMA_CORRECTION       = 0xE1,
        CMD_DIGITAL_GAMMA_CONTROL_1         = 0xE2,
        CMD_DIGITAL_GAMMA_CONTROL_2         = 0xE3,
        CMD_DRIVER_TIMING_CONTROL_A         = 0xE8,
        CMD_DRIVER_TIMING_CONTROL_B         = 0xEA,
        CMD_POWER_ON_SEQ_CONTROL            = 0xED,
        CMD_ENABLE_3_GAMMA_CONTROL          = 0xF2,
        CMD_INTERFACE_CONTROL               = 0xF6,
        CMD_PUMP_RATIO_CONTROL              = 0xF7,

        COLMOD_12           = 3,
        COLMOD_16           = 5,
        COLMOD_18           = 6,

        MADCTR_MY           = 0x80,
        MADCTR_MX           = 0x40,
        MADCTR_MV           = 0x20,
        MADCTR_ML           = 0x10,
        MADCTR_RGB          = 0x08,
        MADCTR_MH           = 0x04,
    };

    /*
     * We access the display via FSMC Bank1 (NOR/SRAM), region 1.
     * The D/C line controls data/command mode, command is low, data is high.
     * In order to drive it high, we need to calculate the data address as follows:
     *
     *  dataAddr = baseAddr + (2 ^ (AddressLineIdx * 2))
     *
     * Our D/C line is routed on the FSMC A0 line, so our data offset
     * is 2 ^ (0 * 2) = 2, which gives us the uint16_t offset to our 'data' member.
     */
    struct FsmcInterface {
        uint16_t cmd;
        uint16_t data;
    };

    void sendCommandTable(const uint8_t *p);

    void ALWAYS_INLINE writeCmd(uint8_t c) {
        display->cmd = c;
    }

    void ALWAYS_INLINE writeData(uint16_t d) {
        display->data = d;
    }

    uint16_t ALWAYS_INLINE readData() const {
        return display->data;
    }

    volatile FsmcInterface *display;
    static SysTime::Ticks lastTeIsr;
};

#endif // ILI9341_PARALLEL_H
