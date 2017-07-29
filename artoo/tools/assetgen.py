#!/usr/bin/env python
#
# convert assets to binary formats that
# can be understood by firmware
#

import sys, datetime, os, ConfigParser
import itertools
from cStringIO import StringIO
from PIL import Image, ImageFont, ImageDraw

DISPLAY_WIDTH  = 320
DISPLAY_HEIGHT = 240


class Palette:
    ''' our look up table of 16-bit pixel vals '''

    MAX_LUT_SIZE = 256
    ALPHA_KEY = 0x3D3D

    def __init__(self, name):
        self.lut = [self.ALPHA_KEY]
        self.name = name

    def ili9341_pixel(self, p):
        '''
        convert to ili9341 5-6-5 rgb pixel format,
        taking the high-order bits of each 8-bit color channel
        '''
        r, g, b, a = p[0], p[1], p[2], p[3]
        if a == 0:
            return self.ALPHA_KEY
        return (b & 0xf8) << 8 | ((g & 0xfc) << 3) | ((r & 0xf8) >> 3)

    def pix_idx(self, p):
        '''
        return the index in our palette for the given pixel.
        if we don't have an index for this pixel yet, add it to the palette.
        '''
        pixel = self.ili9341_pixel(p)
        if pixel not in self.lut:
            if len(self.lut) == self.MAX_LUT_SIZE:
                raise ValueError("Palette too large - can only support %d entries" % self.MAX_LUT_SIZE)
            self.lut.append(pixel)
        return self.lut.index(pixel) & 0xff

    def write_to(self, cpp, hdr):

        if hdr:
            visibility = "extern"
            hdr.write("extern const Gfx::ImagePalette %s;\n" % self.name)
        else:
            visibility = "static"

        cpp.write("static const uint16_t %s_data[] = {" % self.name)
        for i, p in enumerate(self.lut):
            if i % 10 == 0:
                cpp.write("\n    ")
            cpp.write("0x%04x, " % p)
        cpp.write("\n};\n\n")

        cpp.write("%s const Gfx::ImagePalette %s = {\n" % (visibility, self.name))
        cpp.write("    %s_data,\n" % self.name)
        cpp.write("    %d, // maxIdx\n" % (len(self.lut) - 1))
        cpp.write("};\n\n")


def rle(imgdata, asset_name, palette):
    '''
    run length encode this image.

    each chunk of data is specified by 1-byte header:
        0 to 127:       Copy the next n + 1 symbols verbatim
        -127 to -1:     Repeat the next symbol 1 - n times
        -128:           Do nothing (EOF)
    '''

    MAX_RUN = 128
    EOF = -128
    rle_bytes = []
    single_runs = []

    palette_start_size = len(palette.lut)
    color_set = set()

    # get a list of (count, pixel) tuples
    runs = [(len(list(group)), name) for name, group in itertools.groupby(imgdata)]

    def flush_single_runs():
        rle_bytes.append((len(single_runs) - 1) & 0xff)
        rle_bytes.extend(single_runs)

    for run in runs:

        runlen = run[0]
        runval = palette.pix_idx(run[1]) & 0xff
        color_set.add(runval)

        if runlen == 1:
            single_runs.append(runval)
            if len(single_runs) == MAX_RUN:
                flush_single_runs()
                single_runs = []
        else:
            if len(single_runs) > 0:
                flush_single_runs()
                single_runs = []

            while runlen > 0:
                runsegment = min(MAX_RUN, runlen)
                runlen -= runsegment

                rle_bytes.append((1 - runsegment) & 0xff)
                rle_bytes.append(runval)

    # any left over single runs?
    if len(single_runs) > 0:
        flush_single_runs()

    rle_bytes.append(EOF & 0xff)

    if opt_show_stats:
        palette_diff = len(palette.lut) - palette_start_size
        print "%s - %d colors (%d total, %d new), %d bytes" % (asset_name, len(color_set), len(palette.lut), palette_diff, len(rle_bytes))

    return rle_bytes


def parse_opt_str(opt_str):
    '''
    helper to extract key/val pairs from a string in the form: "key=val, key2=val2, ..."
    '''
    opts = {}

    for opt in opt_str.split(','):
        vals = opt.strip().split('=')
        if len(vals) != 2:
            raise ValueError("bad font option format. must be 'k=v(,)'")
        opts[vals[0]] = vals[1]

    return opts


def convertFont(cfg_path, fontname, font_opts_str, palettes, cpp, hdr):
    """
    process a font file.
    the height for all glyphs is constant, given by the sum
    of ascent and descent provided by font.getmetrics().
    each glyph has its own width.
    """

    opts = parse_opt_str(font_opts_str)

    # fonts with the same bg/color combo share palettes.
    # XXX: could also be better to simply limit the palette size that
    #      pillow uses when generating fonts, but have not taken the
    #      time to figure out how to do that yet...

    fontpath = os.path.join(os.path.dirname(cfg_path), opts['path'])

    font = ImageFont.truetype(fontpath, int(opts['size']))

    start_ch = opts.get('start_ch', ' ')
    end_ch = opts.get('end_ch', 'z')

    color = opts.get('color', "#fff")
    bg = opts.get('bg', "#000")

    color_key = "Palette_%s_%s" % (color.replace("#", ""), bg.replace("#", ""))
    matching_palette = [p for p in palettes if p.name == color_key]
    if matching_palette:
        palette = matching_palette[0]
    else:
        palette = Palette(color_key)
        palettes.append(palette)

    glyphs = map(chr, range(ord(start_ch), ord(end_ch)+1))

    # buffer the array of font glyphs so we don't need to traverse twice
    font_glyphs_str = StringIO()
    font_glyphs_str.write("static const Gfx::GlyphAsset %s_glyphs[] = {" % fontname)

    for g in glyphs:
        w, h = font.getsize(g)
        im = Image.new("RGBA", (w, h))
        draw = ImageDraw.Draw(im)
        draw.rectangle([(0,0), im.size], fill=bg)
        draw.text((0,0), g, font=font, fill=color)

        glyph_name = "%s_glyph_%02x" % (fontname, ord(g))
        cpp.write("static const uint8_t %s_data[] = {" % (glyph_name))
        writeImageBytes(rle(im.getdata(), glyph_name, palette), cpp)
        cpp.write("\n};\n\n")

        font_glyphs_str.write("\n    { %s_data, %d, %d }," % (glyph_name, w, h))

    cpp.write(font_glyphs_str.getvalue())
    cpp.write("\n};\n\n")

    ascent, descent = font.getmetrics()

    hdr.write("extern const Gfx::FontAsset %s;\n" % fontname)
    cpp.write("extern const Gfx::FontAsset %s = {\n" % fontname)
    cpp.write("    %d, // glyphCount\n" % len(glyphs))
    cpp.write("    %d, // ascent\n" % ascent)
    cpp.write("    %d, // descent\n" % descent)
    cpp.write("    Gfx::ImgFmtRle, // format\n")
    cpp.write("    '%c', // start_ch\n" % start_ch)
    cpp.write("    0,  // res0\n")
    cpp.write("    0,  // res1\n")
    cpp.write("    %s_glyphs,\n" % fontname)
    cpp.write("    &%s,\n" % palette.name)
    cpp.write("};\n\n")


def convertFile(imgname, fin, palette, cpp, hdr):

    img = Image.open(fin).convert("RGBA")
    w, h = img.size

    if w > DISPLAY_WIDTH or h > DISPLAY_HEIGHT:
        raise ValueError("error: image size", img.size, "is larger than display")

    hdr.write("extern const Gfx::ImageAsset %s;\n" % imgname)
    cpp.write("static const uint8_t %s_data[] = {" % imgname)

    writeImageBytes(rle(img.getdata(), imgname, palette), cpp)

    cpp.write("\n};\n\n")

    cpp.write("extern const Gfx::ImageAsset %s = {\n" % imgname)
    cpp.write("    %d, // width\n" % w)
    cpp.write("    %d, // height\n" % h)
    cpp.write("    Gfx::ImgFmtRle, // format\n")
    cpp.write("    0, // reserved\n")
    cpp.write("    %s_data,\n" % imgname)
    cpp.write("    &%s,\n" % palette.name)
    cpp.write("};\n\n")


def writeImageBytes(bytes, f):
    for i, b in enumerate(bytes):
        if i % 10 == 0:
            f.write("\n    ")
        f.write("0x%02x, " % b)


def writeWarning(f):
    f.write("/*\n")
    f.write(" * WARNING - this file generated by assetgen.py\n")
    f.write(" *           do not edit, it will be replaced during the next build.\n")
    f.write(" */\n\n")


def checkPilVersion():
    import pkg_resources
    try:
        v = pkg_resources.get_distribution("pillow").version
        maj, min, patch = [int(c) for c in v.split(".")]
        if maj < 2 or (maj == 2 and min < 6):
            print "err: pillow installation is older than 2.6.x, try `pip install --upgrade pillow` to get the latest"
            sys.exit(1)
    except pkg_resources.DistributionNotFound:
        print "pillow is not installed - check ReadMe.md for installation info"
        sys.exit(1)

#
# main
#
# accept search and output dirs on command line,
# scan for PNGs and convert them
#

checkPilVersion()

cfgfile = os.path.join(os.getcwd(), sys.argv[1])
outdir = os.path.join(os.getcwd(), sys.argv[2])

opt_show_stats = '--show-stats' in sys.argv

config = ConfigParser.ConfigParser()
config.optionxform = str    # don't lower case all option names
config.read(cfgfile)

palettes = []

with open(os.path.join(outdir, "resources-gen.h"), "w") as hdrout:

    hdrout.write("#ifndef _RESOURCES_GEN_H\n")
    hdrout.write("#define _RESOURCES_GEN_H\n\n")
    writeWarning(hdrout)
    hdrout.write('#include "gfx.h"\n\n')

    with open(os.path.join(outdir, "resources-gen.cpp"), "w") as cppout:

        cppout.write('#include "ui.h"\n')
        cppout.write('#include "resources-gen.h"\n\n')
        writeWarning(cppout)

        # process image assets
        # there can be multiple asset groups, each of which gets its own palette
        for s in config.sections():
            if s.startswith("Images "):
                pal = Palette(s[len("Images "):])
                palettes.append(pal)
                for name, value in config.items(s):
                    f = os.path.join(os.path.dirname(cfgfile), value)
                    convertFile(name, f, pal, cppout, hdrout)

        # and font assets
        for name, font_opts in config.items('Fonts'):
            convertFont(cfgfile, name, font_opts, palettes, cppout, hdrout)

        for p in palettes:
            if opt_show_stats:
                print "palette: %s - %d colors" % (p.name, len(p.lut))
            p.write_to(cppout, hdrout)

    hdrout.write("\n#endif // _RESOURCES_GEN_H\n")

