#!/usr/bin/env python

import sys
import os
import time
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

parser = argparse.ArgumentParser()
parser.add_argument("state", help='enable [1] or disable [0] Pixhawk USB')
args = parser.parse_args()

if args.state == '1':
    print("Enabling PH2 USB")
    openSetClose(SELECT_GPIO, "1")
    openSetClose(ENABLE_GPIO, "0")
else:
    print("Disabling PH2 USB")
    openSetClose(SELECT_GPIO, "0")
    openSetClose(ENABLE_GPIO, "1")
