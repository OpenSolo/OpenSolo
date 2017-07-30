SUMMARY = "dronekit"
HOMEPAGE = "https://github.com/dronekit/dronekit-python"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file://requirements.txt;md5=d2dfbdbc11136d1e2713f4f391c6b9cf"
PV = "2.4.0"

SRCREV = "v2.4.0"
SRC_URI = "git://github.com/dronekit/dronekit-python/"

S = "${WORKDIR}/git"

inherit setuptools

RDEPENDS_${PN} += "python-pyserial \
                   pymavlink \
                   python-pyparsing \
                  "
