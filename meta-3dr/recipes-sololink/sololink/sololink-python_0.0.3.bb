SUMMARY = "sololink-python"
HOMEPAGE = "https://github.com/OpenSolo/sololink-python"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file://requirements.txt;md5=dc90368fff309dbbef652a1fab32f191"

PROVIDES += "${PN}_${PV}"

SRCREV = "f89466ccd7addae49cf800fdf5c67ed6bdff47d6"
SRC_URI = "git://github.com/OpenSolo/sololink-python/"

S = "${WORKDIR}/git"

inherit setuptools
