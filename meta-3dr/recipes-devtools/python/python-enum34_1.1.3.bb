DESCRIPTION = "backport of Python 3.4's enum package"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://enum/LICENSE;md5=0a97a53a514564c20efd7b2e8976c87e"

PR = "r0"

SRCNAME = "enum34"
SRC_URI = "https://pypi.python.org/packages/source/e/${SRCNAME}/${SRCNAME}-${PV}.tar.gz"
SRC_URI[md5sum] = "f31c81947ff8e54ec0eb162633d134ce"
SRC_URI[sha256sum] = "865506c22462236b3a2e87a7d9587633e18470e7a93a79b594791de2d31e9bc8"

S = "${WORKDIR}/${SRCNAME}-${PV}"

inherit setuptools

DEPENDS += " python-pip "
