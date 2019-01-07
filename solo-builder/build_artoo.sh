#!/bin/bash
set -e


rm -rf /vagrant/artoo/artoo.bin
cd /vagrant/artoo
tup
if [ ! $? -eq 0 ]; then
    exit 1
fi

# Copy new Artoo STM32 FW to Artoo FW Bitbake recipe
cp /vagrant/artoo/artoo.bin /vagrant/meta-3dr/recipes-firmware/artoo/files
