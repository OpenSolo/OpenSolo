SUMMARY = "Artoo firmware binary"

LICENSE = "CLOSED"

FILESEXTRAPATHS_prepend := "${THISDIR}/files/:"

# stick-cfg-evt-*.cfg are for use with sololink_config
SRC_URI += "file://stick-cfg-evt-mode1.cfg \
            file://stick-cfg-evt-mode2.cfg \
            file://stick-cfg-evt-default.cfg \
            file://artoo.bin"

firmwaredir = "/firmware"
FILES_${PN} += "${firmwaredir}/"
FILES_${PN} += "${firmwaredir}/cfg"

REPO_NAME = "artoo"
REPO_TAG = "master"
#REPO_TAG = "${PV}"
FILE_EXT = "bin"
FILE_SRC = "artoo_${PV}.${FILE_EXT}"
FILE_DST = "artoo_${PV}.${FILE_EXT}"

do_install () {
    install -d ${D}${firmwaredir}
    install -m 0644 ${WORKDIR}/artoo.bin ${D}${firmwaredir}/${FILE_DST}
    install -d ${D}${firmwaredir}/cfg/
    install -m 0644 ${WORKDIR}/stick-cfg-evt-mode1.cfg ${D}${firmwaredir}/cfg
    install -m 0644 ${WORKDIR}/stick-cfg-evt-mode2.cfg ${D}${firmwaredir}/cfg
    install -m 0644 ${WORKDIR}/stick-cfg-evt-default.cfg ${D}${firmwaredir}/cfg
}
