#!/usr/bin/env python

# stm32loader in /usr/bin is not on the default python path; make
# sure we always find it no matter where this script is installed
import sys
sys.path.append("/usr/bin")
import stm32loader

cmd = stm32loader.CommandInterface()
cmd.open("/dev/ttymxc1", 115200)
cmd.initChip()
cmd.cmdGet()
cmd.cmdGetID()
cmd.cmdReadoutProtect()
cmd.releaseChip()
