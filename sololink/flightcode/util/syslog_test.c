#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <syslog.h>
#include <unistd.h>
#include "syslog_test.h"

int syslog_test(void)
{
    int status = 0;

    int fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (fd < 0) {
        perror("syslog_test: socket");
        status = 1;
        goto syslog_test_exit_0;
    }

    if (fcntl(fd, F_SETFL, O_NONBLOCK) != 0) {
        perror("syslog_test: fcntl");
        status = 1;
        goto syslog_test_exit_1;
    }

    // remove it if already there; ignore error
    unlink(SYSLOG_SOCK_NAME);

    struct sockaddr_un sa_un;
    memset(&sa_un, 0, sizeof(sa_un));
    sa_un.sun_family = AF_UNIX;
    strncpy(sa_un.sun_path, SYSLOG_SOCK_NAME, sizeof(sa_un.sun_path) - 1);
    if (bind(fd, (struct sockaddr *)&sa_un, sizeof(sa_un)) != 0) {
        perror("syslog_test: bind");
        status = 1;
        goto syslog_test_exit_1;
    }

    openlog("test", 0, LOG_LOCAL0);

    char msg[256];

    // should be nothing there
    if (recv(fd, msg, sizeof(msg), 0) != -1 || (errno != EAGAIN && errno != EWOULDBLOCK)) {
        fprintf(stderr, "syslog_test: unexpected message\n");
        status = 1;
        goto syslog_test_exit_2;
    }

    syslog(LOG_INFO, "hello!");

    // should be a message
    if (recv(fd, msg, sizeof(msg), 0) <= 0) {
        fprintf(stderr, "syslog_test: expected message (%s)\n", strerror(errno));
        status = 1;
        goto syslog_test_exit_2;
    }

    // should be nothing there
    if (recv(fd, msg, sizeof(msg), 0) != -1 || (errno != EAGAIN && errno != EWOULDBLOCK)) {
        fprintf(stderr, "syslog_test: unexpected message\n");
        status = 1;
        goto syslog_test_exit_2;
    }

    // Test dropping messages: Send more than can be queued, then verify we
    // get fewer than that back. On the next send, a "drop" message should be
    // inserted, so verify that after clearing out the queue, one more message
    // causes two to be received.

    // fill it up such that it drops messages
    int msgs_sent = 200;
    int n;
    for (n = 0; n < msgs_sent; n++)
        syslog(LOG_INFO, "hello!");

    // should get fewer than that back
    n = 0;
    int r;
    while ((r = recv(fd, msg, sizeof(msg), 0)) > 0) {
        // msg[r] = '\0'; // msg is not '\0' terminated
        // printf("%s\n", msg);
        n++;
    }
    if (n >= msgs_sent) {
        // this might mean /proc/sys/net/unix/max_dgram_qlen > msgs_sent
        fprintf(stderr, "syslog_test: received too many messages\n");
        status = 1;
        goto syslog_test_exit_2;
    }

    // on the next one, we get the drop message then the new message
    syslog(LOG_INFO, "hello!");
    n = 0;
    while ((r = recv(fd, msg, sizeof(msg), 0)) > 0) {
        // msg[r] = '\0'; // msg is not '\0' terminated
        // printf("%s\n", msg);
        n++;
    }
    if (n != 2) {
        fprintf(stderr, "syslog_test: did not get drop message\n");
        status = 1;
        goto syslog_test_exit_2;
    }

    // Verify overflowing the maximum message length

    for (n = 0; n < SYSLOG_MSG_MAX; n++) {
        // create a string of length n
        memset(msg, 'X', n);
        msg[n] = '\0';
        syslog(LOG_INFO, msg);
        memset(msg, 0, sizeof(msg));
        if ((r = recv(fd, msg, sizeof(msg), 0)) <= 0) {
            fprintf(stderr, "syslog_test: expected message (%s)\n", strerror(errno));
            status = 1;
            goto syslog_test_exit_2;
        }
        msg[r] = '\0'; // msg is not '\0' terminated
        // syslog.c was compiled with SYSLOG_MSG_MAX, so the total length of
        // the returned message should be less than that
        if (strlen(msg) >= (SYSLOG_MSG_MAX - 1)) {
            fprintf(stderr, "syslog_test: message overflow\n");
            status = 1;
            goto syslog_test_exit_2;
        }
        // printf("%s\n", msg);
        // again, with formatting that would overrun
        memset(msg, ' ', n);
        msg[n] = '%';
        msg[n + 1] = 'd';
        msg[n + 2] = '\0';
        syslog(LOG_INFO, msg, 1234);
        memset(msg, 0, sizeof(msg));
        if ((r = recv(fd, msg, sizeof(msg), 0)) <= 0) {
            fprintf(stderr, "syslog_test: expected message (%s)\n", strerror(errno));
            status = 1;
            goto syslog_test_exit_2;
        }
        msg[r] = '\0'; // msg is not '\0' terminated
        // syslog.c was compiled with SYSLOG_MSG_MAX, so the total length of
        // the returned message should be less than that
        if (strlen(msg) >= (SYSLOG_MSG_MAX - 1)) {
            fprintf(stderr, "syslog_test: message overflow\n");
            status = 1;
            goto syslog_test_exit_2;
        }
        // printf("%s\n", msg);
    }

syslog_test_exit_2:
    closelog();
    unlink(SYSLOG_SOCK_NAME);

syslog_test_exit_1:
    close(fd);

syslog_test_exit_0:
    return status;

} // syslog_test
