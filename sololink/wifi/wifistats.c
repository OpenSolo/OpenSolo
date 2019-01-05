#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/wireless.h>
#include <time.h>
#include <unistd.h>

#include "util.h"

#define LOG_INTERVAL_US 10000

int getStat(int *fd, struct iwreq *iwr, int parm)
{
    if (ioctl(*fd, parm, iwr) < 0)
    {
        //fprintf(stderr, "Get ioctl failed\n");
        return -1;
    }

    return 0;
}

int main(void)
{
    struct iwreq iwr;
    int fd;
    char essid[IW_ESSID_MAX_SIZE + 1];
    char essid_save[IW_ESSID_MAX_SIZE + 1];
    struct iw_statistics stats;
    char logMsg[512];
    int bitrate = 0;
    int power = 0;
    int signal = 0;
    int noise = 0;
    int missed = 0;
    char timestr[24];
    FILE *logfd;
    uint64_t next_us;
    uint64_t now_us;

    next_us = clock_gettime_us(CLOCK_MONOTONIC) + LOG_INTERVAL_US;

    while (1)
    {

        now_us = clock_gettime_us(CLOCK_MONOTONIC);
        if (next_us > now_us)
            usleep(next_us - now_us);
        next_us += LOG_INTERVAL_US;

        clock_gettime_str_r(CLOCK_REALTIME, timestr);

        fd = socket(AF_INET, SOCK_DGRAM, 0);
        strncpy(iwr.ifr_name, "wlan0", IFNAMSIZ);

        //Get the ESSID
        memset(&iwr.u, 0, sizeof(struct iwreq));
        iwr.u.essid.pointer = essid;
        iwr.u.essid.length = IW_ESSID_MAX_SIZE + 1;
        if (!getStat(&fd, &iwr, SIOCGIWESSID))
        {
            //printf("ESSID: %s\n", (char*)iwr.u.essid.pointer);
            memcpy(essid_save, essid, IW_ESSID_MAX_SIZE + 1);
        }
        //Get the txrate
        memset(&iwr.u, 0, sizeof(struct iwreq));
        if (!getStat(&fd, &iwr, SIOCGIWRATE))
        {
            bitrate = iwr.u.bitrate.value;
            //printf("Bitrate: %i\n", iwr.u.bitrate.value);
        }
        //Get the tx power
        memset(&iwr.u, 0, sizeof(struct iwreq));
        if (!getStat(&fd, &iwr, SIOCGIWTXPOW))
        {
            power = iwr.u.txpower.value;
            //printf("TxPower: %i\n", iwr.u.txpower.value);
        }
        //Get the statistics
        memset(&stats, 0, sizeof(stats));
        memset(&iwr.u, 0, sizeof(struct iwreq));
        iwr.u.data.pointer = &stats;
        iwr.u.data.length = sizeof(stats);
        if (!getStat(&fd, &iwr, SIOCGIWSTATS))
        {
            if (stats.qual.updated & IW_QUAL_ALL_UPDATED
                && stats.qual.updated & IW_QUAL_DBM)
            {
                signal = (int) stats.qual.level - 256;
                noise = (int) stats.qual.noise - 256;
                missed = stats.miss.beacon;
                //printf("Signal level: %i dBm, noise: %i dBm\n", (int)stats.qual.level - 256, (int)stats.qual.noise - 256);
                //printf("Missed: %i\n", stats.miss.beacon);
            }
            else
            {
                //printf("Signal data not ready or not in dBm\n");
            }
        }

        sprintf(logMsg,
                "%s, ESSID: %s, Bitrate: %i, Txpower: %i, Signal: %i, Noise: %i, MissedBeacons: %i\n",
                timestr, essid_save, bitrate, power, signal, noise,
                missed);
        //printf("%s", logMsg);

        logfd = fopen("/log/wifistats.log", "a");
        if (logfd != NULL)
        {
            fputs(logMsg, logfd);
            fclose(logfd);
        }

        close(fd);

    }
    return 0;
}
