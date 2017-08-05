SUMMARY = "Pixhawk firmware binary"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file://${THISDIR}/files/COPYING.txt;md5=d32239bcb673463ab874e80d47fae504"

firmwaredir = "/firmware"
FILES_${PN} += "${firmwaredir}/"

REPO_NAME = "ardupilot-solo"
#REPO_TAG = "solo-${PV}"
REPO_TAG = "solo-master"
FILE_EXT = "px4"
FILE_SRC = "ArduCopter-v2.${FILE_EXT}"
FILE_DST = "ArduCopter-${PV}.${FILE_EXT}"

do_fetch () {

    # TODO - smart fetch the correct version of the formware to match the repo-tag requested or something
    # for now, get the LATEST MASTER PX4v2 ( ie pixhawk1 or 2.0(solo) firmware from ArduPilot build system:
    wget http://firmware.ap.ardupilot.org/Copter/stable/PX4/ArduCopter-v3.px4 -O ${WORKDIR}/${FILE_SRC}
    # or simply fake it with a zero-length file if the curl fails for some reason..:
    #touch ${WORKDIR}/${FILE_SRC}
}

do_install () {
    install -d ${D}${firmwaredir}
    install -m 0644 ${WORKDIR}/${FILE_SRC} ${D}${firmwaredir}/${FILE_DST}
}

wget -O ac.px4 http://firmware.ap.ardupilot.org/Copter/stable/PX4/ArduCopter-v3.px4