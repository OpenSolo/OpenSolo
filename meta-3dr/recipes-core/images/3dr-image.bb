include recipes-core/images/core-image-base.bb

IMAGE_FEATURES += "debug-tweaks"

SOC_EXTRA_IMAGE_FEATURES ?= "package-management"

# Add extra image features
EXTRA_IMAGE_FEATURES += " \
    ${SOC_EXTRA_IMAGE_FEATURES} \
    ssh-server-openssh \
"

IMAGE_INSTALL += " \
    packagegroup-fsl-gstreamer \
    crda \
    python-pip \
    openssh \
    hostap-daemon \
    iw \
    wireless-tools \
    opkg \
    i2c-tools \
    pciutils \
    dpkg \
    dhcp-server \
    sololink \
"

export IMAGE_BASENAME = "3dr-image"

