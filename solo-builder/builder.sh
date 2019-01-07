#!/bin/bash

# USAGE: builder.sh -a -m -c -n
# "-a true" will build the Artoo STM32 firmware, and copy the artoo.bin file into the build. Default is true if not specified.
# "-m solo" will build only the copter's IMX
# "-m controller" will build only the controller's IMX
# "-m both" will build both the copter and controller IMX.  Default is both if not specified.
# "-c true" will clean the build recipies prior to beginning the build.  Default is false if not specified.
# "-n true" nuclear option will delete the entire build directory to start from a totally clean slate.  Default is false if not specified.
    

# Defaults if options are not set from command line set
MACHINE_BUILD='both'
ARTOO_BUILD=true
CLEAN_BUILD=false
NUKE_BUILD=false
SCRIPT_MODE=false


# Check command line options for git account, repo, and branch.
while getopts a:m:c:n:s: option
do
 case ${option}
 in
 a) ARTOO_BUILD=${OPTARG};;
 m) MACHINE_BUILD=${OPTARG};;
 c) CLEAN_BUiLD=${OPTARG};;
 n) NUKE_BUILD=${OPTARG};;
 s) SCRIPT_MODE=${OPTARG};;
 esac
done

## If nuke arg true, delete the build directory to start from a clean slate
if $NUKE_BUILD; then
    if ! $SCRIPT_MODE; then
        echo
        read -p "Wipe build directory to star over from a clean slate? (y/n):" choice
        echo
        case "$choice" in 
        y|Y ) ;;
        n|N ) echo "Aborting..." && exit 1;;
        * ) echo "Invalid response. Quit pushing my buttons. Aborting..." && exit 1;;
        esac
        echo
    fi
    echo "Deleting entire build directory. Please wait.."
    echo
    sudo rm -rf /solo-build
    echo
    echo "Build directory nuked."
fi

# Prompt for what is about to execute

if ! $SCRIPT_MODE; then
    echo 
    read -p "Proceed with build? (y/n):" choice
    echo
    case "$choice" in 
    y|Y ) echo "Yes! Proceeding with build.";;
    n|N ) echo "No? Fine. Aborting build.." && exit 1;;
    * ) echo "Invalid response. Quit pushing my buttons. Aborting build." && exit 1;;
    esac
    echo
fi

## Run source_sync.sh script to pull in build sources
/vagrant/solo-builder/source_sync.sh
if [ ! $? -eq 0 ]; then
    exit 1
fi

## Switch to build directory
cd /solo-build


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

#TIP: how to build just one bit, such as the pixhawk firmware from OpenSolo/meta-3dr/recipes-firmware/pixhawk/pixhawk-firmware_1.3.1.bb :
#assuming you've run the 'export MACHINE...' and 'source ./setup...' commands first, and are in /solo-build/build/ folder as a result:
#bitbake -c clean pixhawk-firmware
#bitbake pixhawk-firmware
#or verbose:
#bitbake pixhawk-firmware -v
#TIP: -k means continue-after-error-for-as-much-as-possible

## If -c = true, run the recipe clean commands on everything
if $CLEAN_BUILD; then
    # these clean command/s are very verbose, and return an error code even though the clean works, lets quieten them:
    echo "solo clean started..."
    MACHINE=imx6solo-3dr-1080p bitbake world -c cleansstate -f -k 2>&1 > /dev/null
    echo "...solo clean finished."

    echo "controller clean started..."
    MACHINE=imx6solo-3dr-artoo bitbake world -c cleansstate -f -k 2>&1 > /dev/null
    echo "...controller clean finished"
fi

# clean the solo specific recipies, even with -c true to ensure local changes are picked up
if ! $CLEAN_BUILD; then
    MACHINE=imx6solo-3dr-1080p bitbake -c clean -f -k sololink shotmanager sololink-python pymavlink mavproxy cubeBlack-solo gimbal-firmware 2>&1 > /dev/null
    if [ ! $? -eq 0 ]; then
        exit 1
    fi

    MACHINE=imx6solo-3dr-artoo bitbake -c clean -f -k sololink sololink-python pymavlink mavproxy artoo-firmware stm32loader 2>&1 > /dev/null
    if [ ! $? -eq 0 ]; then
        exit 1
    fi
fi

## if -a arg is true, build the Artoo STM32 firmware and copy artoo.bin to the build.
if $ARTOO_BUILD; then
    /vagrant/solo-builder/build_artoo.sh
    if [ ! $? -eq 0 ]
    then
        exit 1
    fi
fi


## if -m arg is solo or both, build the Solo's IMX
if [ $MACHINE_BUILD = 'solo' ] || [ $MACHINE_BUILD = 'both' ]; then
    MACHINE=imx6solo-3dr-1080p bitbake 3dr-solo
    if [ ! $? -eq 0 ]; then
        exit 1
    fi
fi


## if -m arg is controller or both, build the Controller's IMX
if [ $MACHINE_BUILD = 'controller' ] || [ $MACHINE_BUILD = 'both' ]; then
    MACHINE=imx6solo-3dr-artoo bitbake 3dr-controller
    if [ ! $? -eq 0 ]
    then
        exit 1
    fi
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

if [ $MACHINE_BUILD = 'solo' ] || [ $MACHINE_BUILD = 'both' ]; then
    cp /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-1080p/3dr-solo.tar.gz $NEW_DIR
    md5sum 3dr-solo.tar.gz > 3dr-solo.tar.gz.md5
fi

if [ $MACHINE_BUILD = 'controller' ] || [ $MACHINE_BUILD = 'both' ]; then
    cp /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-artoo/3dr-controller.tar.gz $NEW_DIR
    md5sum 3dr-controller.tar.gz > 3dr-controller.tar.gz.md5
    cp /vagrant/meta-3dr/recipes-firmware/artoo/files/artoo.bin "$NEW_DIR/artoo_$COMP_DATE.bin"
fi

echo
echo "All completed files located in below directories of the Vagrant virtual machine (squashfs, uImage, kernel, u-boot, dtb file, initramfs, rootfs.cpio, etc)"
echo /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-1080p/
echo /solo-build/build/tmp-eglibc/deploy/images/imx6solo-3dr-artoo/

echo
echo "Completed binaries have been copied to the /solo-builder/binaries/ directory:"
ls -lh $NEW_DIR
