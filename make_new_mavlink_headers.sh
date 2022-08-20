#!/bin/bash

echo "this script designed to be run inside the vagrant machine"

cd /vagrant/sololink/flightcode/mavlink && ./generate /vagrant/modules/mavlink-solo
cd /vagrant/artoo/src/mavlink           && /vagrant/sololink/flightcode/mavlink/generate /vagrant/modules/mavlink-solo

# this is another equivalent way to do the artoo ones:
#/vagrant/artoo/scripts/regen-mavlink-headers.sh

# tip, we have XML message definitions in:
#/vagrant/modules/mavlink-solo/message_definitions/v1.0/
# and 
#/vagrant/modules/ardupilot-solo/libraries/GCS_MAVLink/message_definitions/
# 
#this script re-builds using the first of them, and copies the result into two palces as they xml is suposed to be kept insync betwene them


#we also have two sets of generated outputs that dont necessarily match with the above two sources, so we just keep them in sync as well..
# /vagrant/artoo/src/mavlink/c_library/ 
# /vagrant/sololink/flightcode/mavlink/c_library/



