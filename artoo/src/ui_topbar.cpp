#include "ui_topbar.h"
#include "battery.h"
#include "ui.h"
#include "resources-gen.h"

#include <stdio.h>

UiTopBar::UiTopBar() :
    shotNameDirty(true),
    gpsDirty(true),
    numSatsDirty(true),
    batteryDirty(true),
    rssiDirty(true),
    chargerDirty(true)
{
}

void UiTopBar::init()
{
    markDirty();
    drawStaticElements();
}

void UiTopBar::markDirty()
{
    /*
     * Mark all update-able elements as requiring an update.
     */

    shotNameDirty = true;
    gpsDirty = true;
    numSatsDirty = true;
    batteryDirty = true;
    rssiDirty = true;
    chargerDirty = true;
}

void UiTopBar::drawStaticElements()
{
    drawBattFrame();
}

void UiTopBar::update()
{
    /*
     * Update any elements that have been marked dirty since our last update.
     */

    const Telemetry & tv = FlightManager::instance.telemVals();

    // ------ battery ------
    if (batteryDirty) {
        batteryDirty = false;

        const unsigned batt = Battery::instance.uiLevel();

        uint16_t x = BattFrameX + 2;
        uint16_t y = Row1RightBaseY - BattFrameH;
        uint16_t h = BattFrameH - 3;

        if (batt <= BATT_DANGER_ZONE_PERCENT) {
            Gfx::fillRect(Gfx::Rect(x, y, 3, h), UiColor::Red);
        } else {
            const unsigned battW = scale(batt, 0U, 100U, 0U, BattFrameW - 4);
            Gfx::fillRect(Gfx::Rect(x, y, battW, h), UiColor::White);
        }
    }

    // ------ num satellites ------
    if (numSatsDirty || gpsDirty) {
        // check gpsDirty to make sure color matches the gps icon
        numSatsDirty = false;

        if (tv.numSatellitesInitialized()) {
            char numbuf[32];
            const Gfx::FontAsset & f = Helvetica16;

            const unsigned x = 33;
            const unsigned y = Row1Y - 2;
            const unsigned eraseW = Gfx::stringWidth("000", f);

            Gfx::fillRect(Gfx::Rect(x, y, eraseW, f.ascent), UiColor::Black);

            sprintf(numbuf, "%d", tv.numSatellites);
            uint16_t fgcolor = tv.hasGpsFix() ? UiColor::Gray : UiColor::Red;
            uint16_t bgcolor = UiColor::Black;
            Gfx::write(x, y, numbuf, f, &fgcolor, &bgcolor);
        }
    }

    // ------ gps ------
    if (gpsDirty) {
        gpsDirty = false;

        const Gfx::ImageAsset & img = tv.hasGpsFix() ? Icon_UD_GPS : Red_Icon_UD_GPS;
        Gfx::drawImage(13, Row1Y, img);

        // XXX: draw number of satellites
    }

    // ------ rssi ------
    if (rssiDirty) {
        rssiDirty = false;

        const unsigned MaxBars = UiTelemetry::RssiMaxBars;

        const unsigned rssiBarBase = 4;
        const unsigned rssiBarW = 3;
        const unsigned rssiBarInc = 3;  // increment from one bar to the next

        const unsigned totalW = (MaxBars * rssiBarW) + (MaxBars - 1);
        const unsigned totalH = rssiBarBase + (MaxBars * rssiBarInc);

        const unsigned rssiX = 289;
        const unsigned rssiY = Row1RightBaseY - totalH;

        Gfx::fillRect(Gfx::Rect(rssiX, rssiY, totalW, totalH), 0x0);

        unsigned bars;
        if (tv.rssiInitialized()) {
            bars = UiTelemetry::rssiBars(tv.rssi);
        } else {
            bars = 0;
        }

        for (unsigned i = 0; i < MaxBars; ++i) {
            Gfx::Rect rect(rssiX + (rssiBarW+1)*i, rssiY + rssiBarInc*(MaxBars-1-i), rssiBarW, rssiBarBase + i*rssiBarInc);

            uint16_t color = (i+1 <= bars) ? UiColor::White : UiColor::DarkGray;
            Gfx::fillRect(rect, color);
        }
    }

    // ------ charger ------
    if (chargerDirty) {
        chargerDirty = false;

        const Gfx::ImageAsset & img = Icon_UD_Bolt;

        const unsigned chgX = 276;
        const unsigned chgY = Row1RightBaseY - img.height;

        if (Battery::instance.chargerIsPresent()) {
            Gfx::drawImage(chgX, chgY, img);
        } else {
            Gfx::fillRect(Gfx::Rect(chgX, chgY, img.width, img.height), 0x0);
        }
    }

    if (shotNameDirty) {
        drawShotName();
        shotNameDirty = false;
    }
}

void UiTopBar::onShotChanged(const char *shot)
{
    if (strncmp(shotName, shot, MAX_SHOT_NAME)) {
        shotNameDirty = true;
        strncpy(shotName, shot, MAX_SHOT_NAME);
        Ui::instance.pendEvent(Event::ShotInfoUpdated);
    }
}

void UiTopBar::onVehicleConnChanged()
{
    // clear the shot name on disconnect
    if (!FlightManager::instance.linkIsConnected()) {
        shotNameDirty = true;
        strcpy(shotName, "");
        Ui::instance.pendEvent(Event::ShotInfoUpdated);
    }
}

void UiTopBar::drawBattFrame()
{
    const uint16_t battFrameColor = UiColor::Gray;

    const unsigned y = Row1RightBaseY - BattFrameH - 2;

    // horizontal
    Gfx::fillRect(Gfx::Rect(BattFrameX, y, BattFrameW, 1), battFrameColor);
    Gfx::fillRect(Gfx::Rect(BattFrameX, y + BattFrameH, BattFrameW, 1), battFrameColor);

    // vertical
    Gfx::fillRect(Gfx::Rect(BattFrameX, y, 1, BattFrameH), battFrameColor);
    Gfx::fillRect(Gfx::Rect(BattFrameX + BattFrameW - 1, y, 1, BattFrameH), battFrameColor);

    // end cap
    Gfx::fillRect(Gfx::Rect(BattFrameX + BattFrameW, y + 3, 3, 8), battFrameColor);
}

void UiTopBar::drawShotName()
{
    const Gfx::FontAsset & f = Helvetica16;
    const unsigned shotFrameY = 5;
    const unsigned shotFrameX = 84;
    const unsigned totalW = (Gfx::WIDTH/2 - shotFrameX) * 2;

    // XXX: would like to draw grey bg here as in spec,
    //      but font color mapping is not currently working for
    //      white on arbitrary bg.
    //      just do white on black for now.

    Gfx::fillRect(Gfx::Rect(shotFrameX, shotFrameY, totalW, 32), UiColor::Black);
    Gfx::writeCanvasCenterJustified(shotFrameY + 10, shotName, f);
}
