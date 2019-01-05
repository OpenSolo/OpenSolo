SUMMARY = "stm32loader.py for bootloading the stm32"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file:///vagrant/LICENSE-APACHE;md5=3b83ef96387f14655fc854ddc3c6bd57"

SRCREV = "${AUTOREV}"
SRC_URI = "git:///vagrant/;protocol=file"

S = "${WORKDIR}/git/stm32loader"

FILES_${PN} += "${bindir}/"

do_install () {
	install -d ${D}${bindir}

	install -m 0755 ${S}/stm32loader.py ${D}${bindir}
}
