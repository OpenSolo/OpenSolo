FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"

SRC_URI += " \
    file://bootlogd \
    file://logrotate-boot.conf \
    file://rcS-default-patch \
    "

do_install_prepend() {
    patch -p 1 ${WORKDIR}/rcS-default < ${WORKDIR}/rcS-default-patch
}

do_install_append() {
    install -d ${D}${sysconfdir}/init.d
    install -m 0755 ${WORKDIR}/bootlogd ${D}${sysconfdir}/init.d/
    install -m 0644 ${WORKDIR}/logrotate-boot.conf ${D}${sysconfdir}
}
