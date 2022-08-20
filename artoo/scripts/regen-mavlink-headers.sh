#!/bin/sh

#
# change directories into the mavlink-solo repo,
# so we can use `python -m`, which relies on the layout
# of the local relative path.
#
# make note of our current directory so we know where to direct the generator output.
#

ARTOODIR=/vagrant/artoo
MAVSOLO=/vagrant/modules/mavlink-solo

echo "Removing old includes"
rm -rf ARTOODIR/src/mavlink/c_library/

echo "Generating C code"

# can pass in mavlink-solo location to override default
if [ "$#" -eq  "1" ]
  then
MAVSOLO=$1
fi

pushd ${MAVSOLO}
mavgen.py --lang C --wire-protocol 2.0 -o ${ARTOODIR}/src/mavlink/c_library  message_definitions/v1.0/ardupilotmega.xml
popd
