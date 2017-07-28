
SRC_URI = "git://git@github.com/OpenSolo/imx6-uboot.git;protocol=ssh"
SRCREV = "solo_v1.0.0"

# save UBOOT_CONFIG as separate names
do_deploy_append() {
    install ${S}/${UBOOT_BINARY} ${DEPLOYDIR}/${UBOOT_IMAGE}_${UBOOT_CONFIG}
}
