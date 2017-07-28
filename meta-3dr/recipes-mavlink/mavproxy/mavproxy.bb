SUMMARY = "This is a MAVLink ground station written in python."
HOMEPAGE = "http://tridge.github.io/MAVProxy/"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file://COPYING.txt;md5=3c34afdc3adf82d2448f12715a255122"

PV = "1.4.20-solo"

SRCREV = "sololink_v1.1.17"
SRC_URI = "git://git@github.com/OpenSolo/MAVProxy.git;protocol=ssh"

S = "${WORKDIR}/git"

inherit setuptools

RDEPENDS_${PN} += "python-pyserial \
                   pymavlink \
                   python-pyparsing \
                  "
