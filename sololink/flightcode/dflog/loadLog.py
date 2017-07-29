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

#Set the GPIO low
def disconnectAndExit():
    openSetClose(SELECT_GPIO, "0")
    openSetClose(ENABLE_GPIO, "1")
    sys.exit()

parser = argparse.ArgumentParser()
parser.add_argument("lognum", help="Log number to download, or 'latest'")
args = parser.parse_args()

#Log downloading process
print "Pixhawk log loader"

#Set the USB select GPIOs
openSetClose(SELECT_GPIO, "1")
openSetClose(ENABLE_GPIO, "0")
time.sleep(1)

print "Checking for pixhawk on USB"

usb_devs = glob.glob('/dev/serial/by-id/usb-3D*')
if not usb_devs:
    print "No pixhawk found on USB.  Exiting."
    disconnectAndExit()
    
print "Pixhawk found on USB, requesting log."
pixhawk_usb = usb_devs[-1]
m = mavutil.mavlink_connection(pixhawk_usb)

#Call the log downloader app
ret = subprocess.call(["dflog", str(args.lognum)])

disconnectAndExit()

