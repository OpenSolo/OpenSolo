
#include <cstring>
#include <iostream>
#include <iomanip>

#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <unistd.h>
#include <stddef.h>
#include <stdlib.h>
#include <signal.h>
#include <syslog.h>
#include <unistd.h>
#include <sys/signalfd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include "util.h"
#include "mutex.h"
#include "ButtonFunctionCfg.h"
#include "SetShotInfo.h"
#include "TcpServer.h"

//#define NDEBUG
#include <assert.h>

using namespace std;

TcpClient::TcpClient(TcpServer *server, int fd_client)
    : _server(server), _fd_client(fd_client), _buf_bytes(0)
{
    int sockopt = 1;
    if (setsockopt(fd_client, IPPROTO_TCP, TCP_NODELAY, &sockopt, sizeof(sockopt)) != 0)
        syslog(LOG_ERR, "TcpClient: setsockopt TCP_NODELAY: %s", strerror(errno));
}

TcpClient::~TcpClient()
{
    close(_fd_client);
    _fd_client = -1;
    _server = NULL;
}

// Stuff that is always true
void TcpClient::invariant(void) const
{

    assert(_server != NULL);
    assert(_fd_client > 0);
    assert(_buf_bytes <= _buf_len);

} // TcpClient::invariant

int TcpClient::send_upstream(const void *data, int data_len)
{
    invariant();
    // MSG_NOSIGNAL means if the remote end closes the connection, we
    // don't want the SIGPIPE; just return from send with errno EPIPE
    // MSG_DONTWAIT means if the send would block, return EAGAIN or
    // EWOULDBLOCK instead. We will drop the message, but in our cases
    // (low rate small messages) this means there is something wrong
    // with the connection, and it will likely be closed anyway. The
    // absolute worst case is we lose a button event, which should not
    // cause any harm (as if the button were never pressed).
    return send(_fd_client, data, data_len, MSG_NOSIGNAL | MSG_DONTWAIT);
}

// Receive from fd, appending data to buffer.
// Check for complete message in buffer and send downstream if so.
// Return true if data received, false if client is gone.
bool TcpClient::do_recv(void)
{
    bool status;
    int res;

    invariant();

    res = recv(_fd_client, _buf + _buf_bytes, _buf_len - _buf_bytes, 0);
    // cout << "TcpClient:do_recv: recv returned " << res << endl;
    if (res > 0) {
        // new data appended to _buf
        _buf_bytes += res;

        // don't look at message header until we have enough for it
        while (_buf_bytes >= sizeof(SoloMessage::Hdr)) {
            SoloMessage::Hdr *hdr = (SoloMessage::Hdr *)_buf;

            // message is SoloMessage::Hdr plus payload
            unsigned msg_len = sizeof(SoloMessage::Hdr) + hdr->length;

            if (_buf_bytes < msg_len)
                break;

            // have a complete message; format and send downstream

            // cout << "TcpClient: have downstream message:" << endl;
            // cout << *hdr << endl;

            if (hdr->type == SoloMessage::Hdr::SET_BUTTON_STRING) {
                SoloMessage::SetButtonString *appMsg;

                appMsg = (SoloMessage::SetButtonString *)_buf;

                // struct ButtonFunctionCfgMsg does not include the descriptor
                // plant the message on top of a buffer big enough
                char stm32Buf[ButtonFunctionCfgMsg_BufSize];
                memset(stm32Buf, 0, sizeof(stm32Buf));
                ButtonFunctionCfgMsg *stm32Msg = (ButtonFunctionCfgMsg *)stm32Buf;

                stm32Msg->button_id = appMsg->button_id;
                stm32Msg->button_event = appMsg->button_event;
                stm32Msg->shot_id = appMsg->shot_id;
                stm32Msg->state = appMsg->state;
                // descriptor is everything after pad to the end
                int msgBodyLen = sizeof(SoloMessage::SetButtonString) - sizeof(SoloMessage::Hdr);
                int descLen = appMsg->length - msgBodyLen;
                // if too long, chop it off
                if (descLen > (ButtonFunctionCfgMsg::descriptor_max - 1))
                    descLen = (ButtonFunctionCfgMsg::descriptor_max - 1);
                memcpy(stm32Msg->descriptor, appMsg->descriptor, descLen);

                // cout << "TcpClient: sending downstream:" << endl;
                // cout << *stm32Msg << endl;

                // Send it to the downstream UDP port for this message.
                // (All downstream messages have to be sent via the stm32
                // downstream thread to avoid contention on the serial
                // interface.)
                struct sockaddr_in sa;
                memset((char *)&sa, 0, sizeof(sa));
                sa.sin_family = AF_INET;
                assert(ButtonFunctionCfg::udpPort != 0);
                sa.sin_port = htons(ButtonFunctionCfg::udpPort);
                sendto(_server->stm32_fd(), stm32Msg, sizeof(*stm32Msg) + descLen, 0,
                       (struct sockaddr *)&sa, sizeof(sa));
            } else if (hdr->type == SoloMessage::Hdr::SET_SHOT_STRING) {
                SoloMessage::SetShotString *appMsg;

                appMsg = (SoloMessage::SetShotString *)_buf;

                // struct SetShotInfoMsg does not include the descriptor
                // plant the message on top of a buffer big enough
                char stm32Buf[SetShotInfoMsg_BufSize];
                memset(stm32Buf, 0, sizeof(stm32Buf));
                SetShotInfoMsg *stm32Msg = (SetShotInfoMsg *)stm32Buf;

                // descriptor is everything to the end
                int msgBodyLen = sizeof(SoloMessage::SetShotString) - sizeof(SoloMessage::Hdr);
                int descLen = appMsg->length - msgBodyLen;
                // if too long, chop it off
                if (descLen > (SetShotInfoMsg::descriptor_max - 1))
                    descLen = (SetShotInfoMsg::descriptor_max - 1);
                memcpy(stm32Msg->descriptor, appMsg->descriptor, descLen);

                // cout << "TcpClient: sending downstream:" << endl;
                // cout << *stm32Msg << endl;

                // Send it to the downstream UDP port for this message.
                // (All downstream messages have to be sent via the stm32
                // downstream thread to avoid contention on the serial
                // interface.)
                struct sockaddr_in sa;
                memset((char *)&sa, 0, sizeof(sa));
                sa.sin_family = AF_INET;
                assert(SetShotInfo::udpPort != 0);
                sa.sin_port = htons(SetShotInfo::udpPort);
                sendto(_server->stm32_fd(), stm32Msg, sizeof(*stm32Msg) + descLen, 0,
                       (struct sockaddr *)&sa, sizeof(sa));
            }

            // done with the message at the start of the buffer;
            // copy any unused data after it back to the start
            _buf_bytes -= msg_len; // how much is left over
            memmove(_buf, _buf + msg_len, _buf_bytes);

        } // while (_buf_bytes...)

        status = true;

    } else // res <= 0
    {
        status = false;
    }

    invariant();

    return status;

} // TcpClient::do_recv

// Constructor initializes object; call start method to open socket and start
// threads.
TcpServer::TcpServer(int port, const char *name)
    : _name(name), _listen_port(port), _listen_fd(-1), _stm32_fd(-1),
      // _clients
      // _clients_mutex
      _listen_sfd(-1), _downstream_sfd(-1)
// _listen_id
// _downstream_id
{
}

TcpServer::~TcpServer()
{
}

int TcpServer::start(void)
{
    int sockopt;
    struct sockaddr_in sa;
    sigset_t mask;
    int res;

    // initialize clients list mutex
    res = mutex_init(&_clients_mutex);
    if (res != 0) {
        syslog(LOG_ERR, "mutex_init: %d", res);
        goto start_exit_0;
    }

    // create listening socket
    _listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (_listen_fd < 0) {
        syslog(LOG_ERR, "socket: %s", strerror(errno));
        goto start_exit_1;
    }

    // non-blocking - this handles the race where a client tries to connect,
    // the select() activates, then the client is gone before the accept.
    if (fcntl(_listen_fd, F_SETFL, O_NONBLOCK) != 0) {
        syslog(LOG_ERR, "fcntl: %s", strerror(errno));
        goto start_exit_2;
    }

    // allow re-binding to our port in case of restart
    sockopt = 1;
    if (setsockopt(_listen_fd, SOL_SOCKET, SO_REUSEADDR, &sockopt, sizeof(sockopt)) != 0) {
        syslog(LOG_ERR, "setsockopt: %s", strerror(errno));
        goto start_exit_2;
    }

    // bind to port where we listen for connections
    memset(&sa, 0, sizeof(sa));
    sa.sin_family = AF_INET;
    sa.sin_port = htons(_listen_port);
    sa.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bind(_listen_fd, (struct sockaddr *)&sa, sizeof(sa)) == -1) {
        syslog(LOG_ERR, "bind: %s", strerror(errno));
        goto start_exit_2;
    }

    // listen for connections
    if (listen(_listen_fd, 10) == -1) {
        syslog(LOG_ERR, "listen: %s", strerror(errno));
        goto start_exit_2;
    }

    res = sigemptyset(&mask);
    assert(res == 0); // invalid arguments
    res = sigaddset(&mask, SIGHUP);
    assert(res == 0); // invalid arguments
    res = sigaddset(&mask, SIGQUIT);
    assert(res == 0); // invalid arguments
    res = pthread_sigmask(SIG_BLOCK, &mask, NULL);
    assert(res == 0); // invalid arguments

    // create listen signal fd
    res = sigemptyset(&mask);
    assert(res == 0); // invalid arguments
    res = sigaddset(&mask, SIGQUIT);
    assert(res == 0); // invalid arguments
    _listen_sfd = signalfd(-1, &mask, 0);
    if (_listen_sfd < 0) {
        syslog(LOG_ERR, "signalfd: %s", strerror(errno));
        goto start_exit_2;
    }

    // create downstream thread signal fd
    res = sigemptyset(&mask);
    assert(res == 0); // invalid arguments
    res = sigaddset(&mask, SIGHUP);
    assert(res == 0); // invalid arguments
    res = sigaddset(&mask, SIGQUIT);
    assert(res == 0); // invalid arguments
    _downstream_sfd = signalfd(-1, &mask, 0);
    if (_downstream_sfd < 0) {
        syslog(LOG_ERR, "signalfd: %s", strerror(errno));
        goto start_exit_3;
    }

    // UDP socket that will be used by all clients to send messages to an
    // stm32 downstream port
    _stm32_fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (_stm32_fd < 0) {
        syslog(LOG_ERR, "socket: %s", strerror(errno));
        goto start_exit_4;
    }

    // bind to any IP, any port */
    memset((char *)&sa, 0, sizeof(sa));
    sa.sin_family = AF_INET;
    sa.sin_port = htons(0);
    sa.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bind(_stm32_fd, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
        syslog(LOG_ERR, "bind: %s", strerror(errno));
        goto start_exit_5;
    }

    // start listen_thread
    if (pthread_create(&_listen_id, NULL, &TcpServer::listen_entry, this) != 0) {
        syslog(LOG_ERR, "pthread_create: %s", strerror(errno));
        goto start_exit_5;
    }

    if (pthread_setname_np(_listen_id, "stm32_listen") != 0) {
        syslog(LOG_ERR, "pthread_setname_np: %s", strerror(errno));
        goto start_exit_6;
    }

    // start downstream_thread
    if (pthread_create(&_downstream_id, NULL, &TcpServer::downstream_entry, this) != 0) {
        syslog(LOG_ERR, "pthread_create: %s", strerror(errno));
        goto start_exit_6;
    }

    if (pthread_setname_np(_downstream_id, "stm32_recv") != 0) {
        syslog(LOG_ERR, "pthread_setname_np: %s", strerror(errno));
        goto start_exit_7;
    }

    return 0;

// WARNING: Error conditions are not tested.
//          Errors here are probably fatal to the system.

start_exit_7:
    thread_kill(_downstream_id);
    thread_wait(_downstream_id);

start_exit_6:
    thread_kill(_listen_id);
    thread_wait(_listen_id);

start_exit_5:
    close(_stm32_fd);
    _stm32_fd = -1;

start_exit_4:
    close(_downstream_sfd);
    _downstream_sfd = -1;

start_exit_3:
    close(_listen_sfd);
    _listen_sfd = -1;

start_exit_2:
    close(_listen_fd);
    _listen_fd = -1;

start_exit_1:
    (void)pthread_mutex_destroy(&_clients_mutex);

start_exit_0:
    return -1;

} // TcpServer::start

// WARNING: Stopping is not tested. Normal operation is to start and run
//          forever, or stop by killing the entire process.
void TcpServer::stop(void)
{

    thread_kill(_downstream_id);
    thread_kill(_listen_id);

    thread_wait(_downstream_id);
    thread_wait(_listen_id);

    close(_stm32_fd);
    _stm32_fd = -1;

    close(_downstream_sfd);
    _downstream_sfd = -1;

    close(_listen_sfd);
    _listen_sfd = -1;

    close(_listen_fd);
    _listen_fd = -1;

    (void)pthread_mutex_destroy(&_clients_mutex);

} // TcpServer::stop

// Tell a thread to exit. We send it SIGQUIT; it is expected to be waiting
// on a signalfd where this will arrive, and know that SIGQUIT means quit.
void TcpServer::thread_kill(pthread_t id)
{
    // SIGQUIT means quit
    if (pthread_kill(id, SIGQUIT) != 0)
        syslog(LOG_ERR, "pthread_kill: %s", strerror(errno));
}

// Wait for a thread to exit. It should have already received the SIGQUIT, so
// should soon get it and cleanly exit. If it does not, we attempt to kill it.
void TcpServer::thread_wait(pthread_t id)
{
    // The timeout to pthread_timedjoin_np() is an absolute time, which
    // can break if the time is changed while waiting. Instead we poll
    // pthread_tryjoin_np() few times.

    // wait up to 10 msec
    for (int try_num = 0; try_num < 10; try_num++) {
        if (pthread_tryjoin_np(id, NULL) == 0)
            return;
        usleep(1000); // 1 msec
    }

    // the join never succeeded; try canceling
    syslog(LOG_ERR, "thread_wait: canceling thread");
    pthread_cancel(id);
    // thread cleans up asynchronously
    usleep(10000); // 10 msec

} // TcpServer::thread_wait

// Listening thread.
// Create a socket and listen for connections. When a connection is received,
// the client is added to the list of clients. The list of clients determines
// what is monitored for incoming data (select, in downstream_thread) and who
// gets all upstream messages (send_clients method).
void *TcpServer::listen_thread(void)
{
    int nfds;
    fd_set rfds;

    syslog(LOG_INFO, "%s listen_thread: starting", _name);

    while (true) {

        // Select waits for either an incoming connection on _listen_fd or a
        // signal on _listen_sfd.
        FD_ZERO(&rfds);
        nfds = 0;

        FD_SET(_listen_sfd, &rfds);
        if (nfds <= _listen_sfd)
            nfds = _listen_sfd + 1;

        FD_SET(_listen_fd, &rfds);
        if (nfds <= _listen_fd)
            nfds = _listen_fd + 1;

        int res = select(nfds, &rfds, NULL, NULL, NULL);

        if (res > 0) {

            // got a signal?
            if (FD_ISSET(_listen_sfd, &rfds)) {
                // clear out the signal
                signalfd_siginfo si;
                if (read(_listen_sfd, &si, sizeof(si)) != sizeof(si)) {
                    syslog(LOG_ERR, "%s listen_thread: reading siginfo", _name);
                    break; // while (true)
                } else if (si.ssi_signo == SIGQUIT) {
                    // SIGQUIT means quit
                    break; // while (true)
                } else {
                    // mystery signal
                    syslog(LOG_ERR, "%s listen_thread: unexpected signal", _name);
                }
            }

            // got a connection?
            if (FD_ISSET(_listen_fd, &rfds)) {
                // Incoming client - this will not block (the socket is
                // nonblocking). If the client is no longer trying to
                // connect, we get an invalid fd_client (immediately) and
                // handle that.
                struct sockaddr_in sa;
                memset((char *)&sa, 0, sizeof(sa));
                socklen_t sa_len = sizeof(sa);
                int fd_client = accept(_listen_fd, (struct sockaddr *)&sa, &sa_len);
                if (fd_client < 0) {
                    // client tried to connect then changed its mind
                    syslog(LOG_ERR, "accept: %s", strerror(errno));
                    usleep(10000); // 10ms
                    continue;
                }

                if (sa.sin_family == AF_INET)
                    syslog(LOG_INFO, "%s listen_thread: adding client %d at %s:%u", _name,
                           fd_client, inet_ntoa(sa.sin_addr), ntohs(sa.sin_port));
                else
                    syslog(LOG_INFO, "%s listen_thread: adding client %d", _name, fd_client);

                // Add new client to the list of clients that gets everything
                // via send_clients(). Clients are removed from this list when
                // send_clients() determines that the connection is dead.
                TcpClient *new_client = new TcpClient(this, fd_client);
                pthread_mutex_lock(&_clients_mutex);
                _clients.push_back(new_client);
                pthread_mutex_unlock(&_clients_mutex);

                // Knock downstream_thread out of its select, so it will
                // rebuild the fdset with the new client (we use SIGHUP).
                if (pthread_kill(_downstream_id, SIGHUP) != 0)
                    syslog(LOG_ERR, "pthread_kill: %s", strerror(errno));
            }
        } else {
            syslog(LOG_ERR, "%s listen_thread: select: %s", _name, strerror(errno));
        }

    } // while (true)

    syslog(LOG_INFO, "%s listen_thread: exiting", _name);

    return NULL;

} // TcpServer::listen_thread

// Downstream thread.
// Select on clients, waiting for data to arrive for one.
// Read data, letting each client accumulate data and send a message
// downstream when it has one.
void *TcpServer::downstream_thread(void)
{
    int nfds;
    fd_set rfds;
    list< TcpClient * >::iterator it, next;
    int res;
    int fd;

    syslog(LOG_INFO, "%s downstream_thread: starting", _name);

    while (true) {

        // build set of fds to wait on
        FD_ZERO(&rfds);
        nfds = 0;

        // signal fd is always in the set
        fd = _downstream_sfd;
        FD_SET(fd, &rfds);
        if (nfds <= fd)
            nfds = fd + 1;

        // add all the clients to the set
        pthread_mutex_lock(&_clients_mutex);
        for (it = _clients.begin(); it != _clients.end(); it++) {
            fd = (*it)->fd_client();
            FD_SET(fd, &rfds);
            if (nfds <= fd)
                nfds = fd + 1;
        }
        // unsigned num_clients = _clients.size();
        pthread_mutex_unlock(&_clients_mutex);

        // wait for something on any of them (or a signal)
        res = select(nfds, &rfds, NULL, NULL, NULL);

        if (res > 0) {

            // signal?
            if (FD_ISSET(_downstream_sfd, &rfds)) {
                signalfd_siginfo si;
                if (read(_downstream_sfd, &si, sizeof(si)) != sizeof(si)) {
                    syslog(LOG_ERR, "%s downstream_thread: reading siginfo", _name);
                    break; // while (true)
                } else if (si.ssi_signo == SIGQUIT) {
                    // SIGQUIT means quit
                    break; // while (true)
                } else if (si.ssi_signo == SIGHUP) {
                    // SIGHUP means recreate the fdset we're waiting on
                } else {
                    // mystery signal
                    syslog(LOG_ERR, "%s downstream_thread: unexpected signal", _name);
                }
            }

            // data from any client?
            pthread_mutex_lock(&_clients_mutex);
            for (it = _clients.begin(); it != _clients.end(); it = next) {
                next = it;
                next++;
                TcpClient *c = *it;
                if (FD_ISSET(c->fd_client(), &rfds)) {
                    if (!c->do_recv()) {
                        syslog(LOG_INFO, "%s downstream_thread: deleting client %d", _name,
                               c->fd_client());
                        _clients.erase(it);
                        delete c;
                    }
                }
            }
            pthread_mutex_unlock(&_clients_mutex);
        } else // res <= 0
        {
            syslog(LOG_ERR, "%s downstream_thread: select returned %d", _name, res);
        }

    } // while (true)

    syslog(LOG_INFO, "%s downstream_thread: exiting", _name);

    return NULL;

} // TcpServer::downstream_thread

// Send data to all clients.
// The supplied data is sent to all clients in the client list, i.e. all
// clients that have connected to the server.
void TcpServer::send_clients(const void *data, int data_len)
{
    list< TcpClient * >::iterator it;

    pthread_mutex_lock(&_clients_mutex);

    for (it = _clients.begin(); it != _clients.end(); it++) {
        uint64_t t0_us = clock_gettime_us(CLOCK_MONOTONIC);
        int rc = (*it)->send_upstream(data, data_len);
        uint64_t t1_us = clock_gettime_us(CLOCK_MONOTONIC);
        if (rc != data_len) {
            // The client might be gone; downstream thread detects that
            // and deletes it
            syslog(LOG_ERR, "%s send_clients: %s", _name, strerror(errno));
        }
        unsigned delay_us = t1_us - t0_us;
        if (delay_us > 10000) {
            // Looking for trouble - when does send_upstream block?
            syslog(LOG_ERR, "%s send_clients: send_upstream took %u usec", _name, delay_us);
        }
    }

    pthread_mutex_unlock(&_clients_mutex);

} // TcpServer::send_clients
