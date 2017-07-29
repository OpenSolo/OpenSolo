#include "ui_updater.h"
#include "resources-gen.h"
#include "ui_color.h"

UiUpdater::UiUpdater() :
    updateEvent(Event::None)
{
}

void UiUpdater::init(Event::ID e)
{
    if (updateEvent == e) {
        return;
    }

    updateEvent = e;

    if (updateEvent == Event::SystemUpdateBegin) {
        drawUpdateBegin();

    } else if (updateEvent == Event::SystemUpdateComplete) {
        drawUpdateSuccess();

    } else if (updateEvent == Event::SystemUpdateFail) {
        drawUpdateFailed();
    }
}

bool UiUpdater::update()
{
    if (updateEvent == Event::None) {
        return true;
    }

    return false;
}

bool UiUpdater::onButtonEvent(Button *b, Button::Event e)
{
    /*
     * Dismiss update complete & failed events with a button click,
     * otherwise we leave update begin up indefinitely.
     *
     * Return whether we took action on this event.
     */

    if (updateEvent == Event::SystemUpdateComplete || updateEvent == Event::SystemUpdateFail) {
        if (e == Button::ClickRelease && b->id() == Io::ButtonA) {
            updateEvent = Event::None;
            return true;
        }
    }

    return false;
}

void UiUpdater::drawPrimaryMsg(unsigned y, const char *s1, const char *s2, const Gfx::FontAsset & f, uint16_t color)
{
    /*
     * Helper to draw a centered primary msg with 2 components, one colored and one not.
     */

    unsigned w = Gfx::stringWidth(s1, f) + Gfx::stringWidth(s2, f);
    unsigned x = Gfx::WIDTH/2 - w/2;

    uint16_t color_fg = color;
    uint16_t color_bg = UiColor::Black;

    x = Gfx::write(x, y, s1, f, &color_fg, &color_bg);
    Gfx::write(x, y, s2, f);
}

void UiUpdater::drawUpdateBegin()
{
    Gfx::clear(0x0);

    Gfx::drawImageCanvasHCentered(63, Icon_Wrench);

    const unsigned y = 126;
    drawPrimaryMsg(y, "Updating ", "system", HelveticaNeueLTProLightLarge, UiColor::Green);

    const Gfx::FontAsset & f = HelveticaNeueLTProRoman;
    Gfx::writeCanvasCenterJustified(168, "Update will take about 5 minutes", f);
}

void UiUpdater::drawUpdateSuccess()
{
    Gfx::clear(0x0);

    Gfx::drawImageCanvasHCentered(49, Icon_Check);

    const unsigned y = 126;
    drawPrimaryMsg(y, "Controller ", "updated", HelveticaNeueLTProLightLarge, UiColor::Green);

    const Gfx::FontAsset & f = HelveticaNeueLTProRoman;
    Gfx::writeCanvasCenterJustified(168, "Reconnect app to SoloLink wifi", f);

    promptToContinue();
}

void UiUpdater::drawUpdateFailed()
{
    Gfx::clear(0x0);

    Gfx::drawImageCanvasHCentered(49, Icon_Batsu);

    const unsigned y = 126;
    drawPrimaryMsg(y, "Update ", "failed", HelveticaNeueLTProLightLarge, UiColor::Red);

    const Gfx::FontAsset & f = HelveticaNeueLTProRoman;
    Gfx::writeCanvasCenterJustified(168, "Please try again using the Solo app", f);

    promptToContinue();
}

void UiUpdater::promptToContinue()
{
    // helper to draw common button prompt to continue

    const unsigned secondaryY = 199;
    const Gfx::FontAsset & f = HelveticaNeueLTProRoman;
    const char *msg1 = "Press ", *msg2 = " to continue";
    const Gfx::ImageAsset & img = Icon_New_A_Btn;

    unsigned totalWidth = Gfx::stringWidth(msg1, f) + img.width + Gfx::stringWidth(msg2, f);
    unsigned x = Gfx::WIDTH/2 - totalWidth/2;

    x = Gfx::write(x, secondaryY, msg1, f);
    Gfx::drawImage(x, secondaryY - 6, img);
    x += img.width;
    x = Gfx::write(x, secondaryY, msg2, f);
}
