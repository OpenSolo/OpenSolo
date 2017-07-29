
#include <linux/watchdog.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>

/* start, kick, or cancel the watchdog */

#define DEV_NAME "/dev/watchdog"

static int usage(void)
{
    printf("usage: wdog -t <T>    set new timeout\n");
    printf("       wdog -k        kick watchdog\n");
    printf("       wdog -c        cancel watchdog\n");
    return 1;
}

static int set_timeout(int t)
{
    int status = 0;
    int fd = open(DEV_NAME, O_RDWR);
    if (fd < 0) {
        fprintf(stderr, "wdog: ERROR opening %s\n", DEV_NAME);
        status = 1;
    } else {
        if (ioctl(fd, WDIOC_SETTIMEOUT, &t) != 0) {
            fprintf(stderr, "wdog: ERROR setting watchdog\n");
            status = 1;
        }
        close(fd);
    }
    return status;
}

static int cancel(void)
{
    int status = 0;
    int fd = open(DEV_NAME, O_RDWR);
    if (fd < 0) {
        fprintf(stderr, "wdog: ERROR opening %s\n", DEV_NAME);
        status = 1;
    } else {
        if (write(fd, "V", 1) != 1) {
            fprintf(stderr, "wdog: ERROR canceling watchdog\n");
            status = 1;
        }
        close(fd);
    }
    return status;
}

static int kick(void)
{
    int status = 0;
    int fd = open(DEV_NAME, O_RDWR);
    if (fd < 0) {
        fprintf(stderr, "wdog: ERROR opening %s\n", DEV_NAME);
        status = 1;
    } else {
        if (ioctl(fd, WDIOC_KEEPALIVE, 0) != 0) {
            fprintf(stderr, "wdog: ERROR kicking watchdog\n");
            status = 1;
        }
        close(fd);
    }
    return status;
}

int main(int argc, char *argv[])
{
    int status;

    if (argc == 2) {
        if (strcmp(argv[1], "-c") == 0) {
            status = cancel();
        } else if (strcmp(argv[1], "-k") == 0) {
            status = kick();
        } else {
            status = usage();
        }
    } else if (argc == 3) {
        if (strcmp(argv[1], "-t") == 0) {
            char *e;
            long int t = strtol(argv[2], &e, 10);
            if (e != argv[2] && *e == '\0') {
                status = set_timeout(t);
            } else {
                status = usage();
            }
        } else {
            status = usage();
        }
    } else {
        status = usage();
    }

    exit(status);

} /* main */
