
#include <pthread.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>

#include <vector>
#include <string>
#include <iostream>
#include <sstream>

#include "Log.h"

using namespace std;


ostream& operator<<(ostream& os, const struct sockaddr& sa);


// Simple wrapper for sockaddr and its variants
class SockAddr
{

    public:

        // Constructor mainly just checks that the supplied sockaddr fits
        // (else is is probably corrupt).
        SockAddr(struct sockaddr *s, socklen_t len)
        {
            memset(&su, 0, sizeof(su));
            sl = len;
            if (sl > sizeof(su))
                sl = sizeof(su);
            memcpy(&su, s, sl);
        }

        // Destructor doesn't need to do anything; memory cleared for fun.
        ~SockAddr()
        {
            memset(&su, 0, sizeof(su));
            sl = 0;
        }

        // Used when adding/deleting a new SockAddr to see if a particular
        // one is already in the list
        const bool operator==(const SockAddr& rhs)
        {
            // address does not have to match after 'sl' bytes
            return (sl == rhs.sl) && (memcmp(&su, &rhs.su, sl) == 0);
        }

        // 'string' representation is used in the response to a 'list'
        // command, where a list of all SockAddrs is being sent back. Uses
        // operator<< for the conversion.
        string to_string(void)
        {
            ostringstream ss;
            ss << *this;
            return ss.str();
        }

        // member accessor
        const struct sockaddr *sockaddr()
        {
            return &su.sa;
        }

        // member accessor
        const socklen_t socklen()
        {
            return sl;
        }

        friend ostream& operator<<(ostream&, const SockAddr&);

    private:

        // The actual socket address. In most cases an anonymous union would
        // be better, but there are some cases where we want the maximum size.
        union {
            struct sockaddr sa;
            struct sockaddr_in in;
            struct sockaddr_un un;
        } su;

        // sockaddr_un requires the length to fully specify the address
        // (see 'man 7 unix', pathname vs. unnamed vs. abstract). We only
        // support the pathname variant a the moment, but this is maintained
        // for possible future enhancement.
        socklen_t sl;

}; // SockAddr


class Commander
{
    public:
        Commander(const char *sock_name);
        ~Commander();
        void send_clients(const void *data, int num_bytes);

    protected:
        int _fd;
        virtual void handle_attach(const struct sockaddr *, socklen_t,
                                   const char *, bool);
        virtual void handle_list(const struct sockaddr *, socklen_t);
        virtual void handle_ping(const struct sockaddr *, socklen_t);
        void send_response(const struct sockaddr *, socklen_t,
                           const char *, ssize_t response_len=-1);

    private:
        struct sockaddr_un sa;
        pthread_t thread_id;
        vector<SockAddr> clients;
        pthread_mutex_t clients_mutex;

        void *command_thread(void);

        static const int MAX_CMD_LEN = 64;

        // the purpose of this is to give pthread_create a class static
        // function that calls back to an object method
        static void *command_entry(void *arg)
        {
            Commander *me = (Commander *)arg;
            return me->command_thread();
        }
};
