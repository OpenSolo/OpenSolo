#include "ui_holdprogressbar.h"
#include "ui.h"
#include "gfx.h"
#include "resources-gen.h"

const unsigned UiHoldProgressBar::Height = Hold_PBarCap.height;

UiHoldProgressBar::UiHoldProgressBar(unsigned y, unsigned marginY, uint16_t color) :
    yCoord(y),
    yMargin(marginY),
    colorBar(color)
{
}

void UiHoldProgressBar::clear()
{
    Gfx::fillRect(Gfx::Rect(0, yCoord, Gfx::WIDTH, Height + yMargin*2), UiColor::Black);
}

void UiHoldProgressBar::update(unsigned w)
{
    update(w, colorBar);
}

void UiHoldProgressBar::update(unsigned w, uint16_t color)
{
    STATIC_ASSERT(Hold_PBarCap.height == Kill_PBarCap.height);

    const unsigned y = yCoord + yMargin;
    const unsigned x = MAX(w, 1);

    Gfx::fillRect(Gfx::Rect(0, y, w, Hold_PBarCap.height), color);

    // XXX: hack attack
    //      we don't have clipping support yet, so once the end cap has reached the edge,
    //      fill the rect over it. otherwise, the image draw results in artifacts as
    //      it wraps back around the edge of the visible region.
    if (w > Gfx::WIDTH - Hold_PBarCap.width) {
        return;
    }

    if (color == UiColor::Green) {
        Gfx::drawImage(x, y, Hold_PBarCap);
    } else if (color == UiColor::Red) {
        Gfx::drawImage(x, y, Kill_PBarCap);
    }
}
