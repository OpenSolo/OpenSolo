#ifndef HOSTAPD_CTRL_H
#define HOSTAPD_CTRL_H

#ifdef __cplusplus
extern "C" {
#endif

#ifndef MAC_LEN
#define MAC_LEN 6
#endif

extern void *hostapd_ctrl_new(const char *ifname);
extern int hostapd_ctrl_delete(void *handle);

typedef struct {
    uint8_t mac[MAC_LEN];
    /* more fields are available, but not parsed */
} hostapd_station_info_t;

extern int hostapd_ctrl_get_stations(const void *handle, hostapd_station_info_t *station_info,
                                     int *station_entries);
extern int hostapd_ctrl_find_by_mac(const hostapd_station_info_t *station_info, int station_entries,
                                    const uint8_t *mac);

#ifdef __cplusplus
};
#endif

#endif /* HOSTAPD_CTRL_H */
