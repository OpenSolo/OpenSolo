#!/bin/sh

PROG=artoo

VERSION=$(git describe --tags)
DEST=bins

rm -rf ${DEST}
mkdir ${DEST}

cp ${PROG}.elf ${DEST}/${PROG}_${VERSION}.elf
cp ${PROG}.bin ${DEST}/${PROG}_${VERSION}.bin
cp ${PROG}.hex ${DEST}/${PROG}_${VERSION}.hex

echo copied ${VERSION} binaries to ${DEST}
