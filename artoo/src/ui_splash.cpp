#include "ui_splash.h"
#include "ui.h"
#include "hostprotocol.h"
#include "version.h"
#include "resources-gen.h"

#include "stm32/systime.h"

UiSplash::UiSplash() :
    versionDrawRequested(false)
{
}

void UiSplash::init()
{
    Gfx::clear(0x00);

    uint16_t y = Gfx::HEIGHT/2 - Icon_Solo_Startup_Logo.height/2;
    Gfx::drawImageCanvasHCentered(y, Icon_Solo_Startup_Logo);
}

bool UiSplash::update()
{
    /*
     * Draw an estimate of our boot progress.
     */

    unsigned millis = (SysTime::now() - Ui::instance.stateStartTime()) / SysTime::msTicks(1);
    if (millis >= BootEstimateMillis) {
        return true;
    }

    // it's possible to boot directly in the event
    // that we received a host msg while we were sleeping.
    // still want to show some splash screen in that case.
    if (HostProtocol::instance.connected()) {
        if (millis >= MinSplashMillis) {
            return true;
        }
    }

    drawVersion();

    uint16_t w = scale(millis, 0U, BootEstimateMillis, 0U, Gfx::WIDTH);
    Gfx::fillRect(Gfx::Rect(0, Gfx::HEIGHT - ProgressBarH, w, ProgressBarH), UiColor::Green);

    return false;
}

void UiSplash::drawVersion()
{
    const Gfx::FontAsset & f = HelveticaNeueLTProRoman;
    unsigned w = Gfx::stringWidth(Version::str(), f);
    uint16_t x = Gfx::WIDTH - w - 12;
    uint16_t y = Gfx::HEIGHT - f.height() - ProgressBarH - 2;
    Gfx::write(x, y, Version::str(), f);
}
