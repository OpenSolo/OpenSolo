SUMMARY = "3DR Logo"

LICENSE = "CLOSED"
SRC_URI = "file://3dr.fb.gz"

FILES_${PN} = "/"

do_install () {
	install -d ${D}/
    gzip -c ${WORKDIR}/3dr.fb > ${WORKDIR}/3dr.fb.gz
    install -m 0644 ${WORKDIR}/3dr.fb.gz ${D}/
}
