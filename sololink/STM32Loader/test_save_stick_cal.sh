#!/bin/bash

# Purpose of this test
    # Enable readout protect and then attempt an artoo update.
    # Artoo parameters (i.e. stick cals) should not be wiped.
    # Test for IG-1435

# Note that this test doesn't always work
    # because for some reason I need to run stm32_readout_protect.py a couple times for it to take effect,
    # but it should be kept around as inspiration for how to test this functionality manually.
    # Testing via a hard power cycle could be more representative than reboot anyway

# Preconditions for this test:
    # Controller is on Solo v2.4.2-1, with Artoo 1.2.11.
    # A firmware file for Artoo 1.2.11 named 1.2.22 exists in /firmware/loaded
    # stm32_readout_protect.py and this file have been copied from the sololink repo (stm32loader folder) into artoo:/usr/bin

init 2  # Stop the stm32 process
sleep 5
cp /firmware/loaded/artoo_1.2.12.bin /firmware/
python /usr/bin/stm32_readout_protect.py  # Enable Readout Protect
echo "Rebooting the controller. Once it comes up, check /log/3dr-solo.log for test results."
sync
reboot