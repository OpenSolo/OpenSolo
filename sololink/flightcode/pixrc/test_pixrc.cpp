#include <stdlib.h>
#include <string.h>
#include <iostream>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netdb.h>
#include <time.h>
#include <arpa/inet.h>
#include "util.h"

using namespace std;

/***********************************************************************
UDP macros
***********************************************************************/
#define UDP_PORT 5005
#define NUM_CHANNELS 8

int main(void)
{
    int sock_fd;
    struct sockaddr_in remaddr; /* server address */
    int slen = sizeof(remaddr);
    char *server = "10.1.1.10";
    // char *server = "127.0.0.1";	/* change this to use a different server */
    uint16_t channelVals[NUM_CHANNELS] = {1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500};
    uint16_t sequence = 0;
    uint64_t timestamp = 0;
    uint64_t last_us, now_us;
    char buf[512];
    int delta;
    struct sched_param param;

    srand(time(NULL));

    if ((sock_fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        cerr << "cannot create socket" << endl;
        return 0;
    }

    int tos_local = 0xFF;
    setsockopt(sock_fd, IPPROTO_IP, IP_TOS, &tos_local, sizeof(tos_local));

    memset((char *)&remaddr, 0, sizeof(remaddr));
    remaddr.sin_family = AF_INET;
    remaddr.sin_port = htons(UDP_PORT);
    if (inet_aton(server, &remaddr.sin_addr) == 0) {
        cerr << "inet_aton() failed" << endl;
        return 0;
    }

    memset(&param, 0, sizeof(param));
    param.sched_priority = sched_get_priority_max(SCHED_FIFO);
    pthread_setschedparam(0, SCHED_FIFO, &param);

    last_us = clock_gettime_us(CLOCK_MONOTONIC);

    while (true) {
        now_us = clock_gettime_us(CLOCK_MONOTONIC);
        delta = now_us - last_us;
        if (delta > 21000)
            cout << "Slow! " << delta << "us" << endl;
        last_us = now_us;
        memset(buf, 0, sizeof(buf));
        memcpy(buf, &timestamp, 8);
        memcpy(&buf[8], &sequence, 2);
        memcpy(&buf[10], channelVals, 16);

        /* now let's send the messages */
        if (sendto(sock_fd, buf, 26, 0, (struct sockaddr *)&remaddr, slen) == -1) {
            cerr << "sendto failed" << endl;
            return 0;
        }

        timestamp += 1;
        sequence += 1;

        uint64_t delay = 20000; // + (rand() % 10000 - 5000);
        usleep(delay);
    }

    close(sock_fd);
    return 1;
}
