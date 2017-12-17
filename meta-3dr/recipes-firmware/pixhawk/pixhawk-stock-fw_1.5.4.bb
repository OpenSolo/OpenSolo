SUMMARY = "Pixhawk stock cube firmware binary"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file://${THISDIR}/files/COPYING.txt;md5=d32239bcb673463ab874e80d47fae504"

firmwaredir = "/firmware/3dr"
FILES_${PN} += "${firmwaredir}/"

REPO_NAME = "ardupilot-solo"
REPO_TAG = "solo-${PV}"
FILE_EXT = "px4"
FILE_SRC = "ArduCopter-v2.${FILE_EXT}"
FILE_DST = "ArduCopter-StockCube-${PV}.${FILE_EXT}"

do_fetch () {

    wget https://github.com/OpenSolo/ardupilot-solo/releases/download/solo-1.5.4/ArduCopter-v2.px4 -O ${WORKDIR}/${FILE_SRC}

}

do_install () {
    install -d ${D}${firmwaredir}
    install -m 0644 ${WORKDIR}/${FILE_SRC} ${D}${firmwaredir}/${FILE_DST}
}
