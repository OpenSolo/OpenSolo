#!/bin/bash

# USAGE: builder.sh -a GIT_ACCOUNT -r GIT_REPO -b GIT_BRANCH -b BUILD_MACHINE
    
# EXAMPLE: builder.sh -a OpenSolo -r 3dr-arm-yocto-bsp -b Master
#   These are also the defaults that will be used if options are not specified

# EXAMPLE: builder.sh -a Pedals2Paddles -r 3dr-arm-yocto-bsp -b v0.1.0
#   This will use Matt's fork with a branch named v0.1.0

# Defaults if options are not set from command line set
GIT_ACCOUNT=OpenSolo
GIT_REPO=3dr-arm-yocto-bsp
GIT_BRANCH=master
BUILD_MACHINE=both


# Check command line options for git account, repo, and branch.
while getopts a:r:b:m: option
do
 case ${option}
 in
 a) GIT_ACCOUNT=${OPTARG};;
 r) GIT_REPO=${OPTARG};;
 b) GIT_BRANCH=${OPTARG};;
 m) BUILD_MACHINE=$${OPTARG};;
 esac
done

# Promt for what is about to execute
echo
echo 
echo "Ready to initialize the "$GIT_ACCOUNT $GIT_REPO" repo using branch "$GIT_BRANCH
echo
read -p "This is your last chance to say no. Proceed with build? (y/n):" choice
echo
case "$choice" in 
  y|Y ) echo "Yes! Proceeding with build.";;
  n|N ) echo "No? Fine. Aborting build.." && exit 1;;
  * ) echo "Invalid response. Quit pushing my buttons. Aborting build." && exit 1;;
esac
echo

#Do it.
/vagrant/alt_sync.sh

if [ ! $? -eq 0 ]
then
    exit 1
fi

export MACHINE=imx6solo-3dr-1080p
EULA=1 source ./setup-environment build

if [ ! $? -eq 0 ]
then
    exit 1
fi

#TIP: how to build just one bit, such as the pixhawk firmware from OpenSolo/meta-3dr/recipes-firmware/pixhawk/pixhawk-firmware_1.3.1.bb :
#assuming you've run the 'export MACHINE...' and 'source ./setup...' commands first, and are in /solo-build-alt/build/ folder as a result:
#bitbake -c clean pixhawk-firmware
#bitbake pixhawk-firmware
#or verbose:
#bitbake pixhawk-firmware -v
#TIP: -k means continue-after-error-for-as-much-as-possible

MACHINE=imx6solo-3dr-1080p bitbake 3dr-solo -c clean -f -k
if [ ! $? -eq 0 ]
then
    exit 1
fi

MACHINE=imx6solo-3dr-artoo bitbake 3dr-controller -c clean -f -k
if [ ! $? -eq 0 ]
then
    exit 1
fi

MACHINE=imx6solo-3dr-1080p bitbake 3dr-solo
if [ ! $? -eq 0 ]
then
    exit 1
fi

MACHINE=imx6solo-3dr-artoo bitbake 3dr-controller
if [ ! $? -eq 0 ]
then
    exit 1
fi

#TIPS:
# Copy the relevant files to a date/time stamped completed directory in the git repo folder for easy access (on git ignore list).
# Make an MD5sum of each as is required for the Solo and Controller to accept the files.
# The tar.gz and the .md5 go directly in the /log/updates/ directory on the solo and/or controller.
NEW_DIR=/vagrant/"completed_$(date +%F_%H-%M)"
mkdir -p $NEW_DIR
cd $NEW_DIR

cp /solo-build-alt/build/tmp-eglibc/deploy/images/imx6solo-3dr-1080p/3dr-solo.tar.gz $NEW_DIR
md5sum 3dr-solo.tar.gz > 3dr-solo.tar.gz.md5

cp /solo-build-alt/build/tmp-eglibc/deploy/images/imx6solo-3dr-artoo/3dr-controller.tar.gz $NEW_DIR
md5sum 3dr-controller.tar.gz > 3dr-controller.tar.gz.md5

ls -lh $NEW_DIR

echo
echo "All build files located in below directories of the Vagrant virtual machine (squashfs, uImage, kernel, u-boot, dtb file, initramfs, rootfs.cpio, etc)"
echo /solo-build-alt/build/tmp-eglibc/deploy/images/imx6solo-3dr-1080p/
echo /solo-build-alt/build/tmp-eglibc/deploy/images/imx6solo-3dr-artoo/

