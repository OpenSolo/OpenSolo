#!/usr/bin/env python

import subprocess, sys, os, time, glob, argparse, clock
from datetime import datetime
from re import search
from json import loads
SELECT_GPIO = "21"
ENABLE_GPIO = "19"

firmware_ext = "ax"
version_file = "/AXON_VERSION"

def setGPIODir(gpio, direction):
    dir_fd = open("/sys/class/gpio/gpio"+str(gpio)+"/direction", "w")
    dir_fd.write(direction)
    dir_fd.close()

def openGPIO(gpio):
    # Check and see if the GPIO is already exported
    if not os.path.isdir("/sys/class/gpio/gpio"+str(gpio)):
        # Otherwise export it
        exp_fd = open("/sys/class/gpio/export", "w")
        exp_fd.write(gpio)
        exp_fd.close()

    setGPIODir(gpio, "out");

def closeGPIO(gpio):
    unexp_fd = open("/sys/class/gpio/unexport", "w")
    unexp_fd.write(gpio)
    unexp_fd.close()

def setGPIO(gpio, value):
    val_fd = open("/sys/class/gpio/gpio"+str(gpio)+"/value", "w")
    val_fd.write(value)
    val_fd.close()

def openSetClose(gpio, value):
    openGPIO(gpio)
    setGPIO(gpio, value)
    closeGPIO(gpio)

def writeVerFile(AxonVersion, AxonRelease):
    verFile = open(version_file,"w")
    verFile.write(AxonVersion + '\n')
    verFile.write(AxonRelease + '\n')
    verFile.close()

def removeVerFile():
    try:
        os.remove(version_file)
    except Exception:
        pass

def disconnectAndExit():
    openSetClose(ENABLE_GPIO, "1") # disable
    openSetClose(SELECT_GPIO, "0") # uninit
    os.system("echo none > /sys/class/leds/user2/trigger")
    sys.exit()

# return a matching file, or None
def glob_file(pattern):
    files = glob.glob(pattern)
    if len(files) == 0:
        return None
    elif len(files) > 1:
        print("more than one matching filename (%s)" % str(files))
    return files[0]


dev_pattern_usb = "/dev/serial/by-id/usb-3D_Robotics*"

# return device name or None
def create_usb_serial(timeout=2):
    openSetClose(SELECT_GPIO, "1") # init
    openSetClose(ENABLE_GPIO, "0") # enable
    start_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    now_us = start_us
    timeout_us = timeout * 1000000
    while glob_file(dev_pattern_usb) is None and (now_us - start_us) < timeout_us:
        now_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
        time.sleep(0.001)
    end_us = clock.gettime_us(clock.CLOCK_MONOTONIC)
    dev_name = glob_file(dev_pattern_usb)
    return dev_name

# Bootloading process
print("Gimbal update startup script v1.1.8")

parser = argparse.ArgumentParser()
parser.add_argument("file_specified", nargs='?')
args = parser.parse_args()

if args.file_specified and not os.path.isfile(args.file_specified):
    print("File \"%s\" not found" % (args.file_specified))
    sys.exit()

if args.file_specified:
    latest = args.file_specified
else:
    # See what versions we have, sorted by file timestamp
    files = sorted(glob.glob('/firmware/*.%s' % firmware_ext), key=os.path.getmtime)
    if not files:
        print("No Gimbal firmware available for update.")
        sys.exit()

    # Pop the first (newest) firmware from the array
    latest = files[-1]

    # Cleanup old firmwares
    if len(files) > 1:
        for i in range(len(files) - 1):
            print("Removing old firmware: %s" % files[i])
            os.remove(files[i])

# Get the versions from px4 json
latest_json = loads(open(latest).read())
AxonVersion = latest_json['version']
AxonRelease = latest_json['release']

# Set the LED to a blink pattern so the user knows we're updating
os.system("echo timer > /sys/class/leds/user2/trigger")
os.system("echo 1000 > /sys/class/leds/user2/delay_on")
os.system("echo 100 > /sys/class/leds/user2/delay_off")

pixhawk_usb = create_usb_serial()
if pixhawk_usb is None:
    print("No pixhawk found on USB. Exiting.")
    disconnectAndExit()
else:
    print("Pixhawk found on USB")

semver = "unknown"
try:
    output = subprocess.check_output(["/usr/bin/gimbal_setup", "--port=%s" % pixhawk_usb])
    print(output.strip())
    version = search(ur"v(\d+.\d+.\d+)", output)
    if version:
        semver = version.group(1)
except Exception:
    print("Failed to find an attached gimbal, exiting")
    removeVerFile()
    disconnectAndExit()

print("Current gimbal software version %s" % semver)

# Quit early if the gimbal version is the latest (unless called directly with a firmware)
if semver == AxonVersion and not args.file_specified:
    print("Gimbal firmware is current, not updating.")
    writeVerFile(AxonVersion, AxonRelease)
    disconnectAndExit()

print("Loading file %s" % (os.path.abspath(latest)))

# Bootload the gimbal now
ret = subprocess.call(["/usr/bin/gimbal_setup", "--port=%s" % pixhawk_usb, latest])

if ret != 0:
    print("Unable to update the gimbal, closing")
else:
    print("Succesfully updated the gimbal")
    writeVerFile(AxonVersion, AxonRelease)

disconnectAndExit()

