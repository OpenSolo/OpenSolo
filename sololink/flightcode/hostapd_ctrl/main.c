
#include <stdio.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "util.h"
#include "hostapd_ctrl.h"

/* Test program for hostapd_ctrl */

/* make this small (e.g. 2) to test the table-too-small case */
#define STATIONS_MAX 10

int main(int argc, char *argv[])
{
    void *handle;
    hostapd_station_info_t station_info[STATIONS_MAX];
    int stations;
    int i;
    char mac_string[MAC_STRING_LEN];

    handle = hostapd_ctrl_new("wlan0-ap");
    if (handle == NULL) {
        printf("ERROR creating control connection\n");
        exit(1);
    }

    stations = STATIONS_MAX;
    if (hostapd_ctrl_get_stations(handle, station_info, &stations) != 0) {
        printf("ERROR getting station info\n");
        hostapd_ctrl_delete(handle);
        exit(1);
    }

    printf("%d stations:\n", stations);

    if (stations > STATIONS_MAX)
        /* there are more stations than would fit in the table we supplied */
        stations = STATIONS_MAX;

    for (i = 0; i < stations; i++)
        printf("%s\n", mac_ntoa(station_info[i].mac, mac_string));

    hostapd_ctrl_delete(handle);

    exit(0);

} /* main */
