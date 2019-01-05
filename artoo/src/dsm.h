#ifndef DSM_H
#define DSM_H

#include "button.h"
#include "hostprotocol.h"

/*
 * SPKT/DSM channels are used to send values between
 * dsmLowVal and dsmHighVal to pixhawk.
 *
 * The semantics of each channel are configured via GCS software.
 *
 * The first 4 channels are thro/roll/pitch/yaw.
 * Currently, we send flight mode on channel 5, and the
 * A and B buttons on channels 6 and 7.
 */

class Dsm
{
public:
    Dsm() {}

    static Dsm instance;

    void init();
    void onLoiterButtonEvt(Button *b, Button::Event evt);

    void producePacket(HostProtocol::Packet &pkt);

private:

    static const unsigned CHANNEL_COUNT = 8;

    static const unsigned DsmLowVal = 1000;
    static const unsigned DsmMidVal = 1500;
    static const unsigned DsmHighVal = 2000;

    static ALWAYS_INLINE uint16_t toggleHiLo(uint16_t v) {
        return (v == DsmLowVal) ? DsmHighVal : DsmLowVal;
    }

    enum DsmChannelID {
        DsmCh1,
        DsmCh2,
        DsmCh3,
        DsmCh4,
        DsmCh5,
        DsmCh6,
        DsmCh7,
        DsmCh8,
    };

    uint16_t channels[CHANNEL_COUNT];
};

#endif // DSM_H
