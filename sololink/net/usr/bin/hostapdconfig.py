#!/usr/bin/env python

import configfile
import ip
import iw
import logging
import logging.config
from optparse import OptionParser

logging.config.fileConfig("/etc/sololink.conf")
logger = logging.getLogger("net")

logger.info("hostapdconfig.py starting")

parser = OptionParser('hostapdconfig.py [options]')

parser.add_option('--file', dest='fileName', type='string',
                  default='/etc/hostapd.conf', help='config file name')

parser.add_option('--channel', dest='channel', type='string',
                  default=None, help='set channel')

parser.add_option('--ssid', dest='ssid', type='string',
                  default=None, help='set ssid')

parser.add_option('--ssidmac', dest='ssidmac', type='string',
                  default=None, help='append last 3 bytes of MAC to ssid')

parser.add_option('--country', dest='country', type='string',
                  default=None, help='set the country code for regulatory')

(opts, args) = parser.parse_args()


# Handle --channel - set channel in config file

if opts.channel is not None:
    logger.info('--channel %s', opts.channel)

    # integer: set specific channel (0 means auto)
    # string: get interface's channel and use that

    # opts.channel might be string something like '9', so try to convert
    # (can't use type())
    try:
        chanInt = int(opts.channel)
    except:
        chanInt = None

    if chanInt is None:
        # opts.channel should be an interface name, e.g. "wlan0"
        ifName = opts.channel
        freq = iw.getFreq(ifName)
        if freq is None:
            chanInt = 0 # same as acs_survey
            logger.info('can\'t get %s frequency; defaulting to channel %d', ifName, chanInt)
        else:
            # Use wlan0's channel
            chanInt = iw.freqToChan(freq)
            logger.info('%s is at %d MHz (channel %d)', ifName, freq, chanInt)

    oldChan = configfile.paramGet(opts.fileName, 'channel')
    logger.info('changing channel in %s from %s to %d', opts.fileName, str(oldChan), chanInt)
    configfile.paramSet(opts.fileName, 'channel', chanInt)


# Handle --ssid - set SSID in config file

if opts.ssid is not None:
    logger.info('--ssid %s', opts.ssid)
    oldSsid = configfile.paramGet(opts.fileName, 'ssid')
    logger.info('changing ssid in %s from %s to %s', opts.fileName, oldSsid, opts.ssid)
    configfile.paramSet(opts.fileName, 'ssid', opts.ssid)


# Handle --ssidmac - append last 3 bytes of MAC to ssid
#
# Note that common usage is supplying both --ssid <basename> and --ssidmac, e.g.
#     hostapdconfig.py --ssid SoloLink_ --ssidmac wlan0
# would set the ssid to something like SoloLink_505FC8
#
# If the ssid already has the MAC appended, this will blindly append it again.

if opts.ssidmac is not None:
    logger.info('--ssidmac %s', opts.ssidmac)
    mac = ip.getMac(opts.ssidmac)
    if mac is None:
        logger.error('can\'t get mac')
    elif len(mac) != 17:
        logger.error('mac "%s" is not 17 characters', mac)
    else:
        oldSsid = configfile.paramGet(opts.fileName, 'ssid')
        mac = mac[9:11] + mac[12:14] + mac[15:17]
        newSsid = oldSsid + mac.upper()
        logger.info('changing ssid in %s from %s to %s', opts.fileName, oldSsid, newSsid)
        configfile.paramSet(opts.fileName, 'ssid', newSsid)

# Handle --country to set the country code
if opts.country is not None:
    logger.info('--country %s', opts.country)
    oldCountry = configfile.paramGet(opts.fileName, 'country_code')
    logger.info('changing country code from %s to %s', oldCountry, opts.country)
    configfile.paramSet(opts.fileName, 'country_code', opts.country)
