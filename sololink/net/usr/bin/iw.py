
import re
import subprocess


# Expected output:
#
# $ iw dev wlan0 link
# Connected to d4:d7:48:81:68:a0 (on wlan0)
#         SSID: 3DRobotics
#         freq: 2447
#         RX: 5779050 bytes (38689 packets)
#         TX: 13885 bytes (73 packets)
#         signal: -37 dBm
#         tx bitrate: 48.0 MBit/s
#
#         bss flags:      short-preamble short-slot-time
#         dtim period:    0
#         beacon int:     85
# Returns dictionary of information

def link(ifName):

    info = { 'mac' : None,
             'ssid' : None,
             'freq' : None,
             'rxBytes' : None,
             'rxPackets' : None,
             'txBytes' : None,
             'txPackets' : None,
             'signal' : None,
             'txBitrate' : None }

    try:
        iwOut = subprocess.check_output(['iw', 'dev', ifName, 'link'],
                                        stderr=subprocess.STDOUT)
    except:
        return info

    m = re.search("Connected to (.*?)\s", iwOut)
    if m:
        info['mac'] = m.group(1)

    m = re.search('SSID: (.*)\s', iwOut)
    if m:
        info['ssid'] = m.group(1)

    m = re.search('freq: ([0-9]+)\s', iwOut)
    if m:
        info['freq'] = int(m.group(1))

    m = re.search('RX: ([0-9]+) bytes \(([0-9]+) packets\)\s', iwOut)
    if m:
        info['rxBytes'] = int(m.group(1))
        info['rxPackets'] = int(m.group(2))

    m = re.search('TX: ([0-9]+) bytes \(([0-9]+) packets\)\s', iwOut)
    if m:
        info['txBytes'] = int(m.group(1))
        info['txPackets'] = int(m.group(2))

    m = re.search('signal: (-[0-9]+) dBm\s', iwOut)
    if m:
        info['signal'] = int(m.group(1))

    m = re.search('tx bitrate: ([0-9]+\.[0-9]+) MBit', iwOut)
    if m:
        info['txBitrate'] = float(m.group(1))

    return info


# returns frequency in MHz (or None)
def getFreq(ifName):
    info = link(ifName)
    return info['freq']


# Expected output:
#
# $ iw dev wlan0 info
# Interface wlan0
#         ifindex 3
#         wdev 0x1
#         addr 00:02:60:51:90:06
#         ssid SoloLink
#         type AP
#         wiphy 0
#         channel 8 (2447 MHz), width: 20 MHz, center1: 2447 MHz

def getChan(ifName):
    try:
        iwOut = subprocess.check_output(['iw', 'dev', ifName, 'info'],
                                        stderr=subprocess.STDOUT)
    except:
        return None
    m = re.search('channel ([0-9]+)\s', iwOut)
    if m:
        return int(m.group(1))
    return None


map = [(1, 2412), (2, 2417), (3, 2422), (4, 2427), (5, 2432),
       (6, 2437), (7, 2442), (8, 2447), (9, 2452), (10, 2457),
       (11, 2462), (12, 2467), (13, 2472), (14, 2484)]


def freqToChan(freq):
    for m in map:
        if freq == m[1]:
            return m[0]
    return None


def chanToFreq(chan):
    for m in map:
        if chan == m[0]:
            return m[1]
    return None
