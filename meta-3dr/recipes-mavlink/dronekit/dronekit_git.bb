SUMMARY = "dronekit"
HOMEPAGE = "https://github.com/dronekit/dronekit-python"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file://LICENSE;md5=d2794c0df5b907fdace235a619d80314"

SRCREV = "v2.4.0"
SRC_URI = "git://github.com/dronekit/dronekit-python"

PV = "2.4.0"
S = "${WORKDIR}/git"

inherit setuptools

RDEPENDS_${PN} += "python-pyserial \
                   pymavlink \
                   python-pyparsing \
                  "
