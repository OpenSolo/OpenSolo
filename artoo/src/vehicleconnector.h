#ifndef VEHICLE_CONNECTOR_H
#define VEHICLE_CONNECTOR_H

#include "hostprotocol.h"
#include "button.h"

/*
 * VehicleConnector is responsible for managing the pairing
 * process between Artoo and a vehicle.
 */

class VehicleConnector
{
public:
    enum State {
        Idle,
        RequestReceived,
        ConfirmationReceived,
        ConfirmationSent,
    };

    VehicleConnector();

    static VehicleConnector instance;

    static const unsigned MAX_ID_LEN = 32;  // not sure what is driving this yet

    bool producePacket(HostProtocol::Packet &p);

    // called by hostprotocol
    void onPairingRequest(const uint8_t *payload, unsigned len);
    void onPairingResult(const uint8_t *payload, unsigned len);

    // called by buttonmanager
    void onButtonEvent(Button *b, Button::Event evt);

    State state() const {
        return _state;
    }

    const char *pairingId() const {
        return deviceID;
    }

private:
    State _state;
    char deviceID[MAX_ID_LEN];
};

#endif // VEHICLE_CONNECTOR_H
