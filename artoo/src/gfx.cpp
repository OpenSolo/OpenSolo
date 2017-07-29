#include "gfx.h"
#include "ili9341parallel.h"
#include "resources-gen.h"

#include <stdlib.h>

const unsigned Gfx::WIDTH = ILI9341Parallel::WIDTH;
const unsigned Gfx::HEIGHT = ILI9341Parallel::HEIGHT;

void Gfx::init()
{
    ILI9341Parallel::lcd.init();
    fillRect(Rect(0, 0, WIDTH, HEIGHT), 0x0);
}

void Gfx::drawPixelAtCursor(uint16_t color)
{
    static const unsigned AlphaKey = 0x3D3D;

    if (color == AlphaKey) {
        ILI9341Parallel::lcd.skipPixel();
    } else {
        ILI9341Parallel::lcd.drawPixelAtCursor(color);
    }
}

void Gfx::beginDrawingRegion(const Rect &r)
{
    ILI9341Parallel::lcd.beginDrawingRegion(r);
}

void Gfx::clear(uint16_t color)
{
    fillRect(Rect(0, 0, WIDTH, HEIGHT), color);
}

void Gfx::fillRect(const Rect & r, uint16_t color)
{
    ILI9341Parallel::lcd.setRect(r);
    ILI9341Parallel::lcd.fill(color, r.pixelCount());
}

void Gfx::drawImage(int16_t x, int16_t y, const ImageAsset &img) {
    drawBitmapBytes(x, y, static_cast<ImageFormat>(img.format), img.palette, static_cast<const uint8_t*>(img.data), img.width, img.height);
}

uint16_t Gfx::drawImageCanvasHCentered(int16_t y, const ImageAsset &img) {
    uint16_t x = WIDTH/2 - img.width/2;
    drawBitmapBytes(x, y, static_cast<ImageFormat>(img.format), img.palette, static_cast<const uint8_t*>(img.data), img.width, img.height);
    return x;
}

void Gfx::drawGlyph(char c, int16_t x, int16_t y, const FontAsset &font) {
    drawGlyph(c,x, y, font, NULL, NULL);
}

void Gfx::drawGlyph(char c, int16_t x, int16_t y, const FontAsset &font, uint16_t *color_fg, uint16_t *color_bg) {
    const GlyphAsset &g = font.glyph(c);
    drawBitmapBytes(x, y, static_cast<ImageFormat>(font.format), font.palette, static_cast<const uint8_t*>(g.data), g.width, g.height, color_fg, color_bg);
}

void Gfx::drawBitmapBytes(int16_t x, int16_t y, ImageFormat fmt, const ImagePalette *p, const uint8_t *b, unsigned w, unsigned h)
{
    drawBitmapBytes(x, y, fmt, p, b, w, h, NULL, NULL);
}

void Gfx::drawBitmapBytes(int16_t x, int16_t y, ImageFormat fmt, const ImagePalette *p, const uint8_t *b, unsigned w, unsigned h, uint16_t *color_fg, uint16_t *color_bg)
{
    /*
     * render img based on its format.
     */

    static const int8_t RLE_EOF = -128;

    switch (fmt) {
    case ImgFmtRaw:
        // XXX: this is not functional at the moment
        //      need to update to non-monochrome version if we want to use non-RLE images
        // gfx.drawBitmap(x, y, p, w, h, Adafruit_GFX::WHITE);
        break;

    case ImgFmtRle:
        /*
         * each chunk of data is specified by 1-byte header 'n':
         *  0 to 127:       Copy the next n + 1 symbols verbatim
         *  -127 to -1:     Repeat the next symbol 1 - n times
         *  -128:           EOF
         */

        beginDrawingRegion(Rect(x, y, w, h));
        FontColorConverter ch;
        bool isGrayscale;

        // check if we need to tranform pixels from grayscale to color
        if (color_fg && color_bg) {
            ch.init(*color_bg,*color_fg);
            isGrayscale = true;
        } else {
            isGrayscale = false;
        }

        for (;;) {
            int8_t header = *b++;

            if (header == RLE_EOF) {
                break;

            } else if (header < 0) {
                // got a run
                uint8_t count = 1 - header;

                uint16_t pixel;
                if (isGrayscale) {
                    pixel = ch.grayToColor(p->color(*b++));
                } else {
                    pixel = p->color(*b++);
                }

                while (count) {
                    uint8_t chunk = MIN(count, 8);
                    ASSERT(chunk > 0);

                    switch (chunk) {
                        case 8: drawPixelAtCursor(pixel);
                        case 7: drawPixelAtCursor(pixel);
                        case 6: drawPixelAtCursor(pixel);
                        case 5: drawPixelAtCursor(pixel);
                        case 4: drawPixelAtCursor(pixel);
                        case 3: drawPixelAtCursor(pixel);
                        case 2: drawPixelAtCursor(pixel);
                        case 1: drawPixelAtCursor(pixel);
                        case 0: break;
                    };
                    count -= chunk;
                }

            } else if (header >= 0) {
                // got a segment to copy
                uint8_t count = header + 1;

                while (count) {
                    uint8_t chunk = MIN(count, 8);
                    ASSERT(chunk > 0);

                    if (isGrayscale) {
                        switch (chunk) {
                            case 8: drawPixelAtCursor(ch.grayToColor(p->color(*b++)));
                            case 7: drawPixelAtCursor(ch.grayToColor(p->color(*b++)));
                            case 6: drawPixelAtCursor(ch.grayToColor(p->color(*b++)));
                            case 5: drawPixelAtCursor(ch.grayToColor(p->color(*b++)));
                            case 4: drawPixelAtCursor(ch.grayToColor(p->color(*b++)));
                            case 3: drawPixelAtCursor(ch.grayToColor(p->color(*b++)));
                            case 2: drawPixelAtCursor(ch.grayToColor(p->color(*b++)));
                            case 1: drawPixelAtCursor(ch.grayToColor(p->color(*b++)));
                            case 0: break;
                        };
                    } else {
                        switch (chunk) {
                            case 8: drawPixelAtCursor(p->color(*b++));
                            case 7: drawPixelAtCursor(p->color(*b++));
                            case 6: drawPixelAtCursor(p->color(*b++));
                            case 5: drawPixelAtCursor(p->color(*b++));
                            case 4: drawPixelAtCursor(p->color(*b++));
                            case 3: drawPixelAtCursor(p->color(*b++));
                            case 2: drawPixelAtCursor(p->color(*b++));
                            case 1: drawPixelAtCursor(p->color(*b++));
                            case 0: break;
                        };
                    }
                    count -= chunk;
                }
            }
        }
        break;
    }
}

uint16_t Gfx::write(uint16_t x, uint16_t y, const char *s, const FontAsset & font)
{
    return write(x, y, s, font, NULL, NULL);
}

uint16_t Gfx::write(uint16_t x, uint16_t y, const char *s,  const char *s_end, const FontAsset & font)
{
    return write(x, y, s, s_end, font, NULL, NULL);
}

uint16_t Gfx::write(uint16_t x, uint16_t y, const char *s, const FontAsset & font, uint16_t *color_fg, uint16_t *color_bg)
{
    /*
     * write a string with the given font.
     * if a character doesn't exist in this font, we just skip it for now.
     *
     * XXX: no wrapping support yet
     */

    for (; *s; s++) {
        char c = *s;
        if (font.hasGlyph(c)) {
            drawGlyph(c, x, y, font, color_fg, color_bg);
            x += font.glyph(c).width;
        }
    }

    return x;
}

uint16_t Gfx::write(uint16_t x, uint16_t y, const char *s,  const char *s_end, const FontAsset & font, uint16_t *color_fg, uint16_t *color_bg)
{
    /*
     * write a string with the given font from 's' to 's_end'
     * if a character doesn't exist in this font, we just skip it for now.
     *
     * XXX: no wrapping support yet
     */

    for (; *s; s++) {
        char c = *s;
        if (font.hasGlyph(c)) {
            drawGlyph(c, x, y, font, color_fg, color_bg);
            x += font.glyph(c).width;
        }
        if (s == s_end) {
            return x;
        }
    }

    return x;
}

void Gfx::writeRightJustified(uint16_t x, uint16_t y, unsigned w, const char *s, const FontAsset & font)
{
    unsigned strw = stringWidth(s, font);
    write(x + w - strw, y, s, font);
}

void Gfx::writeCenterJustified(uint16_t x, uint16_t y, unsigned center, const char *s, const FontAsset & font)
{
    // XXX: bounds checking...?
    unsigned xoffset = center - stringWidth(s, font)/2;
    write(x + xoffset, y, s, font);
}

void Gfx::writeCanvasCenterJustified(uint16_t y, const char *s, const FontAsset & font)
{
    writeCanvasCenterJustified(y, s, font, 0, NULL, NULL);
}

void Gfx::writeCanvasCenterJustified(uint16_t y, const char *s, const FontAsset & font, uint16_t *color_fg, uint16_t *color_bg)
{
    writeCanvasCenterJustified(y, s, font, 0, color_fg, color_bg);
}

void Gfx::writeCanvasCenterJustified(uint16_t y, const char *s, const FontAsset & font, uint16_t line_spacing_h)
{
    writeCanvasCenterJustified(y, s, font, line_spacing_h, NULL, NULL);
}

void Gfx::writeCanvasCenterJustified(uint16_t y, const char *s, const FontAsset & font, uint16_t line_spacing_h, uint16_t *color_fg, uint16_t *color_bg)
{
    /*
     * write a single string with delimiting characters on multiple lines
     *
     */

    const char *s_begin = s;
    const char *s_end = s;
    uint16_t y_curr = y;

    // print lines preceding last line (do nothing if there's only one line)
    for (; *s; s++) {
        if (*s == '\n'){            // check if we've reached the end of one line
            if (s != s_begin) {     // don't attempt to print substring if we know it's empty
                s_end = s;
                s_end--;
                // XXX: bounds checking...?
                unsigned x = WIDTH/2 - stringWidth(s_begin, s, font)/2; // width should include beginning of delimiter to match default behavior of stringWidth
                write(x, y_curr, s_begin, s_end, font, color_fg, color_bg);
            }
            y_curr += font.height() + line_spacing_h;

            s++;                    // skip newline char
            s_begin = s;
        }
    }

    // print the last line
    // XXX: bounds checking...?
    unsigned x = WIDTH/2 - stringWidth(s_begin, font)/2;
    write(x, y_curr, s_begin, font, color_fg, color_bg);
}

uint16_t Gfx::writeMonospace(uint16_t x, uint16_t y, const char *s, const FontAsset & font, char box,
                             uint16_t *color_fg, uint16_t *color_bg)
{
    ASSERT(font.hasGlyph(box));

    uint8_t boxW = font.glyph(box).width;

    for (; *s; s++) {
        char c = *s;
        if (font.hasGlyph(c)) {
            // right justify within the box
            uint16_t xoff = x + boxW - font.glyph(c).width;
            drawGlyph(c, xoff, y, font, color_fg, color_bg);
            x += boxW;
        }
    }
    return x;
}

uint16_t Gfx::stringWidth(const char *s, const FontAsset & font)
{
    /*
     * Calculate the width of the string 's' using 'font'.
     */

    uint16_t w = 0;

    for (; *s; s++) {
        char c = *s;
        if (font.hasGlyph(c)) {
            w += font.glyph(c).width;
        }
    }

    return w;
}

uint16_t Gfx::stringWidth(const char *s, const char *s_end, const FontAsset & font)
{
    /*
     * Calculate the width of the string 's' until character at 's_end' using 'font'.
     */

    uint16_t w = 0;

    for (; *s; s++) {
        if (s == s_end) {
            return w;
        }
        char c = *s;
        if (font.hasGlyph(c)) {
            w += font.glyph(c).width;
        }
    }

    return w;
}

void Gfx::FontColorConverter::init(uint16_t color_fg, uint16_t color_bg) {
    R1 = R(color_fg);
    R2 = R(color_bg);
    G1 = G(color_fg);
    G2 = G(color_bg);
    B1 = B(color_fg);
    B2 = B(color_bg);
}

