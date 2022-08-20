#pragma once
// MESSAGE GIMBAL_FACTORY_PARAMETERS_LOADED PACKING

#define MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED 207


typedef struct __mavlink_gimbal_factory_parameters_loaded_t {
 uint8_t dummy; /*<  Dummy field because mavgen doesn't allow messages with no fields*/
} mavlink_gimbal_factory_parameters_loaded_t;

#define MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN 1
#define MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_MIN_LEN 1
#define MAVLINK_MSG_ID_207_LEN 1
#define MAVLINK_MSG_ID_207_MIN_LEN 1

#define MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_CRC 201
#define MAVLINK_MSG_ID_207_CRC 201



#if MAVLINK_COMMAND_24BIT
#define MAVLINK_MESSAGE_INFO_GIMBAL_FACTORY_PARAMETERS_LOADED { \
    207, \
    "GIMBAL_FACTORY_PARAMETERS_LOADED", \
    1, \
    {  { "dummy", NULL, MAVLINK_TYPE_UINT8_T, 0, 0, offsetof(mavlink_gimbal_factory_parameters_loaded_t, dummy) }, \
         } \
}
#else
#define MAVLINK_MESSAGE_INFO_GIMBAL_FACTORY_PARAMETERS_LOADED { \
    "GIMBAL_FACTORY_PARAMETERS_LOADED", \
    1, \
    {  { "dummy", NULL, MAVLINK_TYPE_UINT8_T, 0, 0, offsetof(mavlink_gimbal_factory_parameters_loaded_t, dummy) }, \
         } \
}
#endif

/**
 * @brief Pack a gimbal_factory_parameters_loaded message
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param msg The MAVLink message to compress the data into
 *
 * @param dummy  Dummy field because mavgen doesn't allow messages with no fields
 * @return length of the message in bytes (excluding serial stream start sign)
 */
static inline uint16_t mavlink_msg_gimbal_factory_parameters_loaded_pack(uint8_t system_id, uint8_t component_id, mavlink_message_t* msg,
                               uint8_t dummy)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char buf[MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN];
    _mav_put_uint8_t(buf, 0, dummy);

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), buf, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN);
#else
    mavlink_gimbal_factory_parameters_loaded_t packet;
    packet.dummy = dummy;

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), &packet, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN);
#endif

    msg->msgid = MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED;
    return mavlink_finalize_message(msg, system_id, component_id, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_MIN_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_CRC);
}

/**
 * @brief Pack a gimbal_factory_parameters_loaded message on a channel
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param chan The MAVLink channel this message will be sent over
 * @param msg The MAVLink message to compress the data into
 * @param dummy  Dummy field because mavgen doesn't allow messages with no fields
 * @return length of the message in bytes (excluding serial stream start sign)
 */
static inline uint16_t mavlink_msg_gimbal_factory_parameters_loaded_pack_chan(uint8_t system_id, uint8_t component_id, uint8_t chan,
                               mavlink_message_t* msg,
                                   uint8_t dummy)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char buf[MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN];
    _mav_put_uint8_t(buf, 0, dummy);

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), buf, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN);
#else
    mavlink_gimbal_factory_parameters_loaded_t packet;
    packet.dummy = dummy;

        memcpy(_MAV_PAYLOAD_NON_CONST(msg), &packet, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN);
#endif

    msg->msgid = MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED;
    return mavlink_finalize_message_chan(msg, system_id, component_id, chan, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_MIN_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_CRC);
}

/**
 * @brief Encode a gimbal_factory_parameters_loaded struct
 *
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param msg The MAVLink message to compress the data into
 * @param gimbal_factory_parameters_loaded C-struct to read the message contents from
 */
static inline uint16_t mavlink_msg_gimbal_factory_parameters_loaded_encode(uint8_t system_id, uint8_t component_id, mavlink_message_t* msg, const mavlink_gimbal_factory_parameters_loaded_t* gimbal_factory_parameters_loaded)
{
    return mavlink_msg_gimbal_factory_parameters_loaded_pack(system_id, component_id, msg, gimbal_factory_parameters_loaded->dummy);
}

/**
 * @brief Encode a gimbal_factory_parameters_loaded struct on a channel
 *
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param chan The MAVLink channel this message will be sent over
 * @param msg The MAVLink message to compress the data into
 * @param gimbal_factory_parameters_loaded C-struct to read the message contents from
 */
static inline uint16_t mavlink_msg_gimbal_factory_parameters_loaded_encode_chan(uint8_t system_id, uint8_t component_id, uint8_t chan, mavlink_message_t* msg, const mavlink_gimbal_factory_parameters_loaded_t* gimbal_factory_parameters_loaded)
{
    return mavlink_msg_gimbal_factory_parameters_loaded_pack_chan(system_id, component_id, chan, msg, gimbal_factory_parameters_loaded->dummy);
}

/**
 * @brief Send a gimbal_factory_parameters_loaded message
 * @param chan MAVLink channel to send the message
 *
 * @param dummy  Dummy field because mavgen doesn't allow messages with no fields
 */
#ifdef MAVLINK_USE_CONVENIENCE_FUNCTIONS

static inline void mavlink_msg_gimbal_factory_parameters_loaded_send(mavlink_channel_t chan, uint8_t dummy)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char buf[MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN];
    _mav_put_uint8_t(buf, 0, dummy);

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED, buf, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_MIN_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_CRC);
#else
    mavlink_gimbal_factory_parameters_loaded_t packet;
    packet.dummy = dummy;

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED, (const char *)&packet, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_MIN_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_CRC);
#endif
}

/**
 * @brief Send a gimbal_factory_parameters_loaded message
 * @param chan MAVLink channel to send the message
 * @param struct The MAVLink struct to serialize
 */
static inline void mavlink_msg_gimbal_factory_parameters_loaded_send_struct(mavlink_channel_t chan, const mavlink_gimbal_factory_parameters_loaded_t* gimbal_factory_parameters_loaded)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    mavlink_msg_gimbal_factory_parameters_loaded_send(chan, gimbal_factory_parameters_loaded->dummy);
#else
    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED, (const char *)gimbal_factory_parameters_loaded, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_MIN_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_CRC);
#endif
}

#if MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN <= MAVLINK_MAX_PAYLOAD_LEN
/*
  This variant of _send() can be used to save stack space by re-using
  memory from the receive buffer.  The caller provides a
  mavlink_message_t which is the size of a full mavlink message. This
  is usually the receive buffer for the channel, and allows a reply to an
  incoming message with minimum stack space usage.
 */
static inline void mavlink_msg_gimbal_factory_parameters_loaded_send_buf(mavlink_message_t *msgbuf, mavlink_channel_t chan,  uint8_t dummy)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    char *buf = (char *)msgbuf;
    _mav_put_uint8_t(buf, 0, dummy);

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED, buf, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_MIN_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_CRC);
#else
    mavlink_gimbal_factory_parameters_loaded_t *packet = (mavlink_gimbal_factory_parameters_loaded_t *)msgbuf;
    packet->dummy = dummy;

    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED, (const char *)packet, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_MIN_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_CRC);
#endif
}
#endif

#endif

// MESSAGE GIMBAL_FACTORY_PARAMETERS_LOADED UNPACKING


/**
 * @brief Get field dummy from gimbal_factory_parameters_loaded message
 *
 * @return  Dummy field because mavgen doesn't allow messages with no fields
 */
static inline uint8_t mavlink_msg_gimbal_factory_parameters_loaded_get_dummy(const mavlink_message_t* msg)
{
    return _MAV_RETURN_uint8_t(msg,  0);
}

/**
 * @brief Decode a gimbal_factory_parameters_loaded message into a struct
 *
 * @param msg The message to decode
 * @param gimbal_factory_parameters_loaded C-struct to decode the message contents into
 */
static inline void mavlink_msg_gimbal_factory_parameters_loaded_decode(const mavlink_message_t* msg, mavlink_gimbal_factory_parameters_loaded_t* gimbal_factory_parameters_loaded)
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
    gimbal_factory_parameters_loaded->dummy = mavlink_msg_gimbal_factory_parameters_loaded_get_dummy(msg);
#else
        uint8_t len = msg->len < MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN? msg->len : MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN;
        memset(gimbal_factory_parameters_loaded, 0, MAVLINK_MSG_ID_GIMBAL_FACTORY_PARAMETERS_LOADED_LEN);
    memcpy(gimbal_factory_parameters_loaded, _MAV_PAYLOAD(msg), len);
#endif
}
