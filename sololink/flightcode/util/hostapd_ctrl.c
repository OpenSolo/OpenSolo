
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/un.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "util.h"
#include "hostapd_ctrl.h"

#define IF_NAME_MAX 32

#define HOSTAPD_REPLY_TIMEOUT_US 1000000

typedef struct {
    char if_name[IF_NAME_MAX];
    struct sockaddr_un sa_loc;
    struct sockaddr_un sa_dst;
    int fd;
} hostapd_ctrl_info_t;

/*
* hostapd_ctrl_new - create a hostapd control connection
*
* Returns non-NULL handle on success, or NULL on error.
*/
void *hostapd_ctrl_new(const char *if_name)
{
    hostapd_ctrl_info_t *ctrl;
    struct timeval timeout;

    ctrl = (hostapd_ctrl_info_t *)malloc(sizeof(hostapd_ctrl_info_t));
    if (ctrl == NULL)
        goto hostapd_ctrl_new_error_1;

    memset(ctrl, 0, sizeof(*ctrl));

    strncpy(ctrl->if_name, if_name, IF_NAME_MAX - 1);

    ctrl->fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (ctrl->fd == -1)
        goto hostapd_ctrl_new_error_2;

    ctrl->sa_loc.sun_family = AF_UNIX;
    sprintf(ctrl->sa_loc.sun_path, "/tmp/hostapd_ctrl.%ld", syscall(SYS_gettid));
    if (bind(ctrl->fd, (struct sockaddr *)&(ctrl->sa_loc), sizeof(ctrl->sa_loc)) != 0)
        goto hostapd_ctrl_new_error_3;

    timeout.tv_sec = HOSTAPD_REPLY_TIMEOUT_US / 1000000;
    timeout.tv_usec = HOSTAPD_REPLY_TIMEOUT_US % 1000000;
    if (setsockopt(ctrl->fd, SOL_SOCKET, SO_RCVTIMEO, (char *)&timeout, sizeof(timeout)) != 0)
        goto hostapd_ctrl_new_error_3;

    ctrl->sa_dst.sun_family = AF_UNIX;
    if (snprintf(ctrl->sa_dst.sun_path, sizeof(ctrl->sa_dst.sun_path), "/var/run/hostapd/%s",
                 if_name) >= sizeof(ctrl->sa_dst.sun_path))
        goto hostapd_ctrl_new_error_3;

    return (void *)ctrl;

hostapd_ctrl_new_error_3:
    close(ctrl->fd);
hostapd_ctrl_new_error_2:
    memset(ctrl, 0, sizeof(*ctrl));
    free(ctrl);
hostapd_ctrl_new_error_1:
    return NULL;

} /* hostapd_ctrl_new */

/*
* hostapd_ctrl_delete - delete a hostapd control connection
*/
int hostapd_ctrl_delete(void *handle)
{
    hostapd_ctrl_info_t *ctrl = (hostapd_ctrl_info_t *)handle;

    close(ctrl->fd);
    unlink(ctrl->sa_loc.sun_path);
    memset(ctrl, 0, sizeof(*ctrl));
    free(ctrl);

    return 0;

} /* hostapd_ctrl_delete */

/*
* hostapd_ctrl_get_stations - query hostapd for all attached stations
*
* On entry, station_info points to a caller-supplied table of *station_entries
* hostapd_station_info_t structures. This function fills in the table, up to
* *station_entries entries. On return, *station_entries is the number of
* stations associated. If there are more stations than will fit in the table,
* the table is filled up, then *station_entries is set to the actual number of
* stations.
*
* Returns 0 on success, or nonzero on error. If an error is returned, neither
* the contents of station_info nor *station_entries is valid.
*/
int hostapd_ctrl_get_stations(const void *handle, hostapd_station_info_t *station_info,
                              int *station_entries)
{
    const hostapd_ctrl_info_t *ctrl = (const hostapd_ctrl_info_t *)handle;
    char request[64];
    int request_len;
    ssize_t status;
    char reply[1024];
    char *saveptr;
    char *mac;
    int mac_len;
    int entries = 0;

    strcpy(request, "STA-FIRST");
    request_len = strlen(request);
    status = sendto(ctrl->fd, request, request_len, 0, (struct sockaddr *)&(ctrl->sa_dst),
                    sizeof(ctrl->sa_dst));
    if (status != request_len) {
        perror("sendto");
        return -1;
    }

    do {

        memset(reply, 0, sizeof(reply));
        status = recv(ctrl->fd, reply, sizeof(reply), 0);
        if (status < 0) {
            perror("recv");
            return -1;
        } else if (status == 0) {
            /* normal return; get this after the last station */
            break;
        }

        /*printf("%d bytes: \"%s\"\n", status, reply);*/

        /* get first token (mac) */
        mac = strtok_r(reply, "\n", &saveptr);
        if (mac == NULL) {
            printf("ERROR: getting mac from reply\n");
            return -1;
        }
        mac_len = strlen(mac);
        if (mac_len != 17) {
            printf("ERROR: mac is strange length\n");
            return -1;
        }

        /* only save info if there is room; otherwise, we are just counting
           stations so we can set station_entries */
        if (entries < *station_entries) {

            if (mac_aton(mac, station_info[entries].mac) == NULL) {
                printf("ERROR: parsing mac\n");
                return -1;
            }
        }

        entries++;

        sprintf(request, "STA-NEXT %s", mac);
        request_len = strlen(request);
        status = sendto(ctrl->fd, request, request_len, 0, (struct sockaddr *)&(ctrl->sa_dst),
                        sizeof(ctrl->sa_dst));
        if (status != request_len) {
            perror("sendto");
            return -1;
        }

    } while (1);

    *station_entries = entries;

    return 0;

} /* hostapd_ctrl_get_stations */

int hostapd_ctrl_find_by_mac(const hostapd_station_info_t *station_info, int station_entries,
                             const uint8_t *mac)
{
    int i;

    for (i = 0; i < station_entries; i++)
        if (memcmp(mac, station_info[i].mac, MAC_LEN) == 0)
            return i;

    /* not found */
    return -1;

} /* hostapd_ctrl_find_by_mac */
