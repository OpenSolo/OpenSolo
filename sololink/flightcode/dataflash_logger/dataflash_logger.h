#ifndef DATAFLASH_LOGGER_H
#define DATAFLASH_LOGGER_H

/*
 * dataflash_logger
 *
 * Receive telemetry (mavlink) via UDP from Solo, and create dataflash log files
 *
 * Initiate a remote-dataflash stream
 */

#include "INIReader.h"

#include "mavlink_message_handler.h"
#include "mavlink_writer.h"

#include "../mavlink/c_library/common/mavlink.h"

class DataFlash_Logger : public MAVLink_Message_Handler
{

public:
    void fileio_task();

    DataFlash_Logger(MAVLink_Writer *mavlink_writer);

    enum write_buffer_owner { NETWORK_THREAD, FILEIO_THREAD };

private:
    bool configure(INIReader *config);

    void sighup_received();

    void idle_tenthHz();
    void idle_1Hz();
    void idle_10Hz();
    void idle_100Hz();
    bool logging_start(mavlink_remote_log_data_block_t &msg);
    void logging_stop();
    void send_stop_logging_packet();

    bool output_file_open();
    void output_file_close();

    void ensure_write_buffers_ownership();

    // more, smaller buffers means a lower latency to disk.  A total
    // of 700 defered writes gives about 10 seconds of buffering based
    // on a 12k transfer rate.
    static const uint8_t _max_write_buffers = 7;
    static const uint16_t _df_write_buffer_max_defered_writes = 100;
    struct defered_write {
        uint8_t data[MAVLINK_MSG_REMOTE_LOG_DATA_BLOCK_FIELD_DATA_LEN];
        uint32_t seqno;
    };

    struct df_write_buffer {
        struct defered_write defered_writes[_df_write_buffer_max_defered_writes];
        write_buffer_owner owner = NETWORK_THREAD;
        uint16_t next_defered_write = 0;
    } _write_buffers[_max_write_buffers];
    struct df_write_buffer *_current_write_buffer = NULL;
    void write_buffer_to_disk(const struct df_write_buffer *buffer);
    bool write_block_for_seqno(const uint8_t *data, uint32_t seqno);
    struct df_write_buffer *next_write_buffer(const write_buffer_owner owner);
    uint64_t fileio_last_log_time = 0;

    pthread_mutex_t _write_buffer_mutex;
    pthread_cond_t _wakeup_fileio_thread;
    pthread_t _fileio_thread;

    MAVLink_Writer *_mavlink_writer = NULL;
    uint8_t this_system_id = 57;
    uint8_t this_component_id = 57;

    const uint8_t target_system_id_default = 0;
    const uint8_t target_component_id_default = 0;
    uint8_t most_recent_sender_system_id;
    uint8_t most_recent_sender_component_id;
    uint8_t target_system_id;        // who to send our request-for-logs to
    uint8_t target_component_id;     // who to send our request-for-logs to
    uint8_t sender_system_id = 0;    // who the logs areactually coming from
    uint8_t sender_component_id = 0; // who the logs areactually coming from

    void send_start_logging_packet();
    void send_start_or_stop_logging_packet(bool is_start);
    const char *_log_directory_path;
    int out_fd;
    bool logging_started = false;

    void handle_message(uint64_t timestamp, mavlink_message_t &msg);
    void handle_decoded_message(uint64_t T, mavlink_remote_log_data_block_t &msg);

    bool make_new_log_filename(char *buffer, uint8_t bufferlen);

    void send_response(uint32_t seqno, bool status);
    void push_response_queue();

#define RESPONSE_QUEUE_LENGTH 128
    struct packet_status {
        uint32_t seqno;
        bool status; // ack == true
    } responses[RESPONSE_QUEUE_LENGTH];
    uint8_t response_queue_head = 0;
    uint8_t response_queue_tail = 0;

    uint32_t highest_seqno_seen = 0;
    uint64_t _last_data_packet_time = 0;

    /* if we lose > this many packets we do not nack anything in that gap: */
    uint8_t seqno_gap_nack_threshold;

    void queue_response(uint32_t seqno, bool status);
    void queue_nack(uint32_t seqno);
    void queue_ack(uint32_t seqno);
    void queue_gap_nacks(uint32_t seqno);
};

#endif
