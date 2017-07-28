DESCRIPTION = "The /init script for 3dr initramfs"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"
SRC_URI = "file://init"

FILES_${PN} = "/"

do_install() {
    install -m 0755 ${WORKDIR}/init ${D}/init
}

