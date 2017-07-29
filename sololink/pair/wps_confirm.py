#!/usr/bin/env python

# This does the equivalent of:
# hostapd_cli wps_pin any <pin>

import socket

print "wps_confirm.py starting"

controlSock = "/var/run/hostapd/wlan0-ap"

# Message sent to hostapd to confirm PIN pairing. The PIN embedded here must
# match the PIN in Solo's script wps_request.py. It must be a valid WPS PIN;
# use:
#     hostapd_cli wps_check_pin <pin>
#     wpa_cli wps_check_pin <pin>
# to validate a pin, or:
#     wpa_cli wps_pin get
# to get a new random pin.
pinMessage = "WPS_PIN any 74015887"

s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

try:
    s.sendto(pinMessage, controlSock)
    print "pin confirm sent to %s" % (controlSock, )
except:
    print "ERROR sending pin confirm to %s" % (controlSock, )
