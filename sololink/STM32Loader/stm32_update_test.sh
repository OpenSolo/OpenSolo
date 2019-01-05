#!/bin/bash

# STM32 Update Testing
#
# forever:
#   "update" to factory
#   verify calibration
#   update to new
#   verify calibration
#
# Setup:
#   Put factory and latest firmware on controller in /firmware/loaded.
#   Copy this script to controller and run it there.
#   Set names of those two files in this script (below).
#
# Results go to stdout. Run it like this:
#   # ./stm32_update_test.sh 2>&1 | tee -a /log/stm32_test.log &
# to get a log (of both stdout and stderr) and let you disconnect from
# controller while the test runs. If cal is ever detected as missing,
# the test stops.
#
# BIG NOTE:
#
# If you run the script in the background (&), then it is "difficult"
# (I could not figure out how) to stop it without leaving the STM32 in
# a corrupt state (no program to run). If you turn off controller in
# this state, you will have to OPEN IT UP AND FLASH THE STM32 MANUALLY
# to fix it. "Safely" (relative, right) terminate the test like this:
#   # ./stm32_update_test.sh 2>&1 | tee -a /log/stm32_test.log &
#   [1] 5970
#   #
#   (time passes)
#   # kill %1
#   (STM32 is mostly likely CORRUPT at this point)
#   # mv /firmware/loaded/artoo_1.2.8.bin /firmware
#   # checkArtooAndUpdate.py
#   (STM32 is flashed)
#
# Little Notes:
# * Stm32 is normally receiving data (mavlink) at the moment the update
#   process begins. One thought is that data might somehow remain in the
#   uart (imx6 -> STM32), causing problems in init. This test probably
#   does not cover that, but another test that *did* catch that shows
#   that the effect is to fail to flash artoo - cal is not erased.
# * After killing this test, you may be in runlevel 2, which means the
#   controller's power button will NOT work; do an "init 3" then it will
#   work. If you control-C, the script will finish the current update
#   (up to a minute) and quit, leaving you in runlevel 3.

factory=artoo_1.2.2.bin
latest=artoo_1.2.8.bin

# $1 is start address
# $2 is length
# $3 is output file
stm32_read() {
    init 2
    sleep 2
    stm32loader.py -q -p /dev/ttymxc1 -r -a $1 -l $2 $3
    sleep 1
    init 3
    sleep 2
}

# $1 is the firmware filename
stm32_update() {
    cp /firmware/loaded/$1 /firmware
    init 2
    sleep 2
    checkArtooAndUpdate.py
    init 3
    sleep 2
}

check_cal() {
    stm32_read 0x0803f800 2048 /log/cal.bin
    if cmp -s /log/cal.bin /log/cal-ref.bin; then
        return 0
    else
        echo "cal read from STM32 does not match reference cal"
        echo "reference cal:"
        od -x /log/cal-ref.bin
        echo "cal read from STM32:"
        od -x /log/cal.bin
        exit 1
    fi
}

# check required files are there
if [ ! -f /firmware/loaded/${factory} -o \
     ! -f /firmware/loaded/${latest} ]; then
    echo "${factory} or ${latest} not found in /firmware/loaded"
    exit 1
fi

# get reference cal
echo "reading reference cal..."
stm32_read 0x0803f800 2048 /log/cal-ref.bin
if [ `od -x /log/cal-ref.bin | wc -l` -le 3 ]; then
    # cal looks erased already
    echo "reference cal already erased?"
    od -x /log/cal-ref.bin
    exit 1
fi

# get erased block (assumes block before cal is erased)
#echo "reading erased block..."
#stm32_read 0x0803f000 2048 /log/cal-bad.bin
#if [ `od -x /log/cal-bad.bin | wc -l` -ne 3 ]; then
#    # does not look erased
#    echo "erased block isn't erased?"
#    od -x /log/cal-bad.bin
#    exit 1
#fi

# set up so control-C (SIGINT) or kill (SIGTERM) exits between updates
quitting=false

on_sigint() {
    echo "sigint..."
    quitting=true
}
trap on_sigint SIGINT

# The intent is to be able to background this script, then tell it to quit
# with "kill %1" to send it a SIGTERM, but this never gets called... :(
on_sigterm() {
    echo "sigterm..."
    quitting=true
}
trap on_sigterm SIGTERM

while true; do

    echo "updating to ${factory}..."
    stm32_update ${factory}
    echo "checking cal..."
    check_cal

    if [ $quitting == "true" ]; then break; fi

    echo "updating to ${latest}..."
    stm32_update ${latest}
    echo "checking cal..."
    check_cal

    if [ $quitting == "true" ]; then break; fi

done
