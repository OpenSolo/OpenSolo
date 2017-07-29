#include "analyzer_util.h"
#include <sys/time.h>

#include <math.h>

void format_timestamp(char *buf, const uint8_t buflen, const uint64_t T)
{
    struct tm *tmp;
    time_t t = T / 1000000;
    tmp = localtime(&t);
    ::strftime(buf, buflen, "%Y%m%d%H%M%S", tmp);
}

uint64_t now()
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec * (uint64_t)1000000 + tv.tv_usec;
}

double vec_len(double vec[3])
{
    return sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2]);
}

double earthradius() // in metres
{
    return 6371000.0f;
}

double wrap_valid_longitude(const double longitude)
{
    if (longitude < 180.0f) {
        return longitude;
    }

    return 180 - (longitude - 180);
    // return (((longitude + 180.0) % 360.0) -180.0);
}

// http://www.movable-type.co.uk/scripts/latlong.html
void gps_newpos(const double orig_lat, const double orig_lon, const double bearing,
                const double distance, double &dest_lat, double &dest_lon)
{
    double origin_lat_rad = deg_to_rad(orig_lat);
    double origin_lon_rad = deg_to_rad(orig_lon);
    double bearing_rad = deg_to_rad(bearing);

    double dr = distance / earthradius();

    dest_lat =
        asin(sin(origin_lat_rad) * cos(dr) + cos(origin_lat_rad) * sin(dr) * cos(bearing_rad));
    dest_lon = origin_lon_rad + atan2(sin(bearing_rad) * sin(dr) * cos(origin_lat_rad),
                                      cos(dr) - sin(origin_lat_rad) * sin(origin_lat_rad));
    dest_lat = rad_to_deg(dest_lat);
    dest_lon = wrap_valid_longitude(rad_to_deg(dest_lon));
}

// origin_lat in degrees
// origin_lon in degrees
// bearing in degrees
// distance in metres
void gps_offset(double orig_lat, double orig_lon, double east, double north, double &dest_lat,
                double &dest_lon)
{
    double bearing = rad_to_deg(atan2(east, north));
    double distance = sqrt(east * east + north * north);
    gps_newpos(orig_lat, orig_lon, bearing, distance, dest_lat, dest_lon);
}

double altitude_from_pressure_delta(double gnd_abs_press, double gnd_temp, double press_abs,
                                    double temp UNUSED)
{
    double scaling = press_abs / gnd_abs_press;
    return 153.8462 * (gnd_temp + 273.15) * (1.0 - exp(0.190259 * log(scaling)));
}
