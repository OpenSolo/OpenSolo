# Copyright (C) 2013-14 3DR

require recipes-kernel/linux/linux-imx.inc
require recipes-kernel/linux/linux-dtb.inc

DEPENDS += "lzop-native bc-native"

COMPATIBLE_MACHINE = "(mx6)"

SRCREV = "sololink_v1.3.0-5"
SRC_URI = "git://git@github.com/OpenSolo/imx6-linux;protocol=ssh"

SRC_URI += "\
    https://www.kernel.org/pub/linux/kernel/projects/rt/3.10/older/patch-3.10.17-rt12.patch.bz2;name=rt-patch1 \
	file://0001-fix-build.patch \
	file://0002-fix-build-with-rt-enabled.patch \
	file://0003-no-split-ptlocks.patch \
	file://aufs3-base.patch \
	file://aufs3-kbuild.patch \
	file://aufs3-standalone.patch \
	file://aufs3-mmap.patch \
	file://aufs_type.h \
	file://aufs \
	file://0001-dts-changes-to-add-uart5.patch \
	file://0004-uart-no-dma.patch \
"

SRC_URI[rt-patch1.md5sum] = "77a28c8b20b01f280dcd860e606a6edd"
SRC_URI[rt-patch1.sha256sum] = "ce219268f08eecccb39ff2b5be83657d53ca67cb1c6b81021494075197190351"

LOCALVERSION = "-1.0.0_ga"

IMX_TEST_SUPPORT = "y"

INITRAMFS_IMAGE = "3dr-initramfs"

do_configure_prepend() {
   # In some cases we'll use a different defconfig
   # example is manufacturing image which uses imx_v7_mfg_defconfig
   # however need way to change it back during daily build

   if [ -z "${FSL_KERNEL_DEFCONFIG}" ] ; then
       echo " defconfig from local.conf not set"
       fsl_defconfig='imx6solo_defconfig'
   else
       echo " Use local.conf for defconfig to set"
       fsl_defconfig=${FSL_KERNEL_DEFCONFIG}
   fi

   # check that defconfig file exists
   if [ ! -e "${S}/arch/arm/configs/$fsl_defconfig" ]; then
       fsl_defconfig='imx6solo_defconfig'
   fi


    cp ${S}/arch/arm/configs/${fsl_defconfig} ${S}/.config
    cp ${S}/arch/arm/configs/${fsl_defconfig} ${S}/../defconfig

    cp ${WORKDIR}/aufs_type.h ${S}/include/uapi/linux
    cp -r ${WORKDIR}/aufs ${S}/fs/
}

# copy zImage to deploy directory
# update uImage with defconfig ane git info in name
# this is since build script can build multiple ways
# and will overwrite previous builds

do_deploy_append () {
    install -d ${DEPLOY_DIR_IMAGE}

    if [ -z "${FSL_KERNEL_DEFCONFIG}" ] ; then
       fsl_defconfig='imx6solo_defconfig'
    else
       fsl_defconfig=${FSL_KERNEL_DEFCONFIG}
       # check that defconfig file exists
       if [ ! -e "${S}/arch/arm/configs/${FSL_KERNEL_DEFCONFIG}" ]; then
           fsl_defconfig='imx6solo_defconfig'
       fi
    fi

    install  arch/arm/boot/uImage ${DEPLOY_DIR_IMAGE}/uImage_$fsl_defconfig
    install  arch/arm/boot/zImage ${DEPLOY_DIR_IMAGE}/zImage_$fsl_defconfig
}
