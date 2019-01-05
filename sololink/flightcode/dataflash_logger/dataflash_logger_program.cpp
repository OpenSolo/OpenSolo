#include "dataflash_logger_program.h"

#include "dataflash_logger.h"
#include "heart.h"
#include "mavlink_reader.h"
#include "telem_forwarder_client.h"
#include "telem_serial.h"

#include "la-log.h"

#include <signal.h>
#include <unistd.h>

const char *DataFlash_Logger_Program::program_name()
{
    if (_argv == NULL) {
        return "[Unknown]";
    }
    return _argv[0];
}

void DataFlash_Logger_Program::usage()
{
    ::printf("Usage:\n");
    ::printf("%s [OPTION] [FILE]\n", program_name());
    ::printf(" -c filepath      use config file filepath\n");
    ::printf(" -h               display usage information\n");
    ::printf(" -d               debug mode\n");
    ::printf("\n");
    ::printf("Example: %s\n", program_name());
    exit(0);
}

DataFlash_Logger_Program logger;

void sighup_handler(int signal)
{
    logger.sighup_handler(signal);
}

void DataFlash_Logger_Program::do_idle_callbacks()
{
    reader->do_idle_callbacks();
}

void DataFlash_Logger_Program::sighup_received_tophalf()
{
    reader->sighup_handler();
}

uint32_t DataFlash_Logger_Program::select_timeout_us()
{
    if (_writer->any_data_to_send()) {
        return 0;
    }
    return Common_Tool::select_timeout_us();
}

void DataFlash_Logger_Program::pack_select_fds(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err,
                                               uint8_t &nfds)
{
    client->pack_select_fds(fds_read, fds_write, fds_err, nfds);
}

void DataFlash_Logger_Program::do_writer_sends()
{
    client->do_writer_sends();
}

void DataFlash_Logger_Program::handle_select_fds(fd_set &fds_read, fd_set &fds_write,
                                                 fd_set &fds_err, uint8_t &nfds)
{
    client->handle_select_fds(fds_read, fds_write, fds_err, nfds);

    // FIXME: find a more interesting way of doing this...  we should
    // probably rejig things so that the client is a mavlink_reader
    // and simply produces mavlink_message_t's itself, rather than us
    // handing off the a dedicated parser object here.
    reader->feed(client->_recv_buf, client->_recv_buflen_content);
    client->_recv_buflen_content = 0;

    // handle data *to* e.g. telem_forwarder
    do_writer_sends();
}

void DataFlash_Logger_Program::run()
{
    init_config();

    if (!debug_mode) {
        la_log_syslog_open();
    }

    la_log(LOG_INFO, "dataflash_logger starting: built " __DATE__ " " __TIME__);
    signal(SIGHUP, ::sighup_handler);

    reader = new MAVLink_Reader(config());
    if (reader == NULL) {
        la_log(LOG_ERR, "Failed to create reader from (%s)\n", config_filename);
        exit(1);
    }

    if (serial_port) {
        client = new Telem_Serial(_client_recv_buf, sizeof(_client_recv_buf));
    } else {
        client = new Telem_Forwarder_Client(_client_recv_buf, sizeof(_client_recv_buf));
    }
    client->configure(config());
    client->init();

    _writer = new MAVLink_Writer(config());
    _writer->add_client(client);
    if (_writer == NULL) {
        la_log(LOG_ERR, "Failed to create writer from (%s)\n", config_filename);
        exit(1);
    }

    // instantiate message handlers:
    DataFlash_Logger *dataflash_logger = new DataFlash_Logger(_writer);
    if (dataflash_logger != NULL) {
        reader->add_message_handler(dataflash_logger, "DataFlash_Logger");
    } else {
        la_log(LOG_INFO, "Failed to create dataflash logger");
    }

    Heart *heart = new Heart(_writer);
    if (heart != NULL) {
        reader->add_message_handler(heart, "Heart");
    } else {
        la_log(LOG_INFO, "Failed to create heart");
    }

    return select_loop();
}

void DataFlash_Logger_Program::parse_arguments(int argc, char *argv[])
{
    int opt;
    _argc = argc;
    _argv = argv;

    while ((opt = getopt(argc, argv, "hc:ds")) != -1) {
        switch (opt) {
        case 'h':
            usage();
            break;
        case 'c':
            config_filename = optarg;
            break;
        case 'd':
            debug_mode = true;
            break;
        case 's':
            serial_port = true;
            break;
        }
    }
}

/*
* main - entry point
*/
int main(int argc, char *argv[])
{
    logger.parse_arguments(argc, argv);
    logger.run();
}
