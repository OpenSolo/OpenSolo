
#include <sys/socket.h>
#include "Commander.h"

class RcCommander : public Commander
{
public:
    RcCommander(const char *sock_name) : Commander(sock_name), uplink_attached(true){};

    inline bool is_attached(void)
    {
        return uplink_attached;
    }

protected:
    // override attach/detach to handle the special case of attaching
    // or detaching the RC uplink
    virtual void handle_attach(const struct sockaddr *, socklen_t, const char *, bool);

private:
    bool uplink_attached;

}; // class RcCommander
