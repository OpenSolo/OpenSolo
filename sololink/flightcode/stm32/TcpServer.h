#ifndef _TCP_SERVER_H_
#define _TCP_SERVER_H_

#include <pthread.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <list>
#include "SoloMessage.h"

class TcpServer;

// One of these for each connection accepted, containing required
// state for the connection.
class TcpClient
{

public:
    TcpClient(TcpServer *server, int fd_client);
    ~TcpClient();
    int send_upstream(const void *data, int data_len);
    bool do_recv(void);
    inline int fd_client(void) const
    {
        return _fd_client;
    };

private:
    // Stuff shared by all clients is kept in the server
    TcpServer *_server;

    // File descriptor for this client. This is already open when the
    // client is constructed, but is closed by the client destructor.
    // This is the TCP stream to/from the client.
    int _fd_client;

    // Since the connection is TCP, we might get more or less than one
    // message on each read. Data is buffered here until we have at least
    // one message, then the message is sent downstream, and any leftover
    // data is copied to the front of the buffer (since it is part of the
    // next message).
    const static unsigned _buf_len = 256;
    char _buf[_buf_len];
    // How much is currently in _buf.
    unsigned _buf_bytes;

    void invariant(void) const;

    friend TcpServer;

}; // TcpClient

// One of these per listening port. listen_thread thread listens on a socket
// for client connections, and downstream_thread selects on a set of sockets,
// one for each client, waiting for downstream messages. Upstream messages are
// sent via the send_clients method.
class TcpServer
{
public:
    TcpServer(int port, const char *name = "anonymous");
    ~TcpServer();

    int start(void);
    void stop(void);

    void send_clients(const void *data, int num_bytes);

    inline int stm32_fd(void)
    {
        return _stm32_fd;
    }

private:
    const char *_name;
    const int _listen_port;
    int _listen_fd;
    int _stm32_fd;

    std::list< TcpClient * > _clients;
    pthread_mutex_t _clients_mutex;

    // signal fds, used to wake up threads out of select
    int _listen_sfd;
    int _downstream_sfd;

    void thread_kill(pthread_t id);
    void thread_wait(pthread_t id);

    pthread_t _listen_id;
    void *listen_thread(void);
    // listen_entry is a pthread_create entry point
    static void *listen_entry(void *arg)
    {
        TcpServer *me = (TcpServer *)arg;
        return me->listen_thread();
    }

    pthread_t _downstream_id;
    void *downstream_thread(void);
    // downstream_entry is a pthread_create entry point
    static void *downstream_entry(void *arg)
    {
        TcpServer *me = (TcpServer *)arg;
        return me->downstream_thread();
    }

}; // TcpServer

#endif // _TCP_SERVER_H_
