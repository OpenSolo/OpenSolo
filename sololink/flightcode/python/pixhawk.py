#!/usr/bin/env python

# Pixhawk Initialization and Firmware Upgrade

import ConfigParser
import glob
import json
import logging
import logging.config
import os
import re
import serial
import subprocess
import sys
import time
import traceback
from pymavlink import mavutil
sys.path.append("/usr/bin")
import clock
import led
import usb

version_file = "/PIX_VERSION"
sololink_conf = "/etc/sololink.conf"
sololink_back = "/etc/sololink.back"
config_baud_name = "telemBaud"
config_baudlist_name = "telemBaudList"
config_dev_name = "telemDev"
config_flow_name = "telemFlow"
firmware_root = "/firmware"


# ardupilot/libraries/AP_SerialManager/AP_SerialManager.cpp, supported bauds:
#   1500000 921600 500000 460800 230400 115200 111100 100000 57600 38400 19200
#   9600 4800 2400 1200
# Reordered in an attempt to try more likely ones sooner (guesses). The one in
# the config file is always tried first.
baudlist_default = "\
115200 \
921600 \
57600 \
230400 \
460800 \
1500000 \
"


# return a matching file, or None
def glob_file(pattern):
    files = glob.glob(pattern)
    if len(files) == 0:
        return None
    elif len(files) > 1:
        logger.warning("more than one matching filename (%s)", str(files))
    return files[0]


# /dev/serial/by-id/usb-3D_Robotics_PX4_FMU_v2.x_0-if00
# /dev/serial/by-id/usb-3D_Robotics_PX4_BL_FMU_v2.x_0-if00
dev_pattern_usb = "/dev/serial/by-id/usb*"

# return device name or None
def create_usb_serial(timeout=5):
    usb.init()
    usb.enable()
    start_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    now_us = start_us
    timeout_us = timeout * 1000000
    while glob_file(dev_pattern_usb) is None and (now_us - start_us) < timeout_us:
        now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
        time.sleep(0.001)
    end_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    dev_name = glob_file(dev_pattern_usb)
    if os.path.exists(dev_name):
        logger.info("%s created in %0.3f sec",
                     dev_name, (end_us - start_us) / 1000000.0)
    else:
        logger.info("error creating %s", dev_pattern_usb)
        usb.disable()
        usb.uninit()
    return dev_name


# return True (success) or False (did not delete device)
def delete_usb_serial(timeout=1):
    usb.disable()
    usb.uninit()
    start_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    now_us = start_us
    timeout_us = timeout * 1000000
    while glob_file(dev_pattern_usb) is not None and (now_us - start_us) < timeout_us:
        now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
        time.sleep(0.001)
    end_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    if glob_file(dev_pattern_usb) is None:
        logger.debug("%s deleted in %0.3f sec",
                     dev_pattern_usb, (end_us - start_us) / 1000000.0)
        return True
    else:
        logger.error("deleting device %s", dev_pattern_usb)
        return False


def config_get(cfg, name):
    try:
        value = cfg.get("solo", name)
    except:
        value = None
    return value


def config_getint(cfg, name):
    try:
        value = cfg.getint("solo", name)
    except:
        value = None
    return value


def config_getbool(cfg, name, default=None):
    try:
        value = cfg.getboolean("solo", name)
    except:
        value = default
    return value


def config_write(config):
    os.system("cp %s %s" % (sololink_conf, sololink_back))
    os.system("md5sum %s > %s.md5" % (sololink_back, sololink_back))
    os.system("sync")
    f = open(sololink_conf, 'wb')
    config.write(f)
    f.close()
    os.system("md5sum %s > %s.md5" % (sololink_conf, sololink_conf))
    os.system("sync")
    os.system("rm %s %s.md5" % (sololink_back, sololink_back))


def create_tty_mavlink(serial_baud=None):
    config = ConfigParser.SafeConfigParser()
    config.optionxform = str
    config.read(sololink_conf)

    serial_dev = config_get(config, config_dev_name)
    if serial_dev is None:
        logger.error("reading %s from %s", config_dev_name, sololink_conf)
        return None
    logger.debug("%s = %s", config_dev_name, serial_dev)

    serial_flow = config_getbool(config, config_flow_name, True)
    logger.debug("%s = %s", config_flow_name, serial_flow)

    if serial_baud is None:
        serial_baud = config_getint(config, config_baud_name)
        if serial_baud is None:
            logger.error("reading %s from %s", config_baud_name, sololink_conf)
            return None
        logger.debug("%s = %d", config_baud_name, serial_baud)

    m = mavutil.mavlink_connection(serial_dev, baud=serial_baud)
    m.set_rtscts(serial_flow)
    return m


# Get list of baud rates to try
#
# Returns:
#     list of integers
def get_baudlist(config=None, expected_baud=None):

    # use list in config file if it is there
    baudlist = config_get(config, config_baudlist_name)
    if baudlist is None:
        # not in config file; use default
        baudlist = baudlist_default
        logger.debug("using default baud list")

    # convert from string to list of integers
    baudlist = baudlist.split()
    baudlist = [int(b) for b in baudlist]

    # put expected baud at start, twice (one retry)
    if expected_baud is not None:
        # first delete it from wherever it might be
        try:
            baudlist.remove(expected_baud)
        except:
            # config file baud is not one we were going to try!
            logger.warning("trying unlisted baud %d", expected_baud)
        # insert at beginning
        baudlist.insert(0, expected_baud)
        baudlist.insert(0, expected_baud)

    return baudlist


# Find and return Pixhawk's telemetry baud
#
# The assumption is that the baud in the config file is almost always correct.
# If the baud is changed via a GCS, this function scans a list of bauds,
# looking for a heartbeat on each one. When a heartbeat is found, the config
# file is updated and that baud is returned.
#
# Config items:
#   serial device (required)
#   expected baud (optional, default is to scan list)
#   list of bauds to scan (optional, default is 'baudlist_default')
#
# The expected baud is given preference by putting it first in the list of
# bauds to scan. It is actually put at the head of the list twice to give some
# degree of error tolerance.
#
# Returns:
#     baud if found
#     None if Pixhawk not detected or other error
def get_baud():

    config = ConfigParser.SafeConfigParser()
    config.optionxform = str
    config.read(sololink_conf)

    serial_dev = config_get(config, config_dev_name)
    if serial_dev is None:
        logger.error("reading %s from %s", config_dev_name, sololink_conf)
        return None
    logger.debug("%s = %s", config_dev_name, serial_dev)

    serial_flow = config_getbool(config, config_flow_name, True)
    logger.debug("%s = %s", config_flow_name, serial_flow)

    expected_baud = config_getint(config, config_baud_name)
    if expected_baud is None:
        logger.warning("no %s in %s (will search)", config_baud_name, sololink_conf)
    logger.debug("%s = %s", config_baud_name, str(expected_baud))

    baudlist = get_baudlist(config, expected_baud)

    logger.debug("baud list %s", str(baudlist))

    logger.info("checking baud...")

    for baud in baudlist:

        logger.debug("baud %d...", baud)

        m = mavutil.mavlink_connection(serial_dev, baud=baud)
        m.set_rtscts(serial_flow)
        # Allow for missing one, then getting the next one. The expectation is
        # that we'll almost always have the right baud and get the first
        # heartbeat.
        start_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
        hb = m.recv_match(type='HEARTBEAT', blocking=True, timeout=2.5)
        end_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
        m.close()

        if hb is not None:
            # pixhawk is at baud
            # update config file if necessary
            logger.debug("heartbeat received in %0.3f sec",
                         (end_us - start_us) / 1000000.0)
            logger.info("found at %d", baud)
            if baud != expected_baud:
                logger.info("updating %s %s from %s to %d", sololink_conf,
                            config_baud_name, str(expected_baud), baud)
                config.set("solo", config_baud_name, str(baud))
                config_write(config)
            return baud
        logger.info("not at %d", baud)
    logger.error("not detected at any baud")
    return None


# Set baud rate in config file if necessary
def set_baud(new_baud):

    config = ConfigParser.SafeConfigParser()
    config.optionxform = str
    config.read(sololink_conf)

    old_baud = config_getint(config, config_baud_name)
    if old_baud is None:
        logger.warning("no %s in %s", config_baud_name, sololink_conf)
        return
    logger.debug("%s = %s", config_baud_name, str(old_baud))

    if new_baud != old_baud:
        logger.info("updating %s %s from %s to %d", sololink_conf,
                    config_baud_name, str(old_baud), new_baud)
        config.set("solo", config_baud_name, str(new_baud))
        config_write(config)


# Get version of running firmware
#
# The autopilot_version_request message is used to get the git hashes. A
# param_request_list message is used to get the build number (x.y.z); it
# happens to be returned in one of the statustext message sent as part of the
# reply.
#
# Returned version is a dictionary:
#   keys are: build_version, ardupilot_git_hash, px4_git_hash, nuttx_git_hash
#   each value is a string, or missing if could not get version from pixhawk
def get_version():

    config = ConfigParser.SafeConfigParser()
    config.optionxform = str
    config.read(sololink_conf)

    serial_dev = config_get(config, config_dev_name)
    if serial_dev is None:
        logger.error("reading %s from %s", config_dev_name, sololink_conf)
        return None
    logger.debug("%s = %s", config_dev_name, serial_dev)

    serial_flow = config_getbool(config, config_flow_name, True)
    logger.debug("%s = %s", config_flow_name, serial_flow)

    serial_baud = config_getint(config, config_baud_name)
    if serial_baud is None:
        logger.error("reading %s from %s", config_baud_name, sololink_conf)
        return None
    logger.debug("%s = %d", config_baud_name, serial_baud)

    m = mavutil.mavlink_connection(serial_dev, baud=serial_baud)
    m.set_rtscts(serial_flow)

    version = {}

    # Read version. Use AUTOPILOT_VERSION message to get the hashes, and use
    # the STATUSTEXT returned at the start a parameter dump to get the x.y.z
    # version.

    m.mav.autopilot_version_request_send(m.target_system, m.target_component)
    start_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    av = m.recv_match(type='AUTOPILOT_VERSION', blocking=True, timeout=2)
    end_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    if av is not None:
        version["ardupilot_git_hash"] = "".join(chr(e) for e in av.flight_custom_version)
        version["px4_git_hash"] =  "".join(chr(e) for e in av.middleware_custom_version)
        version["nuttx_git_hash"] = "".join(chr(e) for e in av.os_custom_version)
        logger.debug("git hashes received in %0.3f sec",
                     (end_us - start_us) / 1000000.0)
    else:
        logger.warning("no version hashes received")

    m.mav.param_request_list_send(m.target_system, m.target_component)
    start_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    end_us = start_us
    timeout_us = 5 * 1000000
    # Loop because we might get a STATUSTEXT without the version first.
    while (end_us - start_us) < timeout_us:
        st = m.recv_match(type='STATUSTEXT', blocking=True, timeout=5)
        end_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
        if st is not None:
            logger.info("Status Text: %s" %st)
            # "APM:Copter solo-0.1.2 (b2dacc52)"
            match = re.match("APM:.*?solo-([0-9]+\.[0-9]+\.[0-9]+)", st.text)
            if match:
                logger.debug("build version received in %0.3f sec",
                             (end_us - start_us) / 1000000.0)
                version["build_version"] = match.group(1)
                logger.info("build version %s", version_string(version))
                m.close()
                return version
            # "ArduCopter V3.2.1 (b2dacc52)"
            # This is matched in case someone is messing with their firmware
            # Anything looking like a version x.y.z is pulled out
            match = re.match(".*?([0-9]+\.[0-9]+\.[0-9]+)", st.text)
            if match:
                logger.warning("firmware is not specifically for solo")
                logger.info("build version received in %0.3f sec",
                             (end_us - start_us) / 1000000.0)
                version["build_version"] = match.group(1)
                logger.info("build version %s", version_string(version))
                m.close()
                return version
    ### while end_us...

    m.close()
    logger.warning("no build version received")
    return version

# load firmware
def load(firmware_path):
    logger.info("loading %s", firmware_path)
    print "pixhawk: loading firmware %s:", firmware_path

    dev_name = create_usb_serial()
    if dev_name is None:
        logger.info("Failed to open USB serial port to load firmware")
        return False

    # load firmware
    start_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    uploader = subprocess.Popen(["uploader.py",
                           "--port=%s" % dev_pattern_usb,
                           firmware_path])

    ## Start a 2 minute timeout for loading firmware in case it fails
    delay = 1.0
    timeout = int(120 / delay)                      
    while uploader.poll() is None and timeout > 0:
        time.sleep(delay)
        timeout -= delay                       

    if uploader.poll() is None:
        #px_uploader.py failed to complete, probably hosed
        loaded = False
        logger.info("Firmware loading failed due to timeout.")
    elif uploader.returncode != 0:
        #px_uploader.py returned error, failed to load due to error
        loaded = False
        logger.info("Firmware loading failed due to error.")
    elif uploader.returncode == 0:
        #px_uploader succeeded
        loaded = True
        end_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
        logger.info("firmware loaded in %0.3f sec",
                    (end_us - start_us) / 1000000.0)
    else:
        #Unsure if loading FW worked or not, so we'll proceed
        loaded = True
        end_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
        logger.info("firmware may have loaded. Checking for HB")

    delete_usb_serial()

    if loaded:
        move_firmware(firmware_path)
    else:
        os.system("rm -f /firmware/*.apj")
        os.system("rm -f /firmware/*.px4")

    time.sleep(5)
    return loaded


# check usb (diagnostic)
def check_usb():
    dev_name = create_usb_serial()
    if dev_name is None:
        print "ERROR creating usb serial device"
        return
    print "created %s" % dev_name
    time.sleep(1)
    s = serial.Serial(port=dev_name, timeout=1)
    print "opened %s" % dev_name
    d = s.read(100)
    print [hex(ord(b)) for b in d]
    s.close()
    print "closed %s" % dev_name
    time.sleep(1)
    delete_usb_serial()
    print "deleted %s" % dev_name


# verify usb (test)
# return True (pass) or False (fail)
def verify_usb():
    dev_name = create_usb_serial()
    if dev_name is None:
        logger.info("ERROR creating usb serial device")
        return False
    # need to experimentally determine how long we have to wait here before
    # trying to use the USB device (pretty sure it's nonzero)
    time.sleep(1)
    m = mavutil.mavlink_connection(dev_name)
    start_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    hb = m.recv_match(type='HEARTBEAT', blocking=True, timeout=2.5)
    end_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    m.close()
    delete_usb_serial()
    if hb is not None:
        logger.info("heartbeat received over USB in %0.3f sec",
                    (end_us - start_us) / 1000000.0)
        return True
    else:
        logger.info("ERROR getting heartbeat over USB")
        return False


# return info about firmware file
# (full_path, versions)
# full_path is the full path to the file, or None if no file
# if full_path is not None, versions is a dictionary of version info
def find_firmware(dir):
    files = glob.glob("%s/*.apj" % dir) + glob.glob("%s/*.px4" % dir)
    if len(files) == 0:
        logger.info("No firmware file found")
        return (None, None)
    # read git hashes
    full_path = files[-1]
    f = open(full_path)
    info = json.loads(f.read())
    f.close()
    versions = {}
    for i in [ "ardupilot_git_hash", "px4_git_hash", "nuttx_git_hash" ]:
        try:
            versions[i] = str(info[i][:8])
        except:
            versions[i] = "(missing)"
    return (full_path, versions)


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        pass # already exists


def move_firmware(firmware_path):
    mkdir_p("%s/loaded" % firmware_root)
    firmware_file = os.path.basename(firmware_path)
    os.rename(firmware_path, "%s/loaded/%s" % (firmware_root, firmware_file))


def write_version_file(version):
    f = open(version_file, "w")
    for v in ["build_version", "ardupilot_git_hash", "px4_git_hash", "nuttx_git_hash"]:
        if v in version:
            f.write(version[v] + '\n')
        else:
            f.write("unknown\n")
    f.close()


def version_string(version):
    vs = ""
    if "build_version" in version:
        vs += "build=%s " % version["build_version"]
    vs += "ardupilot="
    if "ardupilot_git_hash" in version:
        vs += version["ardupilot_git_hash"]
    else:
        vs += "unknown"
    vs += " px4="
    if "px4_git_hash" in version:
        vs += version["px4_git_hash"]
    else:
        vs += "unknown"
    vs += " nuttx="
    if "nuttx_git_hash" in version:
        vs += version["nuttx_git_hash"]
    else:
        vs += "unknown"
    return vs

def resetParameters():
    logger.info("   Resetting parameters...")
    config = ConfigParser.SafeConfigParser()
    config.optionxform = str
    config.read(sololink_conf)

    serial_dev = config_get(config, config_dev_name)
    if serial_dev is None:
        return

    serial_flow = config_getbool(config, config_flow_name, True)

    serial_baud = config_getint(config, config_baud_name)
    if serial_baud is None:
        return

    m = mavutil.mavlink_connection(serial_dev, baud=serial_baud)
    m.set_rtscts(serial_flow)
    
    m.mav.param_set_send(m.target_system, m.target_component, 'SYSID_SW_MREV', 0, 0)
    time.sleep(5)
    m.mav.command_long_send(m.target_system, m.target_component,246 , 0, 1, 0, 0, 0, 0, 0, 0)
    m.close()
    logger.info("   Waiting 30 seconds for pixhawk to reboot...")
    time.sleep(30)
    return

def recoveryCheck():
    p = subprocess.Popen(['df', '-h'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p1, err = p.communicate()
    pattern = p1

    if pattern.find("mmcblk0p1") == -1:
        logger.info("Not on recovery partition")
        return False
    else:
        logger.info("On recovery partition")
        return True

def rebootPixhawk():
    logger.info("   Rebooting pixhawk...")
    global cube_version
    config = ConfigParser.SafeConfigParser()
    config.optionxform = str
    config.read(sololink_conf)

    serial_dev = config_get(config, config_dev_name)
    if serial_dev is None:
        return

    serial_flow = config_getbool(config, config_flow_name, True)

    serial_baud = config_getint(config, config_baud_name)
    if serial_baud is None:
        return

    m = mavutil.mavlink_connection(serial_dev, baud=serial_baud)
    m.set_rtscts(serial_flow)

    m.mav.command_long_send(m.target_system, m.target_component,246 , 0, 1, 0, 0, 0, 0, 0, 0)
    m.close()
    logger.info("   Waiting 30 seconds for pixhawk to reboot...")
    time.sleep(30)
    return

def checkArduCopter():
    baud = get_baud()
    if baud == None:
        print "pixhawk: ERROR checking baud"
        logger.info("Error checking baud. No response")
        return False
    
    running_version = get_version()
    logger.info(running_version)

    logger.info("now running:")
    for component in ["build_version", "ardupilot_git_hash", "px4_git_hash", "nuttx_git_hash"]:
        if component in running_version:
            version = running_version[component]
        else:
            version = "unknown"
        logger.info("%-20s %s", component, version)
    write_version_file(running_version)
    if "build_version" in running_version \
        and running_version["build_version"] != "unknown":
        logger.info("pixhawk status: ready")
        print "pixhawk: running %s" % running_version["build_version"]
    else:
        print "pixhawk: ERROR checking version"
    
    return True

def doFirmware():
    firmware_path = None
    (firmware_path, firmware_version) = find_firmware(firmware_root)

    if firmware_path is not None and verify_usb():
        # We have firmware to load.
        for v in firmware_version:
            logger.info("%-20s %s", v, firmware_version[v])

        load(firmware_path)

def initialize():
    start_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    led.blink(1000, 100)
    print "pixhawk..."

    serial_ok = False
 
    if os.path.exists("/log/.factory") or os.path.exists("/log/updates/FACTORYRESET") or os.path.exists("/log/updates/UPDATE") or os.path.exists("/log/updates/RESETSETTINGS"):
        os.system("rm -f /log/.factory")
    else:
        serial_ok = checkArduCopter()

        # if we're in factory reset, just reset parameters and exit
        if recoveryCheck() and serial_ok:
            resetParameters()
        else:
            # find and load ArduCopter FW
            if doFirmware():
                serial_ok = checkArduCopter()

            # reset ArduCopter parameters if tagged
            if os.path.exists("/firmware/resetParams") and serial_ok:
                resetParameters()
                os.remove("/firmware/resetParams")
    
    led.off()
    end_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    logger.debug("pixhawk initialization took %0.3f sec",
                 (end_us - start_us) / 1000000.0)


if __name__ == "__main__":

    from optparse import OptionParser

    parser = OptionParser("pixhawk.py [options]")
    parser.add_option("-i", "--init", dest="init", action="store_true",
                      default=False, help="initialize pixhawk")
    parser.add_option("-v", "--version", dest="version", action="store_true",
                      default=False, help="find pixhawk version")
    parser.add_option("-b", "--baud", dest="baud", action="store_true",
                      default=False, help="find pixhawk baud")
    parser.add_option("-l", "--load", dest="load", type="string",
                      default=None, help="load pixhawk firmware")
    parser.add_option("-u", "--usb", dest="usb", action="store_true",
                      default=False, help="connect usb and see what's there")
    parser.add_option("-c", "--config", dest="conf", type="string", default=None,
                      help="configuration file (%s)" % sololink_conf)
    parser.add_option("-f", "--firmware", dest="firm", type="string", default=None,
                      help="firmware root directory (%s)" % firmware_root)
    parser.add_option("-p", "--pix_version", dest="pix", type="string", default=None,
                      help="pixhawk version file (%s)" % version_file)
    parser.add_option("-r", "--reboot", dest="reboot", action="store_true",
                      default=False, help="reboots pixhawk")
    (opts, args) = parser.parse_args()

    if opts.conf is not None:
        sololink_conf = opts.conf

    if opts.firm is not None:
        firmware_root = opts.firm

    if opts.pix is not None:
        version_file = opts.pix

    logging.config.fileConfig(sololink_conf)
    logger = logging.getLogger("pix")

    logger.info("pixhawk.py starting")

    if opts.init:
        # initialize, logging any unexpected exceptions
        try:
            initialize()
        except Exception as ex:
            logger.error("unhandled exception!")
            except_str = traceback.format_exc()
            print except_str
            except_str_list = except_str.split('\n')
            for str in except_str_list:
                logger.error(str)
        # try end

    if opts.version:
        print get_version()

    if opts.baud:
        print get_baud()

    if opts.load is not None:
        load(opts.load)

    if opts.usb:
        print check_usb()

    if opts.reboot:
        rebootPixhawk()

    logger.info("pixhawk.py finished")
