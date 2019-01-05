#include "common_tool.h"

#include "mavlink_reader.h"
#include "mavlink_writer.h"
#include "telem_client.h"

class DataFlash_Logger_Program : public Common_Tool
{
public:
    DataFlash_Logger_Program() : Common_Tool()
    {
    }

    void run();

    void parse_arguments(int argc, char *argv[]);
    const char *program_name();

    void pack_select_fds(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err,
                         uint8_t &nfds) override;
    void handle_select_fds(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err,
                           uint8_t &nfds) override;

private:
    void usage();
    void sighup_received_tophalf() override;
    void do_idle_callbacks() override;
    uint32_t select_timeout_us() override;

    void do_writer_sends();

    MAVLink_Reader *reader;
    MAVLink_Writer *_writer;

    long _argc = 0;
    char **_argv = NULL;

    uint8_t _client_recv_buf[512] = {}; // FIXME constant was TELEM_PKT_MAX

    static const uint32_t _client_buflen = 65536; // FIXME constant
    uint32_t _client_buflen_start = 0;
    uint32_t _client_buflen_stop = 0;

    Telem_Client *client = NULL;
    bool debug_mode = false;
    bool serial_port = false;
    // uint8_t _writer_buf[_writer_buflen] = { };
    uint32_t canary = 9876543;
};
