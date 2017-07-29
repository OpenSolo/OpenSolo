#!/bin/bash

import gpio

ENABLE_GPIO = 19
SELECT_GPIO = 21

def init():
    gpio.export(SELECT_GPIO)
    gpio.export(ENABLE_GPIO)
    gpio.set_dir(SELECT_GPIO, "out")
    gpio.set_dir(ENABLE_GPIO, "out")
    gpio.set(SELECT_GPIO, 0)
    gpio.set(ENABLE_GPIO, 1)

def uninit():
    gpio.unexport(SELECT_GPIO)
    gpio.unexport(ENABLE_GPIO)

def enable():
    gpio.set(SELECT_GPIO, 1) # VBUS on
    gpio.set(ENABLE_GPIO, 0) # D+/D- connect

def disable():
    gpio.set(ENABLE_GPIO, 1) # D+/D- disconnect
    gpio.set(SELECT_GPIO, 0) # VBUS off
