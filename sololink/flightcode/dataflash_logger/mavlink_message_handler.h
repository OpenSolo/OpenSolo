#ifndef MAVLINK_MESSAGE_HANDLER_H
#define MAVLINK_MESSAGE_HANDLER_H

/*
 * mavlink_message_handler
 *
 * A base class for objects which process mavlink messages and
 * possibly send responses
 *
 */

#include <stdint.h>

#include "INIReader.h"
#include "../mavlink/c_library/ardupilotmega/mavlink.h"
#include "../mavlink/c_library/common/mavlink.h"

#include <netinet/in.h>

#include "message_handler.h"

#define UNUSED __attribute__((unused))

class MAVLink_Message_Handler : public Message_Handler
{
public:
    MAVLink_Message_Handler() : Message_Handler()
    {
    }

    virtual bool configure(INIReader *config)
    {
        system_id = config->GetInteger("dflogger", "system_id", 254);
        component_id = config->GetInteger("dflogger", "component_id", 17);
        return true;
    }

    virtual void handle_message(uint64_t timestamp, mavlink_message_t &msg);
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_ahrs2_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_attitude_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_ekf_status_report_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_gps_raw_int_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED,
                                        mavlink_global_position_int_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_heartbeat_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_mount_status_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED,
                                        mavlink_nav_controller_output_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_param_value_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED,
                                        mavlink_remote_log_data_block_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_scaled_pressure_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_scaled_pressure2_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_servo_output_raw_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_sys_status_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_statustext_t &msg UNUSED)
    {
    }
    virtual void handle_decoded_message(uint64_t T UNUSED, mavlink_vfr_hud_t &msg UNUSED)
    {
    }

protected:
    uint8_t system_id;
    uint8_t component_id;

private:
};

#endif
