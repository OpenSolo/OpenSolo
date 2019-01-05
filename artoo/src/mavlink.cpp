#include "mavlink.h"
#include "flightmanager.h"
#include "sologimbal.h"

mavlink_message_t Mavlink::currentMsg;
mavlink_status_t Mavlink::status;

void Mavlink::onMavlinkData(const uint8_t *bytes, unsigned len)
{
    /*
     * A chunk of mavlink data has arrived.
     *
     * It may or may not contain a complete mavlink packet, so we maintain
     * a mavlink_message_t persistently to assemble packets as they arrive.
     */

    for (unsigned i = 0; i < len; ++i) {
        if (mavlink_parse_char(MAVLINK_COMM_0, bytes[i], &currentMsg, &status)) {

            if (msgIsFromPixhawk(currentMsg)) {
                FlightManager::instance.onPixhawkMavlinkMsg(&currentMsg);

            } else if (msgIsFromSoloLink(currentMsg)) {
                FlightManager::instance.onSoloMavlinkMsg(&currentMsg);

            } else if (msgIsFromSoloGimbal(currentMsg)) {
                SoloGimbal::instance.onMavlinkMsg(&currentMsg);
            }
        }
    }
}

void Mavlink::packetizeMsg(HostProtocol::Packet &p, const mavlink_message_t *msg)
{
    /*
     * Helper to pack a mavlink packet into a hostprotocol packet.
     *
     * More copying than would be ideal... maybe we implement our
     * own version of mavlink_msg_to_send_buffer() if this is a problem.
     */

    uint8_t mavlinkTxBuf[MAVLINK_MAX_PACKET_LEN];
    uint16_t len = mavlink_msg_to_send_buffer(mavlinkTxBuf, msg);

    p.delimitSlip();
    p.appendSlip(HostProtocol::Mavlink);
    p.appendSlip(mavlinkTxBuf, len);
    p.delimitSlip();
}
