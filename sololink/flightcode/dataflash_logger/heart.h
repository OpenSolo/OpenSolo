#ifndef HEART_H
#define HEART_H

/*
 * heart
 *
 * Periodically send mavlink heartbeats to our upstream connection
 *
 */

#include "mavlink_message_handler.h"
#include "mavlink_writer.h"

class Heart : public MAVLink_Message_Handler
{

public:
    Heart(MAVLink_Writer *mavlink_writer)
        : MAVLink_Message_Handler(), _mavlink_writer(mavlink_writer), last_heartbeat_time(0),
          heartbeat_interval(5000000) // microseconds
    {
    }

    void idle_10Hz();
    bool configure(INIReader *config);

private:
    MAVLink_Writer *_mavlink_writer = NULL;
    uint64_t last_heartbeat_time;
    const uint32_t heartbeat_interval;
    void beat();
};

#endif
