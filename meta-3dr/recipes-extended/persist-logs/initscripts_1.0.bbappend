FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"

SRC_URI += " \
    file://logrotate-dmesg.conf \
    file://dmesg.sh-patch \
    "

do_install_prepend() {
    patch -p 1 ${WORKDIR}/dmesg.sh < ${WORKDIR}/dmesg.sh-patch
}

do_install_append() {
    install -m 0644 ${WORKDIR}/logrotate-dmesg.conf ${D}${sysconfdir}
}
