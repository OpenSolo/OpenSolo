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

MACHINE=imx6solo-3dr-1080p bitbake 3dr-solo
MACHINE=imx6solo-3dr-artoo bitbake 3dr-controller
