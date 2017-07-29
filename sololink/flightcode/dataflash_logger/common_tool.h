#include "util.h"
#include "analyzer_util.h"
#include "INIReader.h"

#include "format_reader.h"

class Common_Tool
{
public:
    Common_Tool() : config_filename(default_config_filename)
    {
    }

    void sighup_handler(int signal);

    void parse_fd(Format_Reader *reader, int fd);

protected:
    class INIReader *config()
    {
        return _config;
    };
    void init_config();
    const char *default_config_filename = "/etc/sololink.conf";
    const char *config_filename;

    virtual void sighup_received_tophalf();

    bool _sighup_received = false; // FIXME: scope

    virtual uint32_t select_timeout_us();
    void select_loop();

    virtual void pack_select_fds(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err,
                                 uint8_t &nfds);
    virtual void handle_select_fds(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err,
                                   uint8_t &nfds);
    virtual void do_idle_callbacks();

private:
    void check_fds_are_empty_after_select(fd_set &fds_read, fd_set &fds_write, fd_set &fds_err,
                                          uint8_t nfds);
    class INIReader *_config = NULL;
};
