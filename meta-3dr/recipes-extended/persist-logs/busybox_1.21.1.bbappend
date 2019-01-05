FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"

SRC_URI += " \
    file://syslog-patch \
    file://syslog-startup.conf.busybox \
    file://logrotate-syslog.conf \
    "

do_install_prepend() {
    patch -p 1 ${WORKDIR}/syslog < ${WORKDIR}/syslog-patch
}

do_install_append() {
    install -m 0755 ${WORKDIR}/syslog-startup.conf.busybox ${D}${sysconfdir}
    install -m 0644 ${WORKDIR}/logrotate-syslog.conf ${D}${sysconfdir}
}
