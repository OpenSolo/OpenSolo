#include "dataflash_logger.h"

#include <signal.h>
#include <stdio.h> // for snprintf
#include <fcntl.h>
#include <errno.h>
#include <unistd.h>

#include <sys/stat.h>
#include <sys/types.h>
#include <sched.h> // for sched_yield

#include "la-log.h"
#include "util.h"
#include "../mavlink/c_library/common/mavlink.h"

/*

There are currently two threads: a "network" thread (see handle_message), and the fileio thread (see
fileio_task).  The network thread takes the data from the packets and packs it into _write_buffers.
It then passes the buffers to the fileio thread for writing to disk.  The buffers are then passed
back to the network thread.

Notes on thread safety:

la_log is called by both the network and IO threads.  openlog/syslog are thread safe.  The la_log
code is not designed to be thread safe.  That code is commented as such, and in future locking may
be required there.  The current implementation has races concerning message suppression but fixing
these may lead to more complexity than is justified.

The fileio and network threads in dataflash logger share:
 - out_fd
 - _write_buffers[]

out_fd is not to be touched in the main thread after it has been opened - unless logging has
stopped, and all the buffers are owned by the network thread.  The fileio thread may only touch
out_fd and _write_buffers if logging has started, or it owns buffers.

The buffers contained in _write_buffers are owned by one thread at a time.  Only the owner may
modify the buffer.  Ownership is transfered by assignment of the owner variable.  This will work for
two threads, but locking of this transfer will be required if more threads become involved, and the
programmer is suitably paranoid.

*/

void *fileio_task_wrapper(void *instance)
{
    ((DataFlash_Logger *)instance)->fileio_task();
    return NULL;
}

DataFlash_Logger::DataFlash_Logger(MAVLink_Writer *mavlink_writer)
    : MAVLink_Message_Handler(), _mavlink_writer(mavlink_writer),
      target_system_id(target_system_id_default), target_component_id(target_component_id_default),
      seqno_gap_nack_threshold(20)
{
    _current_write_buffer = &_write_buffers[0];
    pthread_mutex_init(&_write_buffer_mutex, NULL);
    pthread_cond_init(&_wakeup_fileio_thread, NULL);
    pthread_create(&_fileio_thread, NULL, fileio_task_wrapper, this);
}

void DataFlash_Logger::write_buffer_to_disk(const struct df_write_buffer *buffer)
{
    const uint8_t length = MAVLINK_MSG_REMOTE_LOG_DATA_BLOCK_FIELD_DATA_LEN;
    for (uint16_t j = 0; j < buffer->next_defered_write; j++) {
        const struct defered_write *some_write = &buffer->defered_writes[j];
        const uint32_t seqno = some_write->seqno;
        const uint8_t *data = some_write->data;
        if (lseek(out_fd, seqno * length, SEEK_SET) == -1) {
            la_log(LOG_ERR, "mh-dfl: lseek (%u) failed: %s", seqno * length, strerror(errno));
            return;
        }
        ssize_t written = write(out_fd, data, length);
        if (written < length) {
            la_log(LOG_ERR, "mh-dfl: short write: %s", strerror(errno));
            return;
        }
    }

    // TODO: write all of the blocks in the buffer to disk, trying to
    // coalesce writes as we go:
}

void DataFlash_Logger::fileio_task()
{
    while (true) {
        // we should never be called while fd == -1.
        pthread_cond_wait(&_wakeup_fileio_thread, &_write_buffer_mutex);
        // we don't actually need the mutex:
        pthread_mutex_unlock(&_write_buffer_mutex);

        df_write_buffer *buffer = next_write_buffer(FILEIO_THREAD);
        while (buffer != NULL) {
            write_buffer_to_disk(buffer);
            buffer->next_defered_write = 0;
            // hand the buffer back to the net thread:
            buffer->owner = NETWORK_THREAD;
            buffer = next_write_buffer(FILEIO_THREAD);
            fsync(out_fd);

            uint64_t now = clock_gettime_us(CLOCK_MONOTONIC);
            if (now - fileio_last_log_time > 10000000) {
                // the following isn't quite right given we seek around...
                la_log(LOG_INFO, "mh-dfl: Current log size: %lu", lseek(out_fd, 0, SEEK_CUR));
                fileio_last_log_time = now;
            }
        }
    }
}

void DataFlash_Logger::sighup_received()
{
    logging_stop();
}

void DataFlash_Logger::idle_tenthHz()
{
}

void DataFlash_Logger::idle_1Hz()
{
    if (!logging_started) {
        if (sender_system_id != 0) {
            // we've previously been logging, so telling the other end
            // to stop logging may let us restart logging sooner
            send_stop_logging_packet();
        }
        send_start_logging_packet();
    }
}
void DataFlash_Logger::idle_10Hz()
{
    if (logging_started) {
        // if no data packet in 10 seconds then close log
        uint64_t now_us = clock_gettime_us(CLOCK_MONOTONIC);
        if (now_us - _last_data_packet_time > 10000000) {
            la_log(LOG_INFO, "mh-dfl: No data packets received for some time (now=%llu last=%llu). "
                             " Closing log.  Final log size: %lu",
                   now_us, _last_data_packet_time, lseek(out_fd, 0, SEEK_CUR));
            logging_stop();
        }
    }
}

void DataFlash_Logger::idle_100Hz()
{
    push_response_queue();
}

void DataFlash_Logger::send_response(uint32_t seqno, bool status)
{
    mavlink_message_t msg;
    mavlink_msg_remote_log_block_status_pack(system_id, component_id, &msg, sender_system_id,
                                             sender_component_id, seqno, status);
    _mavlink_writer->send_message(msg);
}

void DataFlash_Logger::push_response_queue()
{
    const uint8_t max_packets_to_send = 5;
    uint8_t packets_sent = 0;
    while (response_queue_head != response_queue_tail && packets_sent < max_packets_to_send) {
        send_response(responses[response_queue_tail].seqno, responses[response_queue_tail].status);
        response_queue_tail++;
        if (response_queue_tail >= RESPONSE_QUEUE_LENGTH) {
            response_queue_tail = 0;
        }
    }
}

bool DataFlash_Logger::configure(INIReader *config)
{
    if (!MAVLink_Message_Handler::configure(config)) {
        return false;
    }

    std::string path = config->Get("dflogger", "log_dirpath", "/log/dataflash");
    _log_directory_path = strdup(path.c_str());
    if (_log_directory_path == NULL) {
        return false;
    }

    // need to do equivalent of 'mkdir -p log_dirpath' here
    // (i.e. handle multi-level path)
    if (mkdir(_log_directory_path,
              S_IRUSR | S_IWUSR | S_IXUSR | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH) != 0) {
        // this is expected to succeed on the first boot after a factory or
        // settings reset, then fail with EEXIST each startup after that.
        if (errno != EEXIST) {
            la_log(LOG_ERR, "mh-dfl: Failed to create (%s): %s", _log_directory_path,
                   strerror(errno));
            return false;
        }
    }

    target_system_id = config->GetInteger("dflogger", "target_system_id", 0);
    target_component_id = config->GetInteger("dflogger", "target_component_id", 0);

    return true;
}

bool DataFlash_Logger::make_new_log_filename(char *buffer, uint8_t bufferlen)
{
    uint8_t lastlog_buflen = 128;
    char lastlog_buf[128];
    // this was really beautiful, but I don't think SoloLink has an
    // RTC; it depends on GPS to update its clock (scribbled down
    // periodically?)

    // time_t t;

    // time(&t);
    // struct tm *timebits = gmtime(&t);

    // snprintf(buffer, bufferlen, "%s/%04d%02d%02d%02d%02d%02d.BIN",
    //          _log_directory_path,
    //          timebits->tm_year+1900,
    //          timebits->tm_mon+1,
    //          timebits->tm_mday,
    //          timebits->tm_hour,
    //          timebits->tm_min,
    //          timebits->tm_sec);

    memset(lastlog_buf, '\0', lastlog_buflen);
    snprintf(lastlog_buf, lastlog_buflen, "%s/LASTLOG.TXT", _log_directory_path);
    int fd;
    uint32_t num;
    if ((fd = open(lastlog_buf, O_RDONLY)) == -1) {
        if (errno != ENOENT) {
            // what?
            syslog(LOG_ERR, "Failed to open (%s) for reading: %s", lastlog_buf, strerror(errno));
            return false;
        }
        num = 1;
    } else {
        uint8_t numbuf_len = 128;
        char numbuf[numbuf_len];
        memset(numbuf, '\0', numbuf_len);
        int bytes_read = read(fd, numbuf, numbuf_len);
        close(fd);
        if (bytes_read == -1) {
            return false;
        }
        num = strtoul(numbuf, NULL, 10);
        num++;
    }

    if ((fd = open(lastlog_buf, O_WRONLY | O_TRUNC | O_CREAT)) == -1) {
        // *shrug*  We will continue to overwrite, I guess...
    } else {
        const uint8_t outsize = 16;
        char out[outsize];
        memset(out, '\0', outsize);
        int towrite = snprintf(out, outsize, "%d\r\n", num);
        write(fd, out, towrite); // ignore return...
        close(fd);
    }

    snprintf(buffer, bufferlen, "%s/%d.BIN", _log_directory_path, num);

    return true;
}

bool DataFlash_Logger::output_file_open()
{
    const uint8_t filename_length = 64;
    char filename[filename_length];

    if (!make_new_log_filename(filename, filename_length)) {
        return false;
    }

    out_fd = open(filename, O_WRONLY | O_CREAT | O_TRUNC, 0777);
    if (out_fd == -1) {
        printf("Failed to open (%s): %s\n", filename, strerror(errno));
        la_log(LOG_ERR, "mh-dfl: Failed to open (%s): %s", filename, strerror(errno));
        return false;
    }
    la_log(LOG_INFO, "mh-dfl: Opened log file (%s)", filename);

    return true;
}

void DataFlash_Logger::output_file_close()
{
    close(out_fd);
    out_fd = -1;
}

void DataFlash_Logger::queue_response(uint32_t seqno, bool status)
{
    responses[response_queue_head].seqno = seqno;
    responses[response_queue_head].status = status;
    response_queue_head++;
    if (response_queue_head >= RESPONSE_QUEUE_LENGTH) {
        response_queue_head = 0;
    }
}

void DataFlash_Logger::queue_ack(uint32_t seqno)
{
    queue_response(seqno, true);
}

void DataFlash_Logger::queue_nack(uint32_t seqno)
{
    queue_response(seqno, false);
}

void DataFlash_Logger::queue_gap_nacks(uint32_t seqno)
{
    if (seqno <= highest_seqno_seen) {
        // this packet filled in a gap (or was a dupe)
        return;
    }

    if (seqno - highest_seqno_seen > seqno_gap_nack_threshold) {
        // we've seen some serious disruption, and lots of stuff
        // is probably going to be lost.  Do not bother NACKing
        // packets here and let the server sort things out
        return;
    }

    for (uint32_t i = highest_seqno_seen + 1; i < seqno; i++) {
        queue_nack(i);
    }
}

bool DataFlash_Logger::logging_start(mavlink_remote_log_data_block_t &msg UNUSED)
{
    sender_system_id = most_recent_sender_system_id;
    sender_component_id = most_recent_sender_component_id;
    la_log_unsuppress();
    la_log(LOG_INFO, "mh-dfl: Starting log, target is (%d/%d), I am (%d/%d)", sender_system_id,
           sender_component_id, this_system_id, this_component_id);
    if (!output_file_open()) {
        return false;
    }

    logging_started = true;
    return true;
}

void DataFlash_Logger::ensure_write_buffers_ownership()
{
    for (uint16_t i = 0; i < _max_write_buffers; i++) {
        uint8_t count = 0;
        while (_write_buffers[i].owner != NETWORK_THREAD) {
            pthread_cond_signal(&_wakeup_fileio_thread);
            sched_yield();
            // do we need really a sleep in here?
            usleep(100000);
            if (count++ > 100) {
                la_log(LOG_ERR, "Stuck waiting for buffers to be freed; exitting");
                abort();
            }
        }
    }
}

void DataFlash_Logger::logging_stop()
{
    logging_started = false;
    // we need to own all of the _write_buffers[] to ensure the
    // iothread is not currently using the output filehandle:
    ensure_write_buffers_ownership();
    output_file_close();
}

void DataFlash_Logger::handle_message(uint64_t timestamp, mavlink_message_t &msg)
{
    most_recent_sender_system_id = msg.sysid;
    most_recent_sender_component_id = msg.compid;
    MAVLink_Message_Handler::handle_message(timestamp, msg);
}

struct DataFlash_Logger::df_write_buffer *
DataFlash_Logger::next_write_buffer(const DataFlash_Logger::write_buffer_owner owner)
{
    for (uint8_t i = 0; i < _max_write_buffers; i++) {
        if (_write_buffers[i].owner == owner) {
            return &_write_buffers[i];
        }
    }
    return NULL;
}

void DataFlash_Logger::handle_decoded_message(uint64_t T UNUSED,
                                              mavlink_remote_log_data_block_t &msg)
{
    if (!logging_started) {
        if (msg.seqno == 0) {
            if (!logging_start(msg)) {
                return;
            }
        } else {
            return;
        }
    }

    uint64_t now = clock_gettime_us(CLOCK_MONOTONIC);
    if (now - _last_data_packet_time > 100000) {
        ::la_log(LOG_ERR, "mh-dfl: long time between messages (%ld)", now - _last_data_packet_time);
    }

    if (_current_write_buffer == NULL) {
        _current_write_buffer = next_write_buffer(NETWORK_THREAD);
        if (_current_write_buffer == NULL) {
            la_log(LOG_ERR, "mh-dfl: no write buffer available");
            _last_data_packet_time = now;
            return;
        }
    }

    struct defered_write *defered_write =
        &_current_write_buffer->defered_writes[_current_write_buffer->next_defered_write++];
    memcpy(defered_write->data, msg.data, MAVLINK_MSG_REMOTE_LOG_DATA_BLOCK_FIELD_DATA_LEN);
    defered_write->seqno = msg.seqno;
    if (_current_write_buffer->next_defered_write >= _df_write_buffer_max_defered_writes) {
        // this buffer is full.  Hand it to the FILEIO thread:
        _current_write_buffer->owner = FILEIO_THREAD;
        _current_write_buffer = NULL;
        // and wake the fileio thread up:
        pthread_cond_signal(&_wakeup_fileio_thread);
    }

    if (clock_gettime_us(CLOCK_MONOTONIC) - now > 100000) {
        ::la_log(LOG_ERR, "mh-dfl: long time to write (%ld)",
                 clock_gettime_us(CLOCK_MONOTONIC) - now);
    }

    // queue an ack for this packet
    queue_ack(msg.seqno);

    // queue nacks for gaps
    queue_gap_nacks(msg.seqno);

    if (msg.seqno > highest_seqno_seen) {
        if (msg.seqno - highest_seqno_seen > 100) {
            la_log(LOG_ERR, "mh-dfl: large seqno gap: %ld", msg.seqno - highest_seqno_seen);
        }
        highest_seqno_seen = msg.seqno;
    }

    _last_data_packet_time = now;
}

void DataFlash_Logger::send_start_logging_packet()
{
    send_start_or_stop_logging_packet(true);
}

void DataFlash_Logger::send_stop_logging_packet()
{
    send_start_or_stop_logging_packet(false);
}

void DataFlash_Logger::send_start_or_stop_logging_packet(bool is_start)
{
    mavlink_message_t msg;

    uint8_t system_id = is_start ? target_system_id : sender_system_id;
    uint8_t component_id = is_start ? target_component_id : sender_component_id;
    uint32_t magic_number;
    if (is_start) {
        // la_log(LOG_INFO, "mh-dfl: sending start packet to (%d/%d)", system_id, component_id);
        magic_number = MAV_REMOTE_LOG_DATA_BLOCK_START;
    } else {
        // la_log(LOG_INFO, "mh-dfl: sending stop packet to (%d/%d)", system_id, component_id);
        magic_number = MAV_REMOTE_LOG_DATA_BLOCK_STOP;
    }
    mavlink_msg_remote_log_block_status_pack(this_system_id, this_component_id, &msg, system_id,
                                             component_id, magic_number, 1);

    _mavlink_writer->send_message(msg);
}
