#ifndef GFX_H
#define GFX_H

#include "stm32/common.h"

class Gfx
{
public:
    Gfx();  // do not implement

    enum ImageFormat {
        ImgFmtRaw,      // uncompressed
        ImgFmtRle,      // run length encoded
    };

    struct ImagePalette {
        const uint16_t *colors; // variable length
        uint8_t maxIdx; // count - 1

        ALWAYS_INLINE uint16_t color(uint8_t idx) const {
            ASSERT(idx <= maxIdx);
            return colors[idx];
        }
    };

    struct ImageAsset {
        uint16_t width;
        uint16_t height;
        uint8_t format;     // see ImageFormat
        uint8_t reserved;
        const void *data;
        const ImagePalette *palette;
    };

    struct GlyphAsset {
        const uint8_t *data;    // variable length
        uint8_t width;
        uint8_t height;
        // format is common to font that contains this glyph
    };

    struct FontAsset {
        uint8_t glyphCount;
        uint8_t ascent;
        uint8_t descent;
        uint8_t format; // see ImageFormat
        char start_ch;
        uint8_t reserved0;
        uint16_t reserved1;
        const GlyphAsset *glyphs; // variable length
        const ImagePalette *palette;

        ALWAYS_INLINE uint16_t height() const {
            return ascent + descent;
        }

        ALWAYS_INLINE bool hasGlyph(char c) const {
            return (c >= start_ch && c < start_ch + glyphCount);
        }

        ALWAYS_INLINE const GlyphAsset & glyph(char c) const {
            ASSERT(hasGlyph(c));
            return glyphs[c - start_ch];
        }
    };

    struct Rect {
        uint16_t x;
        uint16_t y;
        uint16_t width;
        uint16_t height;

        Rect(uint16_t _x, uint16_t _y, uint16_t w, uint16_t h):
            x(_x), y(_y), width(w), height(h)
        {}

        uint32_t pixelCount() const {
            return width * height;
        }
    };

    static const unsigned WIDTH;
    static const unsigned HEIGHT;

    /* FontColorConverter is used to convert a font from a grayscale white-on-black version to
       a colored version given foreground and background colors during initialization. */
    class FontColorConverter {
    public:
        uint8_t R1;
        uint8_t R2;
        uint8_t G1;
        uint8_t G2;
        uint8_t B1;
        uint8_t B2;

        void init(uint16_t color_fg, uint16_t color_bg);

        ALWAYS_INLINE uint16_t grayToColor(uint16_t gray) {
            uint8_t gray_comp = R(gray);
            return Gfx::COLOR(grayToR(gray_comp),grayToG(gray_comp),grayToB(gray_comp));
        }

    private:
        // reverse of RGBToColor : (b & 0xf8) << 8 | ((g & 0xfc) << 3) | ((r & 0xf8) >> 3);
        static ALWAYS_INLINE uint8_t R(uint16_t rgb) {
            return (rgb << 3) & 0xFF;
        }
        static ALWAYS_INLINE uint8_t G(uint16_t rgb) {
            return (rgb >> 3) & 0xFF;
        }
        static ALWAYS_INLINE uint8_t B(uint16_t rgb) {
            return (rgb >> 8) & 0xFF;
        }

        ALWAYS_INLINE uint8_t grayToR(uint8_t gray) {
            //DBG(("[Red]\n\n"));
            return convertRange(R1,R2,gray);
        }
        ALWAYS_INLINE uint8_t grayToG(uint8_t gray) {
            //DBG(("[Green]\n\n"));
            return convertRange(G1,G2,gray);
        }
        ALWAYS_INLINE uint8_t grayToB(uint8_t gray) {
            //DBG(("[Blue]\n\n"));
            return convertRange(B1,B2,gray);
        }

        uint8_t convertRange(int16_t min2, int16_t max2, int16_t x){
            //DBG(("For: %d, %d, %d, %d, %d\n", min1, max1, min2, max2, x));
            //DBG(("     %f, %f\n",(double)((x - min1) * (max2 - min2)),(double)(max1 - min1)));
            //DBG(("Result: %d, %f\n",(uint8_t)((double)((x - min1) * (max2 - min2)) / (double)(max1 - min1)) + min2,((double)((x - min1) * (max2 - min2)) / (double)(max1 - min1)) + min2));
            return scale(x, min1, max1, min2, max2);
        }

        ALWAYS_INLINE uint16_t origColor(uint16_t color) {
            return color;
        }

        static const int16_t min1 = 0;
        static const int16_t max1 = 0xFF;
    };

    static constexpr uint16_t COLOR(uint8_t r, uint8_t g, uint8_t b) {
        // compatible with ILI9341 format
        return (b & 0xf8) << 8 | ((g & 0xfc) << 3) | ((r & 0xf8) >> 3);
    }

    static void init();

    static void beginDrawingRegion(const Rect &r);
    static void drawPixelAtCursor(uint16_t color);

    static void clear(uint16_t color);
    static void fillRect(const Rect & w, uint16_t color);

    static void drawImage(int16_t x, int16_t y, const ImageAsset &img);
    static uint16_t drawImageCanvasHCentered(int16_t y, const ImageAsset &img);
    static void drawGlyph(char c, int16_t x, int16_t y, const FontAsset &font);
    static void drawGlyph(char c, int16_t x, int16_t y, const FontAsset &font, uint16_t *color_fg, uint16_t *color_bg);

    static uint16_t stringWidth(const char *s, const FontAsset & font);
    static uint16_t stringWidth(const char *s, const char *s_end, const FontAsset & font);
    static uint16_t write(uint16_t x, uint16_t y, const char *s, const FontAsset & font);
    static uint16_t write(uint16_t x, uint16_t y, const char *s, const char *s_end, const FontAsset & font);
    static uint16_t write(uint16_t x, uint16_t y, const char *s, const FontAsset & font, uint16_t *color_fg, uint16_t *color_bg);
    static uint16_t write(uint16_t x, uint16_t y, const char *s, const char *s_end, const FontAsset & font, uint16_t *color_fg, uint16_t *color_bg);
    static uint16_t writeMonospace(uint16_t x, uint16_t y, const char *s, const FontAsset & font, char box, uint16_t *color_fg = NULL, uint16_t *color_bg = NULL);
    static void writeRightJustified(uint16_t x, uint16_t y, unsigned w, const char *s, const FontAsset & font);
    static void writeCenterJustified(uint16_t x, uint16_t y, unsigned center, const char *s, const FontAsset & font);
    static void writeCanvasCenterJustified(uint16_t y, const char *s, const FontAsset & font);
    static void writeCanvasCenterJustified(uint16_t y, const char *s, const FontAsset & font, uint16_t line_spacing_h);
    static void writeCanvasCenterJustified(uint16_t y, const char *s, const FontAsset & font, uint16_t *color_fg, uint16_t *color_bg);
    static void writeCanvasCenterJustified(uint16_t y, const char *s, const FontAsset & font, uint16_t line_spacing_h, uint16_t *color_fg, uint16_t *color_bg);

private:
    static void drawBitmapBytes(int16_t x, int16_t y, ImageFormat fmt, const ImagePalette *p, const uint8_t *bytes, unsigned w, unsigned h);
    static void drawBitmapBytes(int16_t x, int16_t y, ImageFormat fmt, const ImagePalette *p, const uint8_t *b, unsigned w, unsigned h, uint16_t *color_fg, uint16_t *color_bg);
};

#endif // GFX_H
