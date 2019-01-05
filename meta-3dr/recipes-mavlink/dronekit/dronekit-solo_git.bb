SUMMARY = "dronekit-solo"
HOMEPAGE = "https://github.com/dronekit/dronekit-python-solo"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file://requirements.txt;md5=b6106de10adcc12b60d3cf95b9017b7f"
PV = "1.2.0"

SRCREV = "1.2.0"
SRC_URI = "git://github.com/dronekit/dronekit-python-solo/"

S = "${WORKDIR}/git"

inherit setuptools

RDEPENDS_${PN} += "python-pyserial \
                   pymavlink \
                   python-pyparsing \
                   dronekit \
                  "
