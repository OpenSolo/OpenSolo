#ifndef UI_TOPBAR_H
#define UI_TOPBAR_H

#include "stm32/common.h"

class UiTopBar
{
public:
    UiTopBar();

    void init();
    void update();

    void onShotChanged(const char * shot);
    void onVehicleConnChanged();
    void onGpsFixChanged() {
        gpsDirty = true;
    }
    void onGpsNumSatsChanged() {
        numSatsDirty = true;
    }
    void onBatteryChanged() {
        batteryDirty = true;
    }
    void onRssiChanged() {
        rssiDirty = true;
    }
    void onChargerChanged() {
        chargerDirty = true;
    }

    const char *currentShotName() const {
        return shotName;
    }

private:
    static const unsigned BATT_DANGER_ZONE_PERCENT = 20;

    static const unsigned Row1Y = 10;
    static const unsigned Row1RightBaseY = 32;
    static const unsigned LeftMargin = 18;
    static const unsigned BattFrameX = 242;
    static const unsigned BattFrameH = 14;
    static const unsigned BattFrameW = 29;

    static const unsigned MAX_SHOT_NAME = 20;
    char shotName[MAX_SHOT_NAME + 1];

    bool shotNameDirty;
    bool gpsDirty;
    bool numSatsDirty;
    bool batteryDirty;
    bool rssiDirty;
    bool chargerDirty;

    void markDirty();
    void drawStaticElements();
    void drawBattFrame();
    void drawShotName();
};

#endif // UI_TOPBAR_H
