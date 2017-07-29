#ifndef UIGIMBAL_H
#define UIGIMBAL_H

#include "gfx.h"
#include "stm32/systime.h"

class UiGimbal
{
public:
    UiGimbal();

    void init();
    bool update();

    void onVehicleConnChanged();
    void onShotChanged(const char *shot);

    bool isSuppressed() const {
        return suppressed;
    }

private:
    static const unsigned PRESET_SAVED_SECONDS = 3;

    static const unsigned TiltArcCenterX = 20;
    static const unsigned TiltArcCenterY = 70;

    static const unsigned RightColumnX = 180;

    bool suppressed;

    int angle;
    float preset1;
    float preset2;
    unsigned sweepSeconds;

    SysTime::Ticks presetSavedTimeout;

    bool alertStateDirty;

    void presetSaved(const Gfx::ImageAsset &i);
    void lineEndpoint(float a, unsigned x, unsigned y, unsigned len,
                      unsigned &xout, unsigned &yout);
    void clearAngleMarker(unsigned radius, float a, const Gfx::ImageAsset & img);
    void redrawAngleMarker(unsigned radius, float a, const Gfx::ImageAsset & img);
    void drawCameraAngle(int a, const Gfx::FontAsset & f, const Gfx::ImageAsset & degree);
};

#endif // UIGIMBAL_H
