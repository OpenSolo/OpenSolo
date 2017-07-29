
#include <syslog.h>
#include <errno.h>
#include <pthread.h>
#include <unistd.h>
#include <stddef.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <iostream>
#include "util.h"
#include "mutex.h"
#include "Commander.h"

using namespace std;


// Constructor creates and opens the command socket, then starts the command
// thread.
Commander::Commander(const char *sock_name)
{

    if (strlen(sock_name) >= sizeof(sa.sun_path)) {
        cerr << "ERROR: command socket name too long" << endl;
        return;
    }

    // If there is something already there with the socket name, it is deleted.
    // If not, unlink() fails (and we don't care).
    (void)unlink(sock_name);

    // create command socket
    _fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (_fd < 0) {
        cerr << "ERROR creating command socket" << endl;
        return;
    }

    // bind command socket to address
    memset(&sa, 0, sizeof(sa));
    sa.sun_family = AF_UNIX;
    strncpy(sa.sun_path, sock_name, sizeof(sa.sun_path) - 1);
    if (bind(_fd, (struct sockaddr *)&sa, sizeof(sa)) != 0) {
        cerr << "ERROR binding command socket" << endl;
        close(_fd);
        _fd = -1;
        return;
    }

    // initialize clients list mutex
    if (mutex_init(&clients_mutex) != 0) {
        cerr << "ERROR initializing clients mutex" << endl;
        close(_fd);
        _fd = -1;
        return;
    }

    // start command thread
    if (pthread_create(&thread_id, NULL, &Commander::command_entry, this) != 0) {
        cerr << "ERROR starting command thread" << endl;
        close(_fd);
        _fd = -1;
        return;
    }

} // Commander::Commander


// Destructor sends a QUIT command to the command thread, waits for it to exit,
// then closes the command socket.
Commander::~Commander()
{
    const char *quit = "QUIT";
    ssize_t quit_len = strlen(quit);

    if (sendto(_fd, quit, quit_len, 0,
               (const struct sockaddr *)&sa, sizeof(sa)) != quit_len) {
        cerr << "~Commander: ERROR returned from sendto" << endl;
    }

    if (pthread_join(thread_id, NULL) != 0) {
        cerr << "ERROR returned from pthread_join" << endl;
    }

    close(_fd);

} // Commander::~Commander()


// Commander processing thread.
// Wait for a command on the command socket, and process each. A QUIT command
// causes the loop to exit.
void *Commander::command_thread(void)
{
    bool quit = false;
    char buf[MAX_CMD_LEN];
    int nb;
    struct sockaddr_storage src_storage;
    struct sockaddr *src = (struct sockaddr *)&src_storage;
    socklen_t src_len;
    char *token;
    const char *delims;

    //cout << "command_thread: running" << endl;

    while (!quit) {

        src_len = sizeof(struct sockaddr_storage);
        memset(src, 0, src_len);
        memset(&buf, 0, sizeof(buf));
        nb = recvfrom(_fd, buf, MAX_CMD_LEN, 0, src, &src_len);
        if (nb < 0) {
            cerr << "ERROR returned from recvfrom" << endl;
            continue;
        }

        delims = " \t\r\n";
        token = strtok(buf, delims);

        if (token == NULL) {
            // no command, like ping
            handle_ping(src, src_len);
        } else if (strcasecmp(token, "ATTACH") == 0) {
            token = strtok(NULL, delims);
            handle_attach(src, src_len, token, true);
        } else if (strcasecmp(token, "DETACH") == 0) {
            token = strtok(NULL, delims);
            handle_attach(src, src_len, token, false);
        } else if (strcasecmp(token, "PING") == 0) {
            handle_ping(src, src_len);
        } else if (strcasecmp(token, "LIST") == 0) {
            handle_list(src, src_len);
        } else if (strcasecmp(token, "QUIT") == 0) {
            quit = true;
        } else {
            cerr << "Unknown command: " << buf << endl;
        }

    } // while (!quit)

    //cout << "command_thread: exiting" << endl;

    return NULL;

} // Commander::command_thread


// Send data to all clients.
// The supplied data is sent to all clients in the client list, i.e. all
// clients for which an ATTACH command has been sent. Unix domain datagram
// sockets are reliable, which means a write will block if the reader is
// not fast enough. We can't let an RC packet consumer block the UDP thread,
// so the sendto is done nonblocking. This means it is up to the reader to
// read fast enough to keep from dropping packets.
void Commander::send_clients(const void *data, int data_len)
{
    static unsigned drops = 0;
    vector<SockAddr>::iterator it;

    pthread_mutex_lock(&clients_mutex);

    for (it = clients.begin(); it != clients.end(); it++) {
        if (sendto(_fd, data, data_len, MSG_DONTWAIT,
                   it->sockaddr(), it->socklen()) != data_len) {
            //cerr << "send_clients: \"" << strerror(errno)
            //     << "\" sending to " << *it << endl;
            drops++;
        } else {
            //cout << "send_clients: sent to " << *it << endl;
            if (drops > 0) {
                syslog(LOG_INFO, "cmd: dropped %d packets", drops);
                drops = 0;
            }
        }
    }

    pthread_mutex_unlock(&clients_mutex);

} // Commander::send_clients


// Handle ATTACH or DETACH command.
//
// ATTACH/DETACH takes and optional argument indicating the client to ATTACH or
// detach. If no argument is given, the sender of the command is used. If an
// argument is given, it should be an AF_UNIX socket (support for UDP sockets
// could be added).
//
// If the command was ATTACH and the client is not in the list of clients, add
// it to the list. If the command was DETACH and the client is in the list of
// clients, remove it from the list.
void Commander::handle_attach(const struct sockaddr *src_addr,
                              socklen_t src_addr_len, const char *client,
                              bool attach)
{
    struct sockaddr_storage client_addr;
    socklen_t client_addr_len;

    memset(&client_addr, 0, sizeof(client_addr));
    client_addr_len = 0;

    if (client == NULL) {
        // no client given - use source of request as client
        memcpy(&client_addr, src_addr, src_addr_len);
        client_addr_len = src_addr_len;
    } else {
        // client should be a unix socket name
        // (support for IP:port could be added)
        struct stat stat_buf;
        if (stat(client, &stat_buf) != 0) {
            cerr << "handle_attach: ERROR: \"" << client
                 << "\" does not exist" << endl;
            return;
        }
        if (!S_ISSOCK(stat_buf.st_mode)) {
            cerr << "handle_attach: ERROR: \"" << client
                 << "\" exists but is not a socket" << endl;
            return;
        }
        struct sockaddr_un *c_un = (struct sockaddr_un *)&client_addr;
        int maxlen = sizeof(c_un->sun_path);
        c_un->sun_family = AF_UNIX;
        strncpy(c_un->sun_path, client, maxlen - 1);
        c_un->sun_path[maxlen - 1] = '\0';
        client_addr_len = offsetof(struct sockaddr_un, sun_path)
                        + strlen(c_un->sun_path) + 1; // man 7 unix
    }

    SockAddr s((struct sockaddr *)&client_addr, client_addr_len);
    bool found = false;
    vector<SockAddr>::iterator it;

    pthread_mutex_lock(&clients_mutex);

    for (it = clients.begin(); it != clients.end(); it++) {
        if (*it == s) { // == overloaded
            found = true;
            break;
        }
    }

    if (attach && !found) {
        // attach new client
        clients.push_back(s);
    } else if (!attach && found) {
        // detach existing client
        clients.erase(it);
    }

    pthread_mutex_unlock(&clients_mutex);

    send_response(src_addr, src_addr_len, "OK\n");

} // Commander::handle_attach


// Handle LIST command.
// Response to LIST is attached clients, one per line, then "OK\n".
void Commander::handle_list(const struct sockaddr *src_addr,
                          socklen_t src_addr_len)
{
    string response;

    pthread_mutex_lock(&clients_mutex);

    vector<SockAddr>::iterator it;
    for (it = clients.begin(); it != clients.end(); it++)
        response = response + it->to_string() + "\n";

    pthread_mutex_unlock(&clients_mutex);

    response += "OK\n";

    send_response(src_addr, src_addr_len, response.c_str());

} // Commander::handle_list


// Handle PING command.
// Response to PING is simply "OK\n".
void Commander::handle_ping(const struct sockaddr *src_addr,
                          socklen_t src_addr_len)
{
    send_response(src_addr, src_addr_len, "OK\n");
}


// Send a reponse to a client command.
void Commander::send_response(const struct sockaddr *src_addr,
                            socklen_t src_addr_len,
                            const char *response, ssize_t response_len)
{
    if (response_len == -1)
        response_len = strlen(response);

    if (sendto(_fd, response, response_len, 0, src_addr, src_addr_len)
        != response_len) {
        cerr << "send_response: ERROR returned from sendto" << endl;
            cerr << "send_response: \"" << strerror(errno)
                 << "\" sending to " << *src_addr << endl;
    } else {
        //cout << "send_response: OK" << endl;
    }

} // Commander::send_response


// print SockAddr to stream (human-readable)
ostream& operator<<(ostream& os, const SockAddr& sock)
{
    sa_family_t family = sock.su.sa.sa_family;

    if (family == AF_UNIX) {
        const struct sockaddr_un *un = &sock.su.un;
        os << "AF_UNIX: " << un->sun_path;
    } else if (family == AF_INET) {
        const struct sockaddr_in *in = &sock.su.in;
        os << "AF_INET: " << inet_ntoa(in->sin_addr) << ":"
            << ntohs(in->sin_port);
    } else {
        os << "sa_family=" << family;
    }
    return os;
}


// print sockaddr/sockaddr_un/sockaddr_in to stream (human-readable)
ostream& operator<<(ostream& os, const struct sockaddr& sa)
{
    sa_family_t family = sa.sa_family;

    if (family == AF_UNIX) {
        const struct sockaddr_un *un = (const struct sockaddr_un *)&sa;
        os << "AF_UNIX: " << un->sun_path;
    } else if (family == AF_INET) {
        const struct sockaddr_in *in = (const struct sockaddr_in *)&sa;
        os << "AF_INET: " << inet_ntoa(in->sin_addr) << ":"
            << ntohs(in->sin_port);
    } else {
        os << "sa_family=" << family;
    }
    return os;
}


#if 0

int main(int argc, char *argv[])
{
    Commander *ss;

    cout << "main: creating command object" << endl;
    ss = new Commander(argv[1]);

    for (int i = 0; i < 4; i++) {
        ss->send_clients("hello\n", 6);
        sleep(5);
    }

    cout << "main: deleting command object" << endl;
    delete ss;

    cout << "main: exiting" << endl;

} // main

#endif 
