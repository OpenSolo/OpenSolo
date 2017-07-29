#include "ui_power.h"
#include "battery.h"
#include "powermanager.h"
#include "ui.h"
#include "ili9341parallel.h"
#include "resources-gen.h"

UiPower::UiPower() :
    reportedLifeAfterDeath(false),
    spinnerFrame(0)
{}

bool UiPower::updateShutdown()
{
    drawSpinner();

    SysTime::Ticks t = SysTime::now() - Ui::instance.stateStartTime();
    if (t > SysTime::sTicks(IMX6_SHUTDOWN_SECONDS) && PowerManager::rcIsDischarged()) {
        // XXX: possibly fade out here in the future
        PowerManager::onShutdownSequenceComplete();
        return true;
    }

    return false;
}

void UiPower::drawSpinner()
{
    /*
     * Animate a progress spinner during shutdown.
     *
     * We don't have explicit support for animations,
     * so we implement it here one off. If there are
     * many more instances in which we want to do this,
     * may want to provide better support for it.
     */

    const Gfx::ImageAsset * const frames[] = {
        &Spinner00,
        &Spinner01,
        &Spinner02,
        &Spinner03,
        &Spinner04,
        &Spinner05,
        &Spinner06,
        &Spinner07,
        &Spinner08,
        &Spinner09,
        &Spinner10,
        &Spinner11,
        &Spinner12,
        &Spinner13,
        &Spinner14,
        &Spinner15,
        &Spinner16,
        &Spinner17,
        &Spinner18,
    };

    // XXX: these must all be the same size, so just use the
    //      first frame for size/coord calculations.
    static const Gfx::ImageAsset & img = *frames[0];
    static const unsigned x = Gfx::WIDTH/2 - img.width/2;
    static const unsigned y = Gfx::HEIGHT - img.height - 40;

    Gfx::fillRect(Gfx::Rect(x, y, img.width, img.height), UiColor::Black);
    Gfx::drawImage(x, y, *frames[spinnerFrame]);

    spinnerFrame = (spinnerFrame + 1) % arraysize(frames);
}

void UiPower::drawBatteryCheck()
{
    drawBattery();

    // power on prompt
    const Gfx::FontAsset &f = Helvetica16;
    const Gfx::ImageAsset &img = Icon_Power_Btn;
    const uint16_t msgY = 156;

    const char *msgPt1 = "HOLD ";
    const char *msgPt2 = " TO POWER ON";

    unsigned w1 = Gfx::stringWidth(msgPt1, f);
    unsigned w2 = Gfx::stringWidth(msgPt2, f);
    unsigned totalw = w1 + img.width + w2;

    unsigned msgX = Gfx::WIDTH/2 - totalw/2;

    Gfx::write(msgX, msgY, msgPt1, f);
    msgX += w1;
    Gfx::drawImage(msgX, 155, img);
    msgX += img.width;
    Gfx::write(msgX, msgY, msgPt2, f);
}

void UiPower::drawChargerConnected()
{
    drawBattery();

    const Gfx::FontAsset &f = Helvetica16;
    Gfx::writeCanvasCenterJustified(156, "CHARGER CONNECTED", f);
}

void UiPower::drawBatteryTooLowToStart()
{
    /*
     * Called during startup if battery is too low
     * to fire up the rest of the system. Assume this will
     * just draw the red end cap, no text needed.
     */

    drawBattery();
}

void UiPower::initShutdown()
{
    Gfx::clear(0x0);
    ILI9341Parallel::lcd.setBacklight(30);

    reportedLifeAfterDeath = false;

    uint16_t y = Gfx::HEIGHT/2 - Icon_Solo_Startup_Logo.height/2;
    Gfx::drawImageCanvasHCentered(y, Icon_Solo_Startup_Logo);
}

void UiPower::drawBattery()
{
    /*
     * called when the system is started up in battery check mode.
     * we just pop up the current battery level, with instructions
     * on how to fully boot the system.
     */

    Gfx::clear(0x00);

    uint16_t y = 82;
    const uint16_t x = Gfx::drawImageCanvasHCentered(y, Battery_Frame) + 5;

    y += 5;

    const unsigned w = Battery::instance.uiLevel();
    // NB: battery is already scaled 0-100, and the max width of the battery
    //     display is 0-100 (including end caps). if this changes, must
    //     update this to scale battLevel accordingly.

    if (w <= Battery::CRITICALLY_LOW_PERCENT) {
        Gfx::drawImage(x, y, Battery_Left_RedCap);

    } else {
        Gfx::drawImage(x, y, Battery_Left_GreenCap);

        const unsigned ecW = Battery_Left_GreenCap.width;
        if (w > ecW) {
            const unsigned battW = MIN(w, 100U - ecW);
            Gfx::fillRect(Gfx::Rect(x + ecW, y, battW, Battery_Left_GreenCap.height), UiColor::Green);
        }

        if (w >= 100U - ecW) {
            Gfx::drawImage(x + 100 - ecW, y, Battery_Right_GreenCap);
        }
    }
}
