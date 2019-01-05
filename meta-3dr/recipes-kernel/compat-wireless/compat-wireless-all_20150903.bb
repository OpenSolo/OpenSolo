include compat-wireless.inc

SRC_URI = " \
	https://www.kernel.org/pub/linux/kernel/projects/backports/2015/09/03/backports-${PV}.tar.xz \
	file://0001-disable_kconf.patch \
	file://0002-define_reinit.patch \
	file://add_db_txt.patch \
	file://japanese_regulatory.patch \
	file://defconfig \
"

COMPAT_WIRELESS_VERSION = "${PV}"

S = "${WORKDIR}/backports-${COMPAT_WIRELESS_VERSION}"

SRC_URI[md5sum] = "f53560aa0cfc006d637a74fd76d2a3af"
SRC_URI[sha256sum] = "bf7707aa9c222e357048431ad5060fb2081a20ec6ef945be6611e962579d5c6e"
