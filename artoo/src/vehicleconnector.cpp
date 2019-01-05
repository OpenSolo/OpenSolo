#include "vehicleconnector.h"
#include "buttonmanager.h"
#include "haptic.h"
#include "ui.h"

#include "stm32/systime.h"

VehicleConnector VehicleConnector::instance;

VehicleConnector::VehicleConnector() :
    _state(Idle)
{
}

bool VehicleConnector::producePacket(HostProtocol::Packet &p)
{
    if (_state == ConfirmationReceived) {
        p.delimitSlip();
        p.appendSlip(HostProtocol::PairConfirm);
        // include null terminated device id
        p.appendSlip(deviceID, strlen(deviceID) + 1);
        p.delimitSlip();
        _state = ConfirmationSent;
        return true;
    }

    return false;
}

void VehicleConnector::onPairingRequest(const uint8_t *payload, unsigned len)
{
    /*
     * A pairing request has arrived.
     *
     * Take note of the device requesting the pairing,
     * and kick off the pairing process.
     *
     * we expect 'len' includes null terminator.
     */

    const unsigned idsz = sizeof deviceID;
    strncpy(deviceID, (const char*)payload, idsz);

    // ensure we're null terminated
    if (len >= idsz) {
        deviceID[idsz - 1] = '\0';
    }

    _state = RequestReceived;
    Ui::instance.pendEvent(Event::PairingRequest);
}

void VehicleConnector::onPairingResult(const uint8_t *payload, unsigned len)
{
    /*
     * The final step in the pairing sequence, emit ui-related events here.
     *
     * PairingResult with same name means pairing worked
     * PairingResult with name "" means pairing failed.
     *
     * we expect 'len' includes null terminator.
     */

    if (len > 1 && strncmp(deviceID, (const char*)payload, sizeof deviceID) == 0) {
        Ui::instance.pendEvent(Event::PairingSucceeded);

    } else {
        // name didn't match or was empty.
        // indicates timeout either because user didn't respond,
        // or because pairing failed to complete in the allotted time
        if (strlen(deviceID) > 0) {
            Ui::instance.pendEvent(Event::PairingIncomplete);
        } else {
            Ui::instance.pendEvent(Event::PairingCanceled);
        }
    }

    strcpy(deviceID, "");
    _state = Idle;
}

void VehicleConnector::onButtonEvent(Button *b, Button::Event evt)
{
    /*
     * If both A and B buttons have long hold events,
     * we confirm an outstanding pairing request.
     *
     * A click on the B button cancels.
     */

    if (_state != RequestReceived) {
        return;
    }

    if (b->id() == Io::ButtonB && evt == Button::ClickRelease) {
        _state = ConfirmationReceived;
        strcpy(deviceID, "");
        HostProtocol::instance.requestTransaction();
        return;
    }

    if (ButtonManager::button(Io::ButtonA).isHeldLong() &&
        ButtonManager::button(Io::ButtonB).isHeldLong())
    {
        _state = ConfirmationReceived;
        Ui::instance.pendEvent(Event::PairingInProgress);
        Haptic::startPattern(Haptic::SingleMedium);
        HostProtocol::instance.requestTransaction();
    }
}
