SUMMARY = "A Python Parsing Module"
SECTION = "devel/python"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://pyparsing.py;beginline=3;endline=23;md5=06277c41c36d17c011da1050c730a193"

SRCNAME = "pyparsing"

SRC_URI = "https://pypi.python.org/packages/source/p/pyparsing/pyparsing-${PV}.tar.gz"
SRC_URI[md5sum] = "37adec94104b98591507218bc82e7c31"
SRC_URI[sha256sum] = "0007cd3f008eba4a203f1f6b4b133ddc352552c8808b694c88c23db56416e4e4"

S = "${WORKDIR}/${SRCNAME}-${PV}"

inherit setuptools

# avoid "error: option --single-version-externally-managed not recognized"
DISTUTILS_INSTALL_ARGS = "--root=${D} \
    --prefix=${prefix} \
    --install-lib=${PYTHON_SITEPACKAGES_DIR} \
    --install-data=${datadir}"
