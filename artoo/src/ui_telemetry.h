#ifndef UI_TELEMETRY_H
#define UI_TELEMETRY_H

#include "gfx.h"
#include "flightmanager.h"
#include "buttonfunction.h"
#include "ui_bottombox.h"
#include "ui_holdprogressbar.h"

class UiTelemetry
{
public:
    UiTelemetry();

    void init();
    void update();

    void onFlightBatteryChanged() {
        flightBatteryDirty = true;
    }
    inline void onButtonFunctionsChanged() {
        bottomBox.onButtonFunctionsChanged();
    }
    void onAltitudeChanged() {
        altitudeDirty = true;
    }
    void onGpsPositionChanged() {
        distanceDirty = true;
    }
    void onVehicleConnChanged() {
        // do nothing
    }

    void onUnitsChanged(bool unitsAreMetric) {
        if (useMetricUnits != unitsAreMetric) {
            useMetricUnits  = unitsAreMetric;
            unitsDirty = true;
        }
    }

    void onSoloAppConnChanged(bool isConnected);

    bool isSoloAppConnected() const {
        return soloAppConnected;
    }

    static const unsigned RssiMaxBars = 5;
    static unsigned rssiBars(int8_t rssi);

    UiBottomBox bottomBox;

private:
    FlightManager::FlightMode flightMode;

    static const unsigned LeftMargin = 18;

    bool flightBatteryDirty;
    bool altitudeDirty;
    bool distanceDirty;
    int distanceInt;

    // Use imperial or metric units
    bool useMetricUnits;
    bool unitsDirty;

    static const unsigned altitude_x = 22;   // offset params for placing the units in the appropriate location in the UI
    static const unsigned altitude_y = 139;
    static const unsigned distance_x = 292;
    static const unsigned distance_y = 90;
    static const unsigned speed_x = 286;
    static const unsigned speed_y = 139;

    bool soloAppConnected;
    unsigned flyBtnHoldProgress;
    unsigned killSwitchHoldProgress;
    UiHoldProgressBar progressBar;

    void markAllDirty();
    void drawStaticElements();
    void drawUnits();
    void updatePrimaryRegion();
    void updateBottomRegion();
    void updateLandProgress();
    void updateKillSwitchProgress();

    bool autoLandActive() const;
    bool killSwitchActive() const;

    static bool flightBattCritical(const Telemetry & tv);
    static const Gfx::ImageAsset & flightBattLabel(const Telemetry & tv);

    void numericField(uint16_t x, uint16_t y, unsigned v, const Gfx::ImageAsset &p, const Gfx::FontAsset &f);
    void labeledNumericField(unsigned val, uint16_t x, uint16_t y, unsigned space, const char *eraseStr,
                       const Gfx::ImageAsset &lbl, const Gfx::FontAsset &f,
                             uint16_t *fg = NULL, uint16_t *bg = NULL);
};

#endif // UI_TELEMETRY_H
