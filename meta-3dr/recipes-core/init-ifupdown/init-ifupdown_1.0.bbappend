FILESEXTRAPATHS_prepend := "${THISDIR}/${PN}:"
PRINC := "${@int(PRINC) + 2}"

SRC_URI_append = " file://interfaces-controller \
		   file://interfaces-solo"

do_install_append() {
	install -m 0644 ${WORKDIR}/interfaces-controller ${D}${sysconfdir}/network/
	install -m 0644 ${WORKDIR}/interfaces-solo ${D}${sysconfdir}/network/
}
