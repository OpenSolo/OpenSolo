#!/usr/bin/env python

import glob
import serial
import slip
import os
import subprocess
import sys
import time
import logging
import logging.config
import param_stored_vals_msg  # Used for reading stick calibration values
import slip, struct  # Used for writing stick calibration values

sololink_conf = "/etc/sololink.conf"

ARTOO_SYSINFO_ID = chr(0x3)
ARTOO_UPDATE_ID = chr(0x12)
ARTOO_LOCKOUT_ID = chr(0x13)
ARTOO_CALIBRATE_ID = chr(0x2)

ARTOO_UPDATE_SUCCESS = chr(1)
ARTOO_UPDATE_FAILED = chr(2)

ARTOO_LOCKOUT_FALSE = chr(0)
ARTOO_LOCKOUT_TRUE = chr(1)

ARTOO_BAUD = 115200

# update_result should be either ARTOO_UPDATE_SUCCESS or ARTOO_UPDATE_FAILED
def setArtooUpdateComplete(update_result):
    ser = serial.Serial("/dev/ttymxc1", 115200, timeout=1)
    slipdev = slip.SlipDevice(ser)
    slipdev.write("".join([ARTOO_UPDATE_ID, update_result]))
    ser.close()

# lockout should be either ARTOO_LOCKOUT_FALSE or ARTOO_LOCKOUT_TRUE
def setArtooLockout(lockout):
    ser = serial.Serial("/dev/ttymxc1", 115200, timeout=1)
    slipdev = slip.SlipDevice(ser)
    slipdev.write("".join([ARTOO_LOCKOUT_ID, lockout]))
    ser.close()

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        pass # already exists

def doUpdateComplete():
    setArtooLockout(ARTOO_LOCKOUT_FALSE)
    if not os.path.exists("/log/updates/READY"):
        if os.path.exists("/log/updates/UPDATEFAILED"):
            f = open("/log/updates/UPDATEFAILED", "r")
            # file should be one line; read it all
            r = f.read(1000)
            f.close()
            r = r.strip("\r\n\t\0 ")
            logger.info("request \"update failed\" screen (%s)", r)
            setArtooUpdateComplete(ARTOO_UPDATE_FAILED)
        else:
            logger.info("request \"update success\" screen")
            setArtooUpdateComplete(ARTOO_UPDATE_SUCCESS)
        mkdir_p("/log/updates")
        open("/log/updates/READY", "w").close() # "touch"
    else:
        logger.info("no screen update (READY exists)")

# return tuple (filename, version), or None
def getFirmwareInfo():
    files = sorted(glob.glob("/firmware/artoo_*.bin"))
    if not files:
        return None
    filename = files[-1]
    # Filename may be of the form
    # "/firmware/artoo_0.0.0.bin", or
    # "/firmware/artoo_v0.0.0.bin".
    # Get it without the 'v'.
    if filename[16] == 'v':
        version = filename[17:-4]
    else:
        version = filename[16:-4]
    return (filename, version)

# return version as string ("unknown" if can't get version)
def getArtooVersion():
    #Check the version of the stm32 firmware over serial
    #The STM32 might be emitting packets already, so we try a few times to get the
    #version string. This has been observed to get the version with one retry on
    #several occasions.
    logger.info("requesting stm32 version")
    version = "unknown"
    ser = serial.Serial("/dev/ttymxc1", 115200, timeout=1)
    slipdev = slip.SlipDevice(ser)
    for i in range(5):
        slipdev.write("".join([ARTOO_SYSINFO_ID]))
        pkt = slipdev.read()
        if not pkt:
            logger.info("no data received from stm32, retrying")
            continue
        pkt = "".join(pkt)
        if pkt[0] == ARTOO_SYSINFO_ID:
            # SysInfo packet is:          artoo/src/hostprotocol.cpp
            # start size
            #   0     1  ARTOO_SYSINFO_ID artoo/src/hostprotocol.h
            #   1    12  UniqueId         artoo/src/stm32/sys.h
            #  13     2  hwversion        artoo/src/hostprotocol.cpp
            #  15   var  Version          artoo/src/version.h
            # Version may start with an initial 'v', e.g. v0.6.10,
            # but we want it starting with the numeric part.
            if pkt[15] != 'v':
                version = pkt[15:]
            else:
                version = pkt[16:]
            break
        logger.info("got %s/%d, retrying", str(hex(ord(pkt[0]))), len(pkt))
    ser.close()
    return version

# Attempt to update the STM32 multiple times
def updateStm32(filename):
    # Total attempts will be retry+1, with the last one doing the unprotect.
    # Since doing the unprotect results in a support call, retries is set
    # such that the unprotect is a last resort. Allow for two init failures
    # and two erase failures (truly degenerate) before doing the unprotect
    # and (hopefully) fixing a protected stm32. Getting to the unprotect
    # (where it is really needed) should happen only once in a controller's
    # lifetime, if at all (it should never be needed, really).
    stick_cal = None
    retry = 4
    while retry >= 0:
        if retry > 0:
            # don't unprotect chip the first few times an erase fails
            logger.info("updating without readout protection disable")
            if call_stm32loader(filename, disable_readout_protect=False):
                break  # Move on if the firmware is successfully loaded.
        else:
            # last attempt - unprotect chip if erase fails
            logger.info("Updating the STM32 has failed several times. We suspect that readout protection is enabled.")
            logger.info("Saving Stick Calibration: ")
            stick_cal = read_stick_cal()
            logger.info(stick_cal)
            logger.info("updating with readout protection disable. This will wipe flash.")
            call_stm32loader(filename, disable_readout_protect=True)
        retry -= 1

    logger.info("Update complete. Stick cal before update was: {}. (None means it wasn't read before update)".format(stick_cal))
    logger.info("stick cal after update: {}".format(read_stick_cal()))

    # Only write stick calibration if we did disabled readout protection:
    if stick_cal is not None:
        # Try to write_stick cal multiple times in case it fails.
        # This is defensive. I've never seen it fail.
        for i in range(3):
            write_stick_cal(stick_cal)
            time.sleep(1)
            logger.info("Stick cal written. Reading it back again as a check:")
            new_cal = read_stick_cal()
            logger.info(new_cal)
            if stick_cal == new_cal:
                break
            else:
                logger.info("Stick cal failed to be written correctly:")
                logger.info("Calibration attempted to be written: {}".format(stick_cal))
                logger.info("Calibration found in flash: {}".format(new_cal))

# Initiate the stm32loader process to actually update the STM32 chip. Return True if successful.
def call_stm32loader(filename, disable_readout_protect=False):
    # subprocess.check_output raises an exception if stm32loader.py returns a nonzero exit code for any reason
    # including if readout_protect is enabled.
    # Disable readout protect if specified. This will erase all flash.

    if disable_readout_protect:
        flags = "-wvqu"
    else:
        flags = "-wvq"

    try:
        s = subprocess.check_output(["stm32loader.py", flags, "-s", "127",
                                     "-b", "115200", "-p", "/dev/ttymxc1", filename],
                                    stderr=subprocess.STDOUT)
        logger.info("stm32loader.py returned normally; output:")
        success = True
    except subprocess.CalledProcessError as cpe:
        s = cpe.output
        logger.info("stm32loader.py returned error; output:")
        success = False

    # this might be ugly, but it gets the output in the log
    s = s.strip("\r\n\t\0 ")
    logger.info(s)
    # Wait a second for the STM32 to come back up before we send it a message later
    time.sleep(1)
    return success

def writeVersionFile(version):
    f = open("/STM_VERSION", 'w')
    f.write(version + '\n')
    f.close()

# return version from /STM_VERSION
def getVersionFile():
    try:
        f = open("/STM_VERSION", 'r')
        version = f.readline()
        f.close()
        version = version.strip()
        if version == "":
            version = "unknown"
    except:
        version = "unknown"
    return version


def read_stick_cal():
    # Start the STM32 process because sololink_config sets runlevel to 2 before an update,
    # but we need the (runlevel 3) STM32 process to read a stick cal.
    p = subprocess.Popen('stm32', shell=True)
    time.sleep(3)

    msg = param_stored_vals_msg.fetch()  # String containing all artoo params (including stick cal values)
    p.terminate()  # Kill the STM32 process.
    time.sleep(1)  # Give time for the STM32 process to die. Not sure if needed.

    # msg is an empty string if the stm32 process is not running (runlevel 2)
    if not msg:
        logger.info("Could not read stick calibration.")
        return None
    else:
        msg = param_stored_vals_msg.unpack(msg)  # Converts string to Dict
        axes = msg.get('stickCals')  # 6-item list of 3-item tuples
        # Pack datastructure into a single list that can be written later
        stick_cals = []
        for a in axes:
            stick_cals.extend(a)
        return stick_cals


def write_stick_cal(values):
    logger.info("Writing stick cal: {}".format(values))

    serialpath = '/dev/ttymxc1'
    serialport = serial.Serial(serialpath, ARTOO_BAUD)
    slipdev = slip.SlipDevice(serialport)

    packed_vals = struct.pack("<HHHHHHHHHHHHHHHHHH", *values)
    slipdev.write("".join([ARTOO_CALIBRATE_ID, packed_vals]))


# Main
logging.config.fileConfig(sololink_conf)
logger = logging.getLogger("stm32")

logger.info("stm32 update starting")

firmware = getFirmwareInfo()

if firmware is None:
    logger.info("no firmware available for update")
else:
    logger.info("firmware: file %s, version %s", firmware[0], firmware[1])

# Read the version from the STM32
artoo_version = getArtooVersion()
logger.info("running version: %s", artoo_version)

# If we have firmware and it does not match what is running, update the STM32
if firmware is not None:
    if artoo_version != firmware[1]:
        logger.info("updating")
        updateStm32(firmware[0])
        # re-read the version from the running firmware
        artoo_version = getArtooVersion()
    else:
        logger.info("not updating (new firmware is already running)")
    # Whether we used it or not, we are done with the new firmware
    logger.info("moving firmware to loaded")
    mkdir_p("/firmware/loaded")
    os.rename(firmware[0], "/firmware/loaded/" + os.path.basename(firmware[0]))
else:
    logger.info("not updating (no new firmware)")

# Write version retrieved from STM32 to file
logger.info("writing STM_VERSION with running version %s", artoo_version)
writeVersionFile(artoo_version)

doUpdateComplete()

# delete /log/.factory if it exists (it has no effect)
if os.path.exists("/log/.factory"):
    logger.info("deleting .factory")
    os.system("rm -f /log/.factory")
