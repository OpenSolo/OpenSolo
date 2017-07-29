#include "ui_pairing.h"
#include "ui.h"
#include "vehicleconnector.h"
#include "resources-gen.h"

#include <stdio.h>

UiPairing::UiPairing() :
    event(Event::None),
    msgTimeout(0)
{
}

void UiPairing::init()
{
    Gfx::clear(0x0);
    msgTimeout = 0;
    event = Event::None;

    drawPairing();
}

bool UiPairing::update()
{
    if (event != Event::None) {
        switch (event) {
        case Event::PairingInProgress:
            drawInProgress();
            break;

        case Event::PairingSucceeded:
            drawSuccess();
            break;

        case Event::PairingCanceled:
            drawCanceled();
            break;

        case Event::PairingIncomplete:
            drawIncomplete();
            break;

        default:
            break;
        }

        event = Event::None;
        msgTimeout = SysTime::now() + SysTime::sTicks(5);
    }

    if (msgTimeout && SysTime::now() > msgTimeout) {
        return true;
    }

    return false;
}

void UiPairing::drawPairing()
{
    Gfx::clear(0x0);

    Gfx::drawImageCanvasHCentered(55, Icon_SoloWhite);
    //Ui::writePrimaryMsg("detected ", HelveticaNeueLTProLightGreen, "new Solo", HelveticaNeueLTProLight);
    uint16_t color_fg = UiColor::Green;
    uint16_t color_bg = UiColor::Black;
    Ui::writePrimaryMsg("detected ", "new Solo", HelveticaNeueLTProLightLargeWhiteOnBlack, &color_fg, &color_bg);

    const Gfx::FontAsset & f = HelveticaNeueLTProRoman;

    const unsigned secondaryY = 199;
    unsigned x = 22;
    x = Gfx::write(x, secondaryY, "Hold ", f);
    Gfx::drawImage(x, secondaryY - 6, Icon_New_A_Btn);
    x += Icon_New_A_Btn.width;
    x = Gfx::write(x, secondaryY, " + ", f);
    Gfx::drawImage(x, secondaryY - 6, Icon_New_B_Btn);
    x += Icon_New_B_Btn.width;
    Gfx::write(x, secondaryY, " to pair", f);

    x = 205;
    Gfx::drawImage(x, secondaryY - 6, Icon_New_B_Btn);
    x += Icon_New_B_Btn.width;
    Gfx::write(x, secondaryY, " to cancel", f);
}

void UiPairing::drawInProgress()
{
    Gfx::clear(0x0);

    Gfx::drawImageCanvasHCentered(55, Icon_SoloWhite);
    //Ui::writePrimaryMsg("pairing ", HelveticaNeueLTProLightGreen, "in progress", HelveticaNeueLTProLight);
    uint16_t color_fg = UiColor::Green;
    uint16_t color_bg = UiColor::Black;
    Ui::writePrimaryMsg("pairing ", "in progress", HelveticaNeueLTProLightLargeWhiteOnBlack, &color_fg, &color_bg);
}

void UiPairing::drawSuccess()
{
    Gfx::clear(0x0);

    Gfx::drawImageCanvasHCentered(55, Icon_SoloGreen);
    //Ui::writePrimaryMsg("Solo ", HelveticaNeueLTProLightGreen, "paired", HelveticaNeueLTProLight);
    uint16_t color_fg = UiColor::Green;
    uint16_t color_bg = UiColor::Black;
    Ui::writePrimaryMsg("Solo ", "paired", HelveticaNeueLTProLightLargeWhiteOnBlack, &color_fg, &color_bg);
}

void UiPairing::drawCanceled()
{
    Gfx::clear(0x0);

    Gfx::drawImageCanvasHCentered(55, Icon_SoloWhite);
    //Ui::writePrimaryMsg("pairing ", HelveticaNeueLTProLightGreen, "canceled", HelveticaNeueLTProLight);
    uint16_t color_fg = UiColor::Green;
    uint16_t color_bg = UiColor::Black;
    Ui::writePrimaryMsg("pairing ", "canceled", HelveticaNeueLTProLightLargeWhiteOnBlack, &color_fg, &color_bg);
}

void UiPairing::drawIncomplete()
{
    Gfx::clear(0x0);

    Gfx::drawImageCanvasHCentered(55, Icon_SoloWhite);
    //Ui::writePrimaryMsg("pairing ", HelveticaNeueLTProLightRed, "unsuccessful", HelveticaNeueLTProLight);
    uint16_t color_fg = UiColor::Red;
    uint16_t color_bg = UiColor::Black;
    Ui::writePrimaryMsg("pairing ", "unsuccessful", HelveticaNeueLTProLightLargeWhiteOnBlack, &color_fg, &color_bg);


    const unsigned secondaryY = 168;
    const Gfx::FontAsset & f = HelveticaNeueLTProRoman;
    Gfx::writeCanvasCenterJustified(secondaryY, "Press pair button on Solo to try again", f);
}
