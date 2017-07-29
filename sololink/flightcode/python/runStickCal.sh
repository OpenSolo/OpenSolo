#!/bin/sh

#Comment out the RCTX line in /etc/inittab
sed -i 's/^RCTX.*/#&/g' /etc/inittab

#stop the stm32 process
init q
sleep 1

#update artoo
echo "Press Ctrl+C to write the calibration"
stick-cal.py /dev/ttymxc1

#Uncomment the RCTX line
sed -i 's/.\(RCTX*.\)/\1/g' /etc/inittab

#start the stm32 process back up
init q
