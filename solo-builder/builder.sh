#!/bin/bash

cd /solo-build

if [ -z "$1" ]; then
    BRANCH=master
else
    BRANCH=$1
fi

echo "Initializing repo with branch $BRANCH"

#repo init -u https://github.com/OpenSolo/3dr-arm-yocto-bsp.git -b $BRANCH
repo init -u https://github.com/OpenSolo/3dr-arm-yocto-bsp.git 
repo sync

export MACHINE=imx6solo-3dr-1080p
EULA=1 source ./setup-environment build

# -k means continue-after-error-for-as-much-as-possible
MACHINE=imx6solo-3dr-1080p bitbake 3dr-solo -k
MACHINE=imx6solo-3dr-artoo bitbake 3dr-controller -k

# other options/examples, how to build just one bit, such as the pixhawk firmware from OpenSolo/meta-3dr/recipes-firmware/pixhawk/pixhawk-firmware_1.3.1.bb :
# assuming you've run the 'export MACHINE...' and 'source ./setup...' commands first, and are in /solo-build/build/ folder as a result:
#bitbake -c clean pixhawk-firmware
#bitbake pixhawk-firmware
#or verbose:
#bitbake pixhawk-firmware -v

# tip:
echo look below for squashfs, uImage, kernel, u-boot, dtb file, initramfs, rootfs.cpio, etc 
echo vagrant ssh
echo ls /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-1080p/
echo ls /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-artoo/

