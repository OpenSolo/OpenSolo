#ifndef _UI_HOLD_PROGRESS_BAR_H
#define _UI_HOLD_PROGRESS_BAR_H

#include "ui_color.h"

class UiHoldProgressBar
{
public:
    UiHoldProgressBar(unsigned y, unsigned marginY = 7, uint16_t color = UiColor::Green); // default green

    static const unsigned Height;   // driven by end cap asset

    void clear();
    void update(unsigned w);
    void update(unsigned w, uint16_t color); // draw with custom color

private:
    const unsigned yCoord;
    const unsigned yMargin;
    const uint16_t colorBar;
};

#endif // _UI_HOLD_PROGRESS_BAR_H
