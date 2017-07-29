#include "ui_telemetry.h"
#include "ui.h"
#include "flightmanager.h"
#include "powermanager.h"
#include "buttonmanager.h"
#include "battery.h"
#include "buttonfunction.h"
#include "mathx.h"
#include "resources-gen.h"
#include "stm32/common.h"

#include <stdio.h>

UiTelemetry::UiTelemetry() :
    bottomBox(),
    flightMode(FlightManager::STABILIZE),
    flightBatteryDirty(true),
    altitudeDirty(true),
    distanceDirty(true),
    distanceInt(-1),
    useMetricUnits(true),
    unitsDirty(true),
    soloAppConnected(false),
    flyBtnHoldProgress(0),
    killSwitchHoldProgress(0),
    progressBar(Ui::HintBoxY + Ui::HintBoxBorderWeight)
{
}

void UiTelemetry::markAllDirty()
{
    /*
     * helper to mark all ui elements as dirty.
     * handy to force redraw of all elements on init.
     */

    // arbitrary invalid value to force redraw
    flightMode = static_cast<FlightManager::FlightMode>(-1);
    distanceInt = -1;

    altitudeDirty = true;
    distanceDirty = true;
    unitsDirty = true;
    flightBatteryDirty = true;
}

void UiTelemetry::init()
{
    /*
     * Draw all the static elements of the standard telemetry view.
     */

    markAllDirty();

    Gfx::clear(0x00);

    Ui::instance.topBar.init();
    bottomBox.init(UiBottomBox::DisplayTelem);

    drawStaticElements();
    update();
}

void UiTelemetry::update()
{
    /*
     * Update the dynamic elements of the telemetry view.
     */

    Ui::instance.topBar.update();
    updatePrimaryRegion();
    updateBottomRegion();
}

void UiTelemetry::updatePrimaryRegion()
{
    /*
     * Update the elements that are in the primary viewing region,
     * specifically things that are neither in top or bottom bars.
     */

    const Telemetry & tv = FlightManager::instance.telemVals();

    const Gfx::FontAsset & altFont = Copenhagen40;
    const Gfx::FontAsset & distFont = Copenhagen40;
    const Gfx::FontAsset & flightBattFont = Copenhagen85;

    if (autoLandActive() || killSwitchActive()) {
        return;
    }

    // altitude
    if (unitsDirty || altitudeDirty) {
        float a = useMetricUnits ? tv.altitude : mathx::metersToFeet(tv.altitude);
        unsigned alt = MIN(999, roundf(a));

        const Gfx::ImageAsset & unit = useMetricUnits ? Unit_UD_Meter : Unit_UD_Feet;
        labeledNumericField(alt, 190, 129, 3, "000", unit, altFont);

        altitudeDirty = false;
    }

    if (distanceDirty || unitsDirty) {
        float dist = roundf(FlightManager::instance.distanceFromTakeoff());
        int d = useMetricUnits ? int(dist) : mathx::metersToFeet(dist);

        if (distanceInt != d || unitsDirty) {
            distanceInt = d;

            const Gfx::ImageAsset & unit = useMetricUnits ? Unit_UD_Meter : Unit_UD_Feet;
            labeledNumericField(distanceInt, 190, 70, 3, "0000", unit, distFont);
        }
        distanceDirty = false;
    }

    if (flightBatteryDirty) {
        flightBatteryDirty = false;

        Gfx::drawImage(15, 54, flightBattLabel(tv));

        const Gfx::ImageAsset & pct = flightBattCritical(tv) ? Unit_UD_Red_Percent : Unit_UD_Percent;

        uint16_t fg = flightBattCritical(tv) ? UiColor::Red : UiColor::White;
        uint16_t bg = UiColor::Black;

        labeledNumericField(tv.flightBatteryDisplay(), 15, 70, 4, "000", pct, flightBattFont, &fg, &bg);
    }

    // this is checked in each of the fields above
    unitsDirty = false;
}

bool UiTelemetry::flightBattCritical(const Telemetry & tv)
{
    return (tv.flightBatteryInitialized() && tv.flightBatteryDisplay() < FlightManager::instance.BatteryLevelCritical);
}

const Gfx::ImageAsset & UiTelemetry::flightBattLabel(const Telemetry & tv)
{
    if (flightBattCritical(tv)) {
        return Red_Label_UD_FlightBatt;
    }

    return Label_UD_FlightBatt;
}

void UiTelemetry::updateBottomRegion()
{
    /*
     * In the bottom region, we'll either show a progress bar
     * towards an auto land event, progress bar towards kill switch event,
     * or the standard button/alerts via bottomBox.
     *
     * kill switch not yet implemented.
     */

    // kill switch is highest priority
    if (killSwitchActive()) {
        updateKillSwitchProgress();
        return;
    }

    if (autoLandActive()) {
        updateLandProgress();
        return;
    }

    // need to clean up from previous progress bar drawing?
    bool reinitDefaultView = false;

    if (killSwitchHoldProgress) {
        killSwitchHoldProgress = 0;
        reinitDefaultView = true;
    }

    if (flyBtnHoldProgress) {
        flyBtnHoldProgress = 0;
        reinitDefaultView = true;
    }

    // auto land or kill switch are not active,
    // if it just transitioned to not active, reinit the primary view
    if (flyBtnHoldProgress == 0 || killSwitchHoldProgress == 0) {
        if (reinitDefaultView) {
            init();
        }
        bottomBox.update();
    }
}

void UiTelemetry::updateLandProgress()
{
    /*
     * If the FLY button is being held while in flight,
     * it will trigger a change to AutoLand.
     *
     * Show progress on that button hold and return whether we drew anything.
     */

    const Button & b = ButtonManager::button(Io::ButtonFly);

    if (!b.isHeldShort() || b.isHeld()) {
        // only want to draw progress up until the hold event
        return;
    }

    unsigned millis = MIN(b.pressDuration() / SysTime::msTicks(1), Button::HoldMillis);
    unsigned prog = scale(millis, 0U, Button::HoldMillis, 0U, Gfx::WIDTH);

    if (flyBtnHoldProgress == 0) {
        Gfx::fillRect(Gfx::Rect(0, 42, Gfx::WIDTH, Ui::HintBoxY), UiColor::Black);
        Ui::writeFlyBtnInstructions("Hold ", " to land");

        progressBar.clear();
    }

    if (flyBtnHoldProgress != prog) {
        flyBtnHoldProgress  = prog;
        progressBar.update(flyBtnHoldProgress);
    }
}

void UiTelemetry::updateKillSwitchProgress()
{
    /*
     * If the FLY button is being held while in flight,
     * it will trigger a change to AutoLand.
     *
     * Show progress on that button hold and return whether we drew anything.
     */

    const Button & a = ButtonManager::button(Io::ButtonA);
    const Button & b = ButtonManager::button(Io::ButtonB);
    const Button & loiter = ButtonManager::button(Io::ButtonLoiter);

    if (a.isHeld() || b.isHeld() || loiter.isHeld()) {
        // only want to draw progress up until the hold event
        return;
    }

    // use one of the buttons to calculate hold time since it will be the same for all buttons held
    unsigned millis = MIN(a.pressDuration() / SysTime::msTicks(1), Button::HoldMillis);
    unsigned prog = scale(millis, 0U, Button::HoldMillis, 0U, Gfx::WIDTH);

    if (killSwitchHoldProgress == 0) {
        Gfx::fillRect(Gfx::Rect(0, 42, Gfx::WIDTH, Ui::HintBoxY), UiColor::Black);
        Ui::writeKillSwitchInstructions("To shut off motors", "hold ");

        progressBar.clear();
    }

    if (killSwitchHoldProgress != prog) {
        killSwitchHoldProgress  = prog;
        progressBar.update(killSwitchHoldProgress, UiColor::Red);
    }
}

void UiTelemetry::drawStaticElements()
{
    Gfx::drawImage(190, 54, Label_UD_Home);
    Gfx::drawImage(190, 114, Label_UD_Alt);
}

bool UiTelemetry::autoLandActive() const
{
    /*
     * Are we currently displaying the auto-land progress bar?
     * Used to determine which parts of the view need updating.
     */

    return ButtonManager::button(Io::ButtonFly).isPressed();
}

bool UiTelemetry::killSwitchActive() const
{
    /*
     * Are we currently displaying the kill-switch progress bar?
     * Used to determine which parts of the view need updating.
     */
    const Button & a = ButtonManager::button(Io::ButtonA);
    const Button & b = ButtonManager::button(Io::ButtonB);
    const Button & loiter = ButtonManager::button(Io::ButtonLoiter);

    return a.isPressed() && b.isPressed() && loiter.isPressed();
}

void UiTelemetry::numericField(uint16_t x, uint16_t y, unsigned v, const Gfx::ImageAsset &p, const Gfx::FontAsset &f)
{
    /*
     * Render a numeric field, with greyed out placeholders
     * for the leading 0 digits.
     */

    static const unsigned NUMERIC_FIELD_NUM_DIGITS = 3;

    char numbuf[32];
    sprintf(numbuf, "%d", v);
    unsigned digits = strlen(numbuf);
    if (digits > NUMERIC_FIELD_NUM_DIGITS) {
        digits = NUMERIC_FIELD_NUM_DIGITS;
    }

    Gfx::fillRect(Gfx::Rect(x, y, p.width * NUMERIC_FIELD_NUM_DIGITS, p.height), 0x0);

    unsigned placeholderCount = NUMERIC_FIELD_NUM_DIGITS - digits;
    for (unsigned i = 0; i < placeholderCount; ++i) {
        Gfx::drawImage(x, y, p);
        x += p.width;
    }

    Gfx::write(x, y, numbuf, f);
}

void UiTelemetry::labeledNumericField(unsigned val, uint16_t x, uint16_t y, unsigned space,
                                      const char *eraseStr,
                                      const Gfx::ImageAsset &lbl, const Gfx::FontAsset &f,
                                      uint16_t *fg, uint16_t *bg)
{
    /*
     * Clear and redraw a numeric field, along with the given label.
     */

    char numbuf[32];
    sprintf(numbuf, "%d", val);
    const unsigned eraseW = Gfx::stringWidth(eraseStr, f) + lbl.width + space;
    Gfx::fillRect(Gfx::Rect(x, y, eraseW, f.height()), UiColor::Black);
    x = Gfx::writeMonospace(x, y, numbuf, f, '0', fg, bg);

    Gfx::drawImage(x + space, y + f.ascent - lbl.height, lbl);
}

void UiTelemetry::onSoloAppConnChanged(bool isConnected) {
    soloAppConnected = isConnected;
    if (soloAppConnected) {
        Ui::instance.pendEvent(Event::SoloAppConnected);
    } else {
        Ui::instance.pendEvent(Event::SoloAppDisconnected);
    }
}

unsigned UiTelemetry::rssiBars(int8_t rssi)
{
    /*
     * Translate a raw rssi value into the number of bars
     * we'd like to represent it with.
     *
     * Should be consistent with
     * github.com/3drobotics/iSolo/blob/master/iSolo/UI/TelemetryBarVC.swift
     */

    if (rssi < -75) { return 0; }
    if (rssi < -70) { return 1; }
    if (rssi < -65) { return 2; }
    if (rssi < -60) { return 3; }
    if (rssi < -50) { return 4; }

    return RssiMaxBars;
}
