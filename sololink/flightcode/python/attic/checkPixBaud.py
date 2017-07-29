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

sololink_conf = "/etc/sololink.conf"

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

def disconnectAndExit():
    openSetClose(SELECT_GPIO, "0")
    openSetClose(ENABLE_GPIO, "1")
    sys.exit()

#Bootloading process
print "Pixhawk telem baudrate checker"

config = ConfigParser.SafeConfigParser()
config.read(sololink_conf)
telemBaud = config.getint("solo","telemBaud")

#Try to connect over the telem and get a heartbeat
m = mavutil.mavlink_connection("/dev/ttymxc1", baud=telemBaud)
m.set_rtscts(True)

hb = m.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
m.close()
if not hb:
    print "Did not receieve a heartbeat on telem.  Checking USB."
else:
    print "Got a heartbeat, this baudrate is correct."
    disconnectAndExit();

#Set the USB select GPIOs
openSetClose(SELECT_GPIO, "1")
openSetClose(ENABLE_GPIO, "0")
time.sleep(1)

#Try to get a heartbeat on the USB.
usb_devs = glob.glob('/dev/serial/by-id/usb-3D*')
if not usb_devs:
    print "No pixhawk found on USB. Exiting."
    disconnectAndExit()

print "Pixhawk found on USB, requesting SERIAL1_BAUD"
pixhawk_usb = usb_devs[-1]
m = mavutil.mavlink_connection(pixhawk_usb)

m.param_fetch_one("SERIAL1_BAUD")
msg = m.recv_match(type='PARAM_VALUE', blocking=True, timeout=3)
if not msg:
    print "Did not get param back!"
    m.close()
    disconnectAndExit()
if msg:
    print "Got value:" + str(msg.param_value)

    if(msg.param_value == 1.):
        baud_setting = 1200
    elif(msg.param_value == 2.):
        baud_setting = 2400
    elif(msg.param_value == 4.):
        baud_setting = 4800
    elif(msg.param_value == 9.):
        baud_setting = 9600
    elif(msg.param_value == 19.):
        baud_setting = 19200
    elif(msg.param_value == 38.):
        baud_setting = 38400
    elif(msg.param_value == 57.):
        baud_setting = 57600
    elif(msg.param_value == 111.):
        baud_setting = 111100
    elif(msg.param_value == 115.):
        baud_setting = 115200
    elif(msg.param_value == 500.):
        baud_setting = 500000
    elif(msg.param_value == 921.):
        baud_setting = 921600
    elif(msg.param_value == 1500.):
        baud_setting = 1500000
    else:
        print "Unknown baudrate!"
        m.close()
        disconnectAndExit()
        
    print "Setting telemBaud to " + str(baud_setting)
    os.system("sed -i \"s/telemBaud.*=.*/telemBaud = "+str(baud_setting)+"/\" /etc/sololink.conf")
    os.system("md5sum /etc/sololink.conf > /etc/sololink.conf.md5")

m.close()

disconnectAndExit()
