#ifndef _SOLO_GIMBAL_H
#define _SOLO_GIMBAL_H

#include "mavlink.h"
#include "tasks.h"

class SoloGimbal
{
public:
    SoloGimbal();

    static SoloGimbal instance;

    static constexpr float ANGLE_MAX = 0.0;
    static constexpr float ANGLE_MIN = -90.0;

    bool isConnected() const {
        return connCounter < CONN_DURATION;
    }

    void sysHeartbeat();
    void onMavlinkMsg(const mavlink_message_t *msg);
    void onMountStatus(const mavlink_mount_status_t &s);

    bool angleIsValid() const {
        return ANGLE_MIN <= angle && angle <= ANGLE_MAX;
    }

    float reportedAngle() const {
        return angle;
    }

private:
    static constexpr float ANGLE_UNKNOWN = 9999.0;
    static const unsigned CONN_DURATION = Tasks::HEARTBEAT_HZ * 3;

    void connected();
    void disconnected();
    void resetConnCount();

    unsigned connCounter;
    float angle;
};

#endif // _SOLO_GIMBAL_H
