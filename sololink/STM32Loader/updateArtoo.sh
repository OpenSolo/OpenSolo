#!/bin/sh

#Comment out the RCTX line in /etc/inittab
sed -i 's/^RCTX.*/#&/g' /etc/inittab

#stop the stm32 process
init q
sleep 1

# update artoo
# we only erase the first 127 pages since the stm32 stores param data in its last page.
# the stm32 we're currently using has 128 pages of 2k each - this will need to change if we
# ever use different stm32 varieties.
stm32loader.py -vw -s 127 -p /dev/ttymxc1 /home/root/artoo.bin

# note - verification
# you can read back the last page to verify that it wasn't overwritten in the update process:
#
#   ./stm32loader.py -r -a 0x803f800 -l 2048 -p /dev/ttymxc1 readback.bin
#   hexdump readback.bin
#
# if it's not all 0xff's you're in good shape!

#Uncomment the RCTX line
sed -i 's/.\(RCTX*.\)/\1/g' /etc/inittab

#start the stm32 process back up
init q
