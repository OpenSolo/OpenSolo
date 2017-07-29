#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <iostream>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netdb.h>
#include <arpa/inet.h>

using namespace std;

/***********************************************************************
UDP macros
***********************************************************************/
#define REMOTE_UDP_PORT 14560
#define LOCAL_UDP_PORT 14550
#define NUM_CHANNELS 8

int main(void)
{
    int sock_fd;
    struct sockaddr_in myaddr;
    struct sockaddr_in remaddr; /* server address */
    int slen = sizeof(remaddr);
    socklen_t addrlen = sizeof(remaddr); /* length of addresses */
    char *server = "127.0.0.1";          /* change this to use a different server */
    char buf[512];
    int recvlen;

    if ((sock_fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        cerr << "cannot create socket" << endl;
        return 0;
    }

    memset((char *)&myaddr, 0, sizeof(myaddr));
    myaddr.sin_family = AF_INET;
    myaddr.sin_addr.s_addr = htonl(INADDR_ANY);
    myaddr.sin_port = htons(LOCAL_UDP_PORT);

    if (bind(sock_fd, (struct sockaddr *)&myaddr, sizeof(myaddr)) < 0) {
        perror("bind failed");
        return 0;
    }

    fcntl(sock_fd, F_SETFL, O_NONBLOCK);

    memset((char *)&remaddr, 0, sizeof(remaddr));
    remaddr.sin_family = AF_INET;
    remaddr.sin_port = htons(REMOTE_UDP_PORT);
    if (inet_aton(server, &remaddr.sin_addr) == 0) {
        cerr << "inet_aton() failed" << endl;
        return 0;
    }

    memset(buf, 0, sizeof(buf));
    sprintf(buf, "Hello!\n");
    sendto(sock_fd, buf, strlen(buf), 0, (struct sockaddr *)&remaddr, slen);

    while (true) {
        // See if theres anything to receive
        memset(buf, 0, sizeof(buf));
        recvlen = recvfrom(sock_fd, buf, 512, 0, (struct sockaddr *)&remaddr, &addrlen);

        if (recvlen > 0)
            cout << "Got " << recvlen << " bytes" << endl;
    }

    close(sock_fd);
    return 1;
}
