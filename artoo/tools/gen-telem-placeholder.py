#!/usr/bin/env python

import sys, os
from PIL import Image, ImageFont, ImageDraw

def genPlaceholder(fontpath, fontsize, fontfill):
    '''
    generate a placeholder glyph for the telem view.
    we generate a single glyph so that we don't need to store
    an entire font.
    '''

    glyph = '0'

    font = ImageFont.truetype(fontpath, fontsize)
    w, h = font.getsize(glyph)

    im = Image.new("RGB", (w, h))
    ImageDraw.Draw(im).text((0,0), glyph, font=font, fill=fontfill)
    path = "telem-placeholder-digit-%d.png" % fontsize
    im.save(path, "PNG")
    print "wrote placeholder image to", path


#
# main
#
# usage:
#   python tools/gen-placeholder.py resources/fonts/Copenhagen_Light.otf 88 "#555656"
#

fontpath = os.path.join(os.getcwd(), sys.argv[1])
fontsize = int(sys.argv[2])
fontfill = sys.argv[3]

genPlaceholder(fontpath, fontsize, fontfill)