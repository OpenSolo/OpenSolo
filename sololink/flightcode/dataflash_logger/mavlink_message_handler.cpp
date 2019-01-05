#include "mavlink_message_handler.h"

#include "la-log.h"
#include <errno.h>

// void MAVLink_Message_Handler::send_message_to_telem_forwarder(mavlink_message_t &msg)
// {
//   uint8_t sendbuf[512];

//   uint16_t messageLen = mavlink_msg_to_send_buffer((uint8_t*)sendbuf,&msg);

//   if (sendto(_fd_telem_forwarder, sendbuf, messageLen, 0, (struct sockaddr
//   *)_sa_telemetry_forwarder, sizeof(struct sockaddr)) == -1) {
//     la_log(LOG_INFO, "Failed sendto: %s", strerror(errno));
//   }
// }

void MAVLink_Message_Handler::handle_message(uint64_t timestamp, mavlink_message_t &msg)
{
    // ::fprintf(stderr, "msg.msgid=%u\n", msg.msgid);
    switch (msg.msgid) {
    case MAVLINK_MSG_ID_AHRS2: {
        mavlink_ahrs2_t decoded;
        mavlink_msg_ahrs2_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_ATTITUDE: {
        mavlink_attitude_t decoded;
        mavlink_msg_attitude_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_EKF_STATUS_REPORT: {
        mavlink_ekf_status_report_t decoded;
        mavlink_msg_ekf_status_report_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_GLOBAL_POSITION_INT: {
        mavlink_global_position_int_t decoded;
        mavlink_msg_global_position_int_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_GPS_RAW_INT: {
        mavlink_gps_raw_int_t decoded;
        mavlink_msg_gps_raw_int_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_HEARTBEAT: {
        mavlink_heartbeat_t decoded;
        mavlink_msg_heartbeat_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_MOUNT_STATUS: {
        mavlink_mount_status_t decoded;
        mavlink_msg_mount_status_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_NAV_CONTROLLER_OUTPUT: {
        mavlink_nav_controller_output_t decoded;
        mavlink_msg_nav_controller_output_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_PARAM_VALUE: {
        mavlink_param_value_t decoded;
        mavlink_msg_param_value_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_REMOTE_LOG_DATA_BLOCK: {
        mavlink_remote_log_data_block_t decoded;
        mavlink_msg_remote_log_data_block_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_SCALED_PRESSURE: {
        mavlink_scaled_pressure_t decoded;
        mavlink_msg_scaled_pressure_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_SCALED_PRESSURE2: {
        mavlink_scaled_pressure2_t decoded;
        mavlink_msg_scaled_pressure2_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_SERVO_OUTPUT_RAW: {
        mavlink_servo_output_raw_t decoded;
        mavlink_msg_servo_output_raw_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_STATUSTEXT: {
        mavlink_statustext_t decoded;
        mavlink_msg_statustext_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_SYS_STATUS: {
        mavlink_sys_status_t decoded;
        mavlink_msg_sys_status_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    case MAVLINK_MSG_ID_VFR_HUD: {
        mavlink_vfr_hud_t decoded;
        mavlink_msg_vfr_hud_decode(&msg, &decoded);
        handle_decoded_message(timestamp, decoded);
        break;
    }
    }
}
