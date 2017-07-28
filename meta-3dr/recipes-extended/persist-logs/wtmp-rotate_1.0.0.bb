SUMMARY = "wtmp file rotation"

LICENSE = "CLOSED"

FILESEXTRAPATHS := "${THISDIR}/${PN}:"

SRC_URI = " \
    file://wtmp_rotate \
    file://logrotate-wtmp.conf \
    "

FILES_${PN} = "/"

do_install() {
    install -d ${D}${sysconfdir}/init.d
    install -d ${D}${sysconfdir}/rcS.d
    install -m 0755 ${WORKDIR}/wtmp_rotate ${D}${sysconfdir}/init.d/
    install -m 0644 ${WORKDIR}/logrotate-wtmp.conf ${D}${sysconfdir}
    ln -s ../init.d/wtmp_rotate ${D}${sysconfdir}/rcS.d/S42wtmp_rotate
}
