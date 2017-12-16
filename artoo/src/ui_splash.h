#ifndef UI_SPLASH_H
#define UI_SPLASH_H

#include "button.h"

class UiSplash
{
public:
    UiSplash();

    void init();
    bool update();

private:
    static const unsigned MinSplashMillis = 6000;
    // XXX: better to measure this, and guess based on the last N boots...
    static const unsigned BootEstimateMillis = 18000;

    static const unsigned ProgressBarH = 10;

    bool versionDrawRequested;

    void drawVersion();
};

#endif // UI_SPLASH_H
