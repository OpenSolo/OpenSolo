#!/usr/bin/env python

# stm32loader in /usr/bin is not on the default python path; make
# sure we always find it no matter where this script is installed
import sys
sys.path.append("/usr/bin")
import stm32loader

stm32loader.QUIET = 0

cmd = stm32loader.CommandInterface()
cmd.open("/dev/ttymxc1", 115200)
cmd.initChip()
cmd.cmdGet()
cmd.cmdGetID()

status = 1

msg = "cal is blank"

try:
    data = cmd.readMemory(0x0803f800, 2048)
    for c in data:
        if c != 255:
            msg = "cal is not blank"
            status = 0
            break
except:
    msg = "error reading cal (readout protect?)"
    pass

cmd.releaseChip()

print msg

sys.exit(status)
