#!/bin/bash
cp /vagrant/github_token ~/.ssh/github_token

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

# tip:
echo look below for squashfs, uImage, kernel, u-boot, dtb file, initramfs, rootfs.cpio, etc 
echo vagrant ssh
echo ls /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-1080p/
echo ls /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-artoo/

