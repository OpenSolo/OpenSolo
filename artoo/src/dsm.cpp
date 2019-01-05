#include "dsm.h"
#include "inputs.h"
#include "cameracontrol.h"
#include "flightmanager.h"
#include "tasks.h"
#include "ui.h"
#include "haptic.h"

Dsm Dsm::instance;

void Dsm::init()
{
    for (unsigned i = 0; i < arraysize(channels); ++i) {
        channels[i] = DsmLowVal;
    }

}

void Dsm::onLoiterButtonEvt(Button *b, Button::Event evt)
{
    UNUSED(b);

    // OPEN SOLO MOD: Toggle RC CH7 high and low with the pause button
    // HoldRelease (2 sec) sets CH7 low. LongHold (3 sec) sets CH7 high.
    if ( evt == Button::LongHold ) {
        channels[DsmCh7] = DsmHighVal;
        Ui::instance.pendEvent(Event::CH7high);    
    } else if ( evt == Button::HoldRelease ) {
        channels[DsmCh7] = DsmLowVal;
        Ui::instance.pendEvent(Event::CH7low);
    }
}

void Dsm::producePacket(HostProtocol::Packet &pkt)
{
    pkt.delimitSlip();
    pkt.appendSlip(HostProtocol::DsmChannels);

    // first 4 channels are stick axes
    for (unsigned i = 0; i < 4; ++i) {
        const StickAxis & stick = Inputs::stick(Io::StickID(i));
        channels[i] = stick.angularPPMValue();
#if 0
        // (not used currently) Send partial vehicle control (assisted landing with broken stick for advanced users)
        if (stick.hasValidInput()) {
            channels[i] = stick.angularPPMValue();
        } else {
            channels[i] = stick.angularPPMDefault(); // send default value if stick value is invalid
        }
#endif
    }

    // TODO: vehicle does not have explicit knowledge when receiving this information that the sticks are invalid, app and Artoo do
    const StickAxis & stickGimbalY = Inputs::stick(Io::StickGimbalY);
    if (stickGimbalY.hasInvalidInput()) {
        channels[DsmCh6] = CameraControl::instance.targetPositionDefault();
        channels[DsmCh8] = stickGimbalY.scaledAngularDefault();
    } else {
        channels[DsmCh6] = CameraControl::instance.targetPosition();
        channels[DsmCh8] = stickGimbalY.scaledAngularValue();
    }

    pkt.appendSlip(channels, sizeof(channels));

    pkt.delimitSlip();
}
