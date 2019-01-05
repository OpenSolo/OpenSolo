require recipes-core/images/core-image-minimal.bb

IMAGE_INSTALL += "3dr-initscript parted mtd-utils mtd-utils-ubifs e2fsprogs-mke2fs util-linux dosfstools e2fsprogs-e2fsck"

IMAGE_FSTYPES = "${INITRAMFS_FSTYPES}"

export IMAGE_BASENAME = "3dr-initramfs"
