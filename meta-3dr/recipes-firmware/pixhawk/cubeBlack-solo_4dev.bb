SUMMARY = "ArduCopter 3.7 firmware for cube"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file://${THISDIR}/files/COPYING.txt;md5=d32239bcb673463ab874e80d47fae504"

FILESEXTRAPATHS_prepend := "${THISDIR}/files/:"

SRC_URI += "file://arducopter.apj"
SRC_URI += "file://resetParams"

FILES_${PN} += "/firmware"
firmwaredir = "/firmware"

do_install () {
    install -d ${D}${firmwaredir}
    install -m 0644 ${WORKDIR}/arducopter.apj ${D}${firmwaredir}
    install -m 0644 ${WORKDIR}/resetParams ${D}${firmwaredir}
}
