#!/bin/bash

# USAGE: builder.sh -a GIT_ACCOUNT -r GIT_REPO -b GIT_BRANCH
    
# EXAMPLE: builder.sh -a OpenSolo -r 3dr-arm-yocto-bsp -b Master
#   These are also the defaults that will be used if options are not specified

# EXAMPLE: builder.sh -a Pedals2Paddles -r 3dr-arm-yocto-bsp -b v0.1.0
#   This will use Matt's fork with a branch named v0.1.0

# Defaults if options are not set from command line set
GIT_ACCOUNT=OpenSolo
GIT_REPO=3dr-arm-yocto-bsp
GIT_BRANCH=master

# Check command line options for git account, repo, and branch.
while getopts a:r:b: option
do
 case ${option}
 in
 a) GIT_ACCOUNT=${OPTARG};;
 r) GIT_REPO=${OPTARG};;
 b) GIT_BRANCH=${OPTARG};;
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
cd /solo-build
repo init -u https://github.com/$GIT_ACCOUNT/$GIT_REPO.git -b $GIT_BRANCH
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


# Copy the relevant files to a date/time stamped completed directory in the git repo folder for easy access (on git ignore list).
# Make an MD5sum of each as is required for the Solo and Controller to accept the files.
# The tar.gz and the MD5 go directly in the /log/updates/ directory on the solo and/or controller.
NEW_DIR=/vagrant/"completed_$(date +%F_%H-%M)"
mkdir -p $NEW_DIR
cp /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-1080p/3dr-solo.tar.gz $NEW_DIR
cp /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-artoo/3dr-controller.tar.gz $NEW_DIR
cd $NEW_DIR
md5sum 3dr-solo.tar.gz > 3dr-solo.tar.gz.md5
md5sum 3dr-controller.tar.gz > 3dr-controller.tar.gz.md5

echo
echo "*****************************"
echo "Completed tar.gz and md5 checksum files for Solo and/or Controller are in a date-time stamped directory in your github directory."
ls -lh $NEW_DIR

echo
echo
echo "All build files located in below directories of the Vagrant virtual machine (squashfs, uImage, kernel, u-boot, dtb file, initramfs, rootfs.cpio, etc)"
echo /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-1080p/
echo /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-artoo/

