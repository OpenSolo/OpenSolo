#include "ui_gimbal.h"
#include "ui.h"
#include "cameracontrol.h"
#include "buttonmanager.h"
#include "params.h"
#include "mathx.h"
#include "resources-gen.h"

#include <stdio.h>

UiGimbal::UiGimbal() :
    suppressed(false),
    angle(0),
    preset1(0),
    preset2(0),
    sweepSeconds(0),
    presetSavedTimeout(0),
    alertStateDirty(false)
{
}

void UiGimbal::init()
{
    const Gfx::FontAsset & f = HelveticaNeueLTProRoman;

    Gfx::clear(0x0);

    Ui::instance.topBar.init();

    // set to invalid values to force redraw
    angle = preset1 = preset2 = -1.0;
    sweepSeconds = -1;

    UiTelemetry & telem = Ui::instance.telem;
    telem.bottomBox.init(UiBottomBox::DisplayGimbal);
    telem.bottomBox.update();

    Gfx::drawImage(TiltArcCenterX, TiltArcCenterY, Tilt_Arc);

    Gfx::write(20, 47, "CAMERA ANGLE", f);
    Gfx::write(RightColumnX, 47, "ANGLE PRESETS", f);
    Gfx::write(RightColumnX, 120, "PRESET SWEEP", f);

    Gfx::drawImage(RightColumnX + 52, 140, Label_SweepSec);

    Gfx::drawImage(RightColumnX, 68, Icon_Angle1Blue_Update);
    Gfx::drawImage(RightColumnX, 91, Icon_Angle2Green_Update);
}

void UiGimbal::onVehicleConnChanged()
{
    /*
     * Called from ui context.
     * Regardless of whether we have disconnected or connected,
     * reset our suppressed state.
     */

    suppressed = false;
}

void UiGimbal::onShotChanged(const char *shot)
{
    /*
     * Hack attack.
     *
     * We receive string names for shots that come down for shot manager.
     * Certain shots disable manual gimbal control, so we must suppress
     * the gimbal ui in those cases. Otherwise, we're showing gimbal UI
     * that does not reflect what's actually happening on the vehicle.
     */

    static const char * const SHOT_TO_SUPPRESS = "FOLLOW";

    suppressed = (strncmp(SHOT_TO_SUPPRESS, shot, strlen(SHOT_TO_SUPPRESS)) == 0);
}

void UiGimbal::presetSaved(const Gfx::ImageAsset &i)
{
    /*
     * a preset has been saved.
     * redraw the hint box with a notification,
     * and set the timer for notification timeout.
     */

    Gfx::fillRect(Gfx::Rect(0, Ui::HintBoxY, Gfx::WIDTH, Gfx::HEIGHT - Ui::HintBoxY), UiColor::Green);

    unsigned x = 81;
    const Gfx::FontAsset & f = HelveticaNeueLTProLightWhiteOnBlack;

    uint16_t color_fg = UiColor::Black;
    uint16_t color_bg = UiColor::Green;
    Gfx::write(x, 204, "PRESET", f, &color_fg, &color_bg);
    x += Gfx::stringWidth("PRESET ", f);

    Gfx::drawImage(x, 201, i);
    x += i.width;

    Gfx::write(x, 204, " SAVED", f, &color_fg, &color_bg);

    presetSavedTimeout = SysTime::now() + SysTime::sTicks(PRESET_SAVED_SECONDS);
}

void UiGimbal::lineEndpoint(float a, unsigned x, unsigned y, unsigned len, unsigned &xout, unsigned &yout)
{
    /*
     * Helper to calculate the endpoint of a line
     * of length 'len' at angle 'a' from the point x/y.
     */

    float r = mathx::radians(90.0 - a);
    xout = x + len * cos(r);
    yout = y + len * sin(r);
}

void UiGimbal::clearAngleMarker(unsigned radius, float a, const Gfx::ImageAsset & img)
{
    unsigned x, y;
    lineEndpoint(a, TiltArcCenterX, TiltArcCenterY, radius, x, y);
    Gfx::fillRect(Gfx::Rect(x - img.width/2, y - img.height/2, img.width, img.height), 0x0);
}

void UiGimbal::redrawAngleMarker(unsigned radius, float a, const Gfx::ImageAsset & img)
{
    // draw new dot
    unsigned x, y;
    lineEndpoint(a, TiltArcCenterX, TiltArcCenterY, radius, x, y);
    Gfx::drawImage(x - img.width/2, y - img.height/2, img);
}

void UiGimbal::drawCameraAngle(int a, const Gfx::FontAsset & f, const Gfx::ImageAsset & degree)
{
    char strbuf[32];
    const unsigned x = TiltArcCenterX;
    const unsigned y = TiltArcCenterY;

    // XXX: grey-out placeholder
    Gfx::fillRect(Gfx::Rect(x, y, Gfx::stringWidth("00", f) + degree.width, f.height()), 0x0);
    sprintf(strbuf, "%02d", a);
    unsigned w = Gfx::stringWidth("00", f);
    Gfx::writeMonospace(x, y, strbuf, f, '0');
    Gfx::drawImage(x + w, y, degree);
}

bool UiGimbal::update()
{
    char strbuf[32];

    bool updated = false;
    bool presetStateChanged = false;

    Ui::instance.topBar.update();
    Ui::instance.telem.bottomBox.update();

    static const unsigned CAMERA_MARKER_RADIUS = 82;
    static const unsigned PRESET_MARKER_RADIUS = 98;

    const Params::StoredValues &sv = Params::sys.storedValues;
    float preset1New = roundf(sv.presets[CameraControl::Preset1].targetPos);
    float preset2New = roundf(sv.presets[CameraControl::Preset2].targetPos);

    //////////////////////////////
    // notification timeout

    if (presetSavedTimeout) {
        if (SysTime::now() > presetSavedTimeout) {
            Ui::instance.telem.bottomBox.onGimbalFunctionsChanged();

            clearAngleMarker(PRESET_MARKER_RADIUS, preset1New, Preset_Marker_SaveBlue);
            redrawAngleMarker(PRESET_MARKER_RADIUS, preset1New, Preset_MarkerBlue);

            clearAngleMarker(PRESET_MARKER_RADIUS, preset2New, Preset_Marker_Save);
            redrawAngleMarker(PRESET_MARKER_RADIUS, preset2New, Preset_Marker);

            presetSavedTimeout = 0;
            presetStateChanged = true;
        }
        updated = true;
    }

    //////////////////////////////
    // preset 1

    if (preset1 != preset1New) {
        if (preset1 >= 0.0) {
            presetSaved(Icon_1_Btn_OnGrn);
            // always clear using the larger marker, so we don't need to track
            // the size of the currently visible marker
            clearAngleMarker(PRESET_MARKER_RADIUS, preset1, Preset_Marker_SaveBlue);
            redrawAngleMarker(PRESET_MARKER_RADIUS, preset1New, Preset_Marker_SaveBlue);
            presetStateChanged = true;
        } else {
            redrawAngleMarker(PRESET_MARKER_RADIUS, preset1New, Preset_MarkerBlue);
        }

        sprintf(strbuf, "%02d", unsigned(preset1New));
        Gfx::writeMonospace(RightColumnX + 52, 70, strbuf, HelveticaNeueLTProRoman, '0');

        preset1 = preset1New;
        updated = true;
    }

    //////////////////////////////
    // preset 2

    if (preset2 != preset2New) {
        if (preset2 >= 0.0) {
            presetSaved(Icon_2_Btn_OnGrn);
            // always clear using the larger marker, so we don't need to track
            // the size of the currently visible marker
            clearAngleMarker(PRESET_MARKER_RADIUS, preset2, Preset_Marker_Save);
            redrawAngleMarker(PRESET_MARKER_RADIUS, preset2New, Preset_Marker_Save);
            presetStateChanged = true;
        } else {
            redrawAngleMarker(PRESET_MARKER_RADIUS, preset2New, Preset_Marker);
        }

        sprintf(strbuf, "%02d", unsigned(preset2New));
        Gfx::writeMonospace(RightColumnX + 52, 91, strbuf, HelveticaNeueLTProRoman, '0');

        preset2 = preset2New;
        updated = true;
    }

    //////////////////////////////
    // camera angle

    int newval = roundf(CameraControl::instance.angle());
    if (presetStateChanged || angle != newval) {

        clearAngleMarker(CAMERA_MARKER_RADIUS, angle, Camera_Angle_Indicator);
        redrawAngleMarker(CAMERA_MARKER_RADIUS, newval, Camera_Angle_Indicator);

        // only draw green on preset-saved. if angle has changed,
        // or preset save timeout has expired, draw white.
        if (angle != newval || presetSavedTimeout == 0) {
            drawCameraAngle(newval, Copenhagen40, Degree40White);
        } else {
            drawCameraAngle(newval, Copenhagen40Green, Degree40Green);
        }

        angle = newval;
        updated = true;
    }

    //////////////////////////////
    // preset sweep time

    unsigned seconds = CameraControl::instance.smoothedPresetSweepSeconds();
    if (sweepSeconds != seconds) {
        sweepSeconds = seconds;

        const unsigned x = RightColumnX;
        const unsigned y = 140;

        // XXX: grey-out placeholder
        const Gfx::FontAsset & f = Copenhagen40;
        Gfx::fillRect(Gfx::Rect(x, y, Gfx::stringWidth("00", f), f.height()), 0x0);
        sprintf(strbuf, "%02d", sweepSeconds);
        Gfx::writeMonospace(x, y, strbuf, f, '0');

        updated = true;
    }

    // if either preset button is being held, keep view alive
    if (ButtonManager::button(Io::ButtonPreset1).isPressed() ||
        ButtonManager::button(Io::ButtonPreset2).isPressed()) {
        updated = true;
    }

    return updated;
}
