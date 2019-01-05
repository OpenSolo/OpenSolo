#!/bin/sh

#This script takes an updated image and pushes it 
#on to the GOLDEN partition of the SD card, creating a
#new golden image.  This should only be used for
#development and production.

#Make sure we're running on the update partition
BOOTPART=`grep 'boot' /proc/mounts | awk '{print $1}'`

if [ $BOOTPART == "/dev/mmcblk0p1" ]; then
    echo "Already on golden partition"
    exit
else
    echo "Making the update partition the golden partition"
fi;

echo "Unmounting the golden partition"
umount /dev/mmcblk0p1

echo "Creating the golden partition filesystem"
mkfs.vfat /dev/mmcblk0p1 -n GOLDEN

echo "Mounting GOLDEN and copying files from LATEST"
mkdir -p golden
mount /dev/mmcblk0p1 golden
cp -r /mnt/boot/* golden/
umount golden

echo "All done!  Run a factory reset if you'd like."

