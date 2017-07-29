#ifndef _MAVLINK_H
#define _MAVLINK_H

#include "mavlink/c_library/ardupilotmega/mavlink.h"
#include "mavlink/c_library/common/mavlink.h"

#include "hostprotocol.h"

class Mavlink
{
public:
    Mavlink();    // do no implement

    static const uint8_t ArtooSysID             = 0xff; // default sysid pixhawk looks for
    static const uint8_t ArtooComponentID       = MAV_TYPE_GCS;

    static const uint8_t SoloSysID              = 0x01;
    static const uint8_t SoloComponentID        = 0x01; // default

    static const uint8_t GimbalSysID            = 1;
    static const uint8_t GimbalComponentID      = 154;

    static const uint8_t RssiSenderSysID        = 10;
    static const uint8_t RssiSenderComponentID  = 0;

    static void onMavlinkData(const uint8_t *bytes, unsigned len);
    static void packetizeMsg(HostProtocol::Packet &p, const mavlink_message_t *msg);

private:

    static inline bool msgIsFromSoloLink(const mavlink_message_t & m) {
        return m.sysid == RssiSenderSysID && m.compid == RssiSenderComponentID;
    }

    static inline bool msgIsFromPixhawk(const mavlink_message_t & m) {
        return m.sysid == SoloSysID && m.compid == SoloComponentID;
    }

    static inline bool msgIsFromSoloGimbal(const mavlink_message_t & m) {
        return m.sysid == GimbalSysID && m.compid == GimbalComponentID;
    }

    static mavlink_message_t currentMsg;
    static mavlink_status_t status;
};

#endif // _MAVLINK_H
