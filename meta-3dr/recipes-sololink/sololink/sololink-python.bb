SUMMARY = "sololink-python"
HOMEPAGE = "https://github.com/OpenSolo/sololink-python"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file://LICENSE-APACHE;md5=3b83ef96387f14655fc854ddc3c6bd57"

SRCREV = "${AUTOREV}"
SRC_URI = "git://github.com/OpenSolo/sololink-python/"

PV = "${SRCPV}"
S = "${WORKDIR}/git"

inherit setuptools
