SUMMARY = "Axon firmware binary"

LICENSE = "CLOSED"

FILESEXTRAPATHS_prepend := "${THISDIR}/files/:"

SRC_URI += "file://gimbal_firmware_1.3.6.ax"

firmwaredir = "/firmware"
FILES_${PN} += "${firmwaredir}/"

REPO_NAME = "solo-gimbal"
REPO_TAG = "master"
#REPO_TAG = "v${PV}"
FILE_EXT = "ax"
FILE_SRC = "gimbal_firmware_${PV}.${FILE_EXT}"
FILE_DST = "gimbal_firmware_${PV}.${FILE_EXT}"

do_install () {
    install -d ${D}${firmwaredir}
    install -m 0644 ${WORKDIR}/gimbal_firmware_1.3.6.ax ${D}${firmwaredir}/
}
