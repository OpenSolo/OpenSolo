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
MACHINE=imx6solo-3dr-1080p bitbake sololink shotmanager sololink-python pymavlink mavproxy cubeBlack-solo gimbal-firmware  2>&1 |  grep -v 'pid'
if [ ! $? -eq 0 ]; then
    exit 1
fi

MACHINE=imx6solo-3dr-artoo bitbake sololink sololink-python pymavlink mavproxy artoo-firmware stm32loader  2>&1 |  grep -v 'pid'
if [ ! $? -eq 0 ]
then
    exit 1
fi

## Build Artoo STM32 FW
cd /vagrant/artoo
tup
if [ ! $? -eq 0 ]; then
    exit 1
fi


