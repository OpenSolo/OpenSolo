#!/usr/bin/env python

import subprocess 
import sys
import os
import time
from pymavlink import mavutil
import glob
import ConfigParser
import shutil
from datetime import datetime
import re
import json
import argparse

SELECT_GPIO = "21"
ENABLE_GPIO = "19"

#GPIO direction set
def setGPIODir(gpio, direction):
    dir_fd = open("/sys/class/gpio/gpio"+str(gpio)+"/direction", "w")
    dir_fd.write(direction)
    dir_fd.close()

#Open the GPIO
def openGPIO(gpio):
    #Check and see if the GPIO is already exported
    if not os.path.isdir("/sys/class/gpio/gpio"+str(gpio)):
        #otherwise export it
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

def writeVerFile(ArduVersion, PX4Version, NuttXVersion, filename):
    verFile = open("/PIX_VERSION","w")
    version=filename.split('-',1)[1].split('.px',1)[0]
    verFile.write(version + '\n')
    verFile.write(ArduVersion + '\n')
    verFile.write(PX4Version + '\n')
    verFile.write(NuttXVersion + '\n')
    verFile.close()

def disconnectAndExit():
    openSetClose(SELECT_GPIO, "0")
    openSetClose(ENABLE_GPIO, "1")
    os.system("echo none > /sys/class/leds/user2/trigger")
    sys.exit()

#Bootloading process
print "Pixhawk bootloader"

parser = argparse.ArgumentParser()
parser.add_argument("file_specified", nargs='?')
args = parser.parse_args()

if args.file_specified and not os.path.isfile(args.file_specified):
    print "File \"%s\" not found" % (args.file_specified)
    sys.exit()
if args.file_specified:
    latest = args.file_specified
else:
    #See what version we have
    files = glob.glob('/firmware/*.px4')
    if not files:
        print "No Pixhawk firmware available for update."
        sys.exit()

    latest = files[-1]

#Get the versions from px4 json
latest_json = json.loads(open(latest).read())
try:
    ArduVersion = latest_json['ardupilot_git_hash'][:8]
except:
    print ".px4 file does not have ardupilot git hash"
    ArduVersion = "00000000"
    PX4Version = "00000000"
    NuttXVersion = "00000000"
else:
    PX4Version = latest_json['px4_git_hash'][:8]
    NuttXVersion = latest_json['nuttx_git_hash'][:8]

print "Read file versions:"
print "    ArduPilot: " + ArduVersion
print "          PX4: " + PX4Version
print "        NuttX: " + NuttXVersion

#Set the LED to a blink pattern so the user knows we're updating
os.system("echo timer > /sys/class/leds/user2/trigger")
os.system("echo 1000 > /sys/class/leds/user2/delay_on")
os.system("echo 100 > /sys/class/leds/user2/delay_off")

#Set the USB select GPIOs
openSetClose(SELECT_GPIO, "1")
openSetClose(ENABLE_GPIO, "0")

time.sleep(1)

usb_devs = glob.glob('/dev/serial/by-id/usb-3D*')
if not usb_devs:
    print "No pixhawk found on USB.  Exiting."
    disconnectAndExit()

print "Pixhawk found on USB."
pixhawk_usb = usb_devs[-1]
m = mavutil.mavlink_connection(pixhawk_usb)

#Check the arducopter version number from the AUTOPILOT_VERSION message
if not args.file_specified:
    m.mav.autopilot_version_request_send(m.target_system, m.target_component)
    while True:
        msg = m.recv_match(type='AUTOPILOT_VERSION', blocking=True, timeout=5)
        if msg:
            pixArduVersion = ''.join(chr(e) for e in msg.flight_custom_version)
            pixPX4Version =  ''.join(chr(e) for e in msg.middleware_custom_version)
            pixNuttXVersion = ''.join(chr(e) for e in msg.os_custom_version)

            print "Pixhawk returned versions:"
            print "    ArduPilot: " + pixArduVersion
            print "          PX4: " + pixPX4Version
            print "        NuttX: " + pixNuttXVersion

            if(ArduVersion != pixArduVersion or PX4Version != pixPX4Version or NuttXVersion != pixNuttXVersion):
                print "New version available, bootloading"
                break
            else:
                print "Already latest version"
                m.close()
                try:
                    os.mkdir("/firmware/loaded/")
                except OSError:
                    pass
                os.rename(latest,"/firmware/loaded/"+os.path.basename(latest))
                writeVerFile(ArduVersion,PX4Version,NuttXVersion,latest) 
                disconnectAndExit()
        else:
            print "Unable to get Ardupilot version, forcing bootload."
            break

m.close()

print "loading file %s" % (os.path.abspath(latest))

#Bootload the pixhawk now (probably not the best way to do this)
ret = subprocess.call(["python","/usr/bin/px_uploader.py","--port=/dev/serial/by-id/usb-3D_Robotics*",latest])

if(ret != 0):
    print "Unable to bootload the pixhawk, closing"
else:
    print "Succesfully bootloaded Pixhawk"
    #move the loaded firmware to a new /firmware/loaded/ folder
    shutil.rmtree("/firmware/loaded/", ignore_errors=True)
    try:
        os.mkdir("/firmware/loaded/")
    except OSError:
        pass
    
    if args.file_specified:
        shutil.copy(latest,"/firmware/loaded/"+os.path.basename(latest))
    else:
        os.rename(latest,"/firmware/loaded/"+os.path.basename(latest));
        writeVerFile(ArduVersion,PX4Version,NuttXVersion,latest) 

disconnectAndExit()
