#include "sologimbal.h"
#include "ui.h"

SoloGimbal SoloGimbal::instance;

SoloGimbal::SoloGimbal() :
    connCounter(CONN_DURATION),
    angle(ANGLE_UNKNOWN)
{
}

void SoloGimbal::sysHeartbeat()
{
    /*
     * called from heartbeat task.
     * Do any work that requires periodic attention.
     */

    if (isConnected()) {
        if (++connCounter >= CONN_DURATION) {
            disconnected();
        }
    }
}

void SoloGimbal::connected()
{
    /*
     * Called when the gimbal transitions to a connected state.
     */

    Ui::instance.pendEvent(Event::GimbalConnChanged);

    // Don't display gimbal connected/disconnected messages while armed or in-flight since it is unlikely that
    // the gimbal would become disconnected/reconnected and frequent link reconnection could result in a bad
    // UI experience
    const FlightManager & fm = FlightManager::instance;
    if (!fm.armed() && !fm.inFlight()) {
        Ui::instance.pendEvent(Event::GimbalConnected);
    }
}

void SoloGimbal::disconnected()
{
    /*
     * Called when the gimbal transitions to a disconnected state.
     */

    angle = ANGLE_UNKNOWN;

    Ui::instance.pendEvent(Event::GimbalConnChanged);

    // Don't display gimbal connected/disconnected messages while armed or in-flight since it is unlikely that
    // the gimbal would become disconnected/reconnected and frequent link reconnection could result in a bad
    // UI experience
    const FlightManager & fm = FlightManager::instance;
    if (!fm.armed() && !fm.inFlight()) {
        Ui::instance.pendEvent(Event::GimbalNotConnected);
    }
}

void SoloGimbal::resetConnCount()
{
    if (!isConnected()) {
        connected();
    }

    connCounter = 0;
}

void SoloGimbal::onMavlinkMsg(const mavlink_message_t *msg)
{
    resetConnCount();

    switch (msg->msgid) {
    case MAVLINK_MSG_ID_HEARTBEAT:
        break;

    default:
        break;
    }
}

void SoloGimbal::onMountStatus(const mavlink_mount_status_t &s)
{
    /*
     * Mount status messages come from the pixhawk,
     * rather than directly from the gimbal but we want to logically
     * group it with the gimbal, so route them here from flightmanager
     * as a special case.
     */

    if (!isConnected()) {
        // assume some other gimbal is reporting
        return;
    }

    angle = clamp(s.pointing_a / 100.0f, ANGLE_MIN, ANGLE_MAX);
    Ui::instance.pendEvent(Event::SoloGimbalAngleChanged);
}
