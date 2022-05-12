#!/bin/bash

## Run source_sync.sh script to pull in build sources
/vagrant/solo-builder/source_sync.sh
if [ ! $? -eq 0 ]; then
    exit 1
fi

## Switch to build directory
cd /solo-build


## Export machine twice since it's a clean build
export MACHINE=imx6solo-3dr-1080p
EULA=1 source ./setup-environment build
export_return=$?
if [  $export_return -eq 0 ]; then
    echo "Build environment ready"
elif [  $export_return -eq 2 ]; then
    # Automatic restart as required
    echo "Restarting setup environment"
    export MACHINE=imx6solo-3dr-1080p
    EULA=1 source ./setup-environment build
    if [ ! $? -eq 0 ]; then
        echo "Machine export error."
        exit 1
    fi
else
    echo "Machine export error."
    exit 1
fi

## Build Solo specific recipes.  Dump most of the running output so the travis log doesn't explode






MACHINE=imx6solo-3dr-1080p bitbake 3dr-solo
if [ ! $? -eq 0 ]; then
    exit 1
fi

MACHINE=imx6solo-3dr-artoo bitbake 3dr-controller
if [ ! $? -eq 0 ]
then
    exit 1
fi


# Copy the relevant files to a date/time stamped completed directory in the git repo folder for easy access (on git ignore list).
# Make an MD5sum of each as is required for the Solo and Controller to accept the files.
# The tar.gz and the .md5 go directly in the /log/updates/ directory on the solo and/or controller.
# Also copies the artoo.bin STM32 FW file used in the build.
COMP_DATE="$(date +%F_%H-%M)"
COMP_DIR="completed_$(date +%F_%H-%M)"
NEW_DIR=/vagrant/solo-builder/binaries/$COMP_DIR
echo $COMP > /tmp/COMP.txt
mkdir -p $NEW_DIR
cd $NEW_DIR

cp /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-1080p/3dr-solo.tar.gz $NEW_DIR
md5sum 3dr-solo.tar.gz > 3dr-solo.tar.gz.md5
cp /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-artoo/3dr-controller.tar.gz $NEW_DIR
md5sum 3dr-controller.tar.gz > 3dr-controller.tar.gz.md5
cp /vagrant/meta-3dr/recipes-firmware/artoo/files/artoo.bin "$NEW_DIR/artoo_$COMP_DATE.bin"

echo
echo "All completed files located in below directories of the Vagrant virtual machine (squashfs, uImage, kernel, u-boot, dtb file, initramfs, rootfs.cpio, etc)"
echo /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-1080p/
echo /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-artoo/
cp /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-1080p/* /vagrant
cp /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-artoo/* /vagrant
echo
echo "Completed binaries have been copied to the /solo-builder/binaries/ directory and /vagrant"
ls -lh $NEW_DIR
ls -lh /vagrant
