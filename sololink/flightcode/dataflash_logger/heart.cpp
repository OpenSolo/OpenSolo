#include "heart.h"

#include "util.h"
#include "la-log.h"

void Heart::idle_10Hz()
{
    uint64_t now_us = clock_gettime_us(CLOCK_MONOTONIC);
    if (last_heartbeat_time + heartbeat_interval < now_us) {
        last_heartbeat_time = now_us;
        beat();
    }
}

bool Heart::configure(INIReader *config)
{
    if (!MAVLink_Message_Handler::configure(config)) {
        return false;
    }
    return true;
}

void Heart::beat()
{
    mavlink_message_t msg;

    uint8_t type = MAV_TYPE_GCS;
    uint8_t autopilot = MAV_AUTOPILOT_INVALID;
    uint8_t base_mode = 0;
    uint32_t custom_mode = 0;
    uint8_t system_status = 0;

    la_log(LOG_DEBUG, "mh-h: sending heartbeat");

    mavlink_msg_heartbeat_pack(system_id, component_id, &msg, type, autopilot, base_mode,
                               custom_mode, system_status);

    _mavlink_writer->send_message(msg);
}
