include recipes-core/images/core-image-base.bb

# created from image_types_fsl; creates additional logging partition
inherit image_types_3dr

PV = "4.0.0"
VER_NAME = "Open Solo 4.0.0"
BUILD_DATE = "Build Date: $(date "+%Y%m%d%H%M%S")"

do_rootfs[depends] += "virtual/kernel:do_bundle_initramfs"

IMAGE_FEATURES += " \
    debug-tweaks \
    package-management \
"

# Add extra image features
EXTRA_IMAGE_FEATURES += " \
    ssh-server-openssh \
"

IMAGE_INSTALL += " \
    fsl-rc-local \
    gst-fsl-plugin \
    gst-plugins-base \
    gst-plugins-base-app \
    gst-plugins-good-udp \
    gst-plugins-good-rtp \
    gst-plugins-bad-mpegtsdemux \
    libudev \
    python-enum34 \
    python-subprocess \
    python-datetime \
    python-json \
    python-pip \
    python-numpy \
    python-posix-ipc \
    python-monotonic \
    openssh \
    iptables \
    iw \
    wireless-tools \
    hostap-daemon \
    dnsmasq \
    sololink \
    sololink-python \
    rpm \
    util-linux \
    artoo-firmware \
    e2fsprogs-e2fsck \
    dosfstools \
    nano \
    vim \
    openssh-sftp-server \
    3dr-splash \
    persist-logs \
    rsync \
    stm32loader \
    compat-wireless-all \
"

update_config_files() {
    # update /etc/network/interfaces
    mv ${IMAGE_ROOTFS}/etc/network/interfaces-controller \
            ${IMAGE_ROOTFS}/etc/network/interfaces
    rm ${IMAGE_ROOTFS}/etc/network/interfaces-solo
    # AP disabled by default, Station enabled
    sed -i 's/^ApEnable=.*/ApEnable=True/' ${IMAGE_ROOTFS}/etc/sololink.orig
    sed -i 's/^StationEnable=.*/StationEnable=False/' ${IMAGE_ROOTFS}/etc/sololink.orig
    # Create golden config files
    mv ${IMAGE_ROOTFS}/etc/hostapd.conf ${IMAGE_ROOTFS}/etc/hostapd.orig
    mv ${IMAGE_ROOTFS}/etc/wpa_supplicant.conf ${IMAGE_ROOTFS}/etc/wpa_supplicant.orig
    # Change hostname so solo and controller are different
    echo "3dr_controller" > ${IMAGE_ROOTFS}/etc/hostname
    #Filesystem available over USB OTG port
    echo "g_acm_ms file=/dev/mmcblk0p4" >> ${IMAGE_ROOTFS}/etc/modules
    #Clear out the leases file on boot
    sed -i '/test \-d \/var\/lib\/misc\/.*/a \        rm -f \/var\/lib\/misc\/dnsmasq\.leases' ${IMAGE_ROOTFS}/etc/init.d/dnsmasq
    # Mount logging partition
    mkdir ${IMAGE_ROOTFS}/log
    echo "/dev/mmcblk0p4 /log auto defaults 0 2" >> ${IMAGE_ROOTFS}/etc/fstab
    # Blacklist the Golden partition from udev
    echo "/dev/mmcblk0p1" >> ${IMAGE_ROOTFS}/etc/udev/mount.blacklist
    # Put a "Version" file in the root partition
    echo "${PV}" >> ${IMAGE_ROOTFS}/VERSION
    echo ${IMAGE_NAME} >> ${IMAGE_ROOTFS}/VERSION
    echo ${VER_NAME} >> ${IMAGE_ROOTFS}/VERSION
    echo ${BUILD_DATE} >> ${IMAGE_ROOTFS}/VERSION
    
    #Check the artoo version at boot and update if necessary
    #Always run this; it is what clears the "updating system" screen
    echo "#!/bin/sh" > ${IMAGE_ROOTFS}/etc/rcS.d/S60updateArtoo.sh
    echo "/usr/bin/checkArtooAndUpdate.py" >> ${IMAGE_ROOTFS}/etc/rcS.d/S60updateArtoo.sh
    chmod +x ${IMAGE_ROOTFS}/etc/rcS.d/S60updateArtoo.sh
    #1MB max rx socket buffer for video
    echo "net.core.rmem_max=1048576" >> ${IMAGE_ROOTFS}/etc/sysctl.conf

    #Password is TjSDBkAu
    sed 's%^root:[^:]*:%root:I8hkLIWAASD4Q:%' \
           < ${IMAGE_ROOTFS}/etc/shadow \
           > ${IMAGE_ROOTFS}/etc/shadow.new;
    mv ${IMAGE_ROOTFS}/etc/shadow.new ${IMAGE_ROOTFS}/etc/shadow ;

    #pubkey for updater
    mkdir -p ${IMAGE_ROOTFS}/home/root/.ssh
    echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDW+YxPnz9h+qMXWh52H2DwvUwbm4u7LiPcEGp0DtfdEmciCQJDzklNvY0tQgy+xv1C66O4SKUQiNbcWDvW2+5+RsQT2FtzjD9jxnLwZf/O1dK4p8G9sW773/1/z+UnTKDRjuVvuFXcu7a6UjQZ7AYaQZhFRoelJtK5ztmZG7/cv8CYzxBX4EDIY1iah3R3pLNksOVbG+UaOnHPqlHewuAXwkdVzBjb8vuFdXsAaDAD6doECSVhqoaOHysjjrQov+AqKKcMmfZCDbyd6Zl9G8g7q6M7lCNqwUaIA3rK6K3t4pyS0t4oUeiI/mxFjf8S4nLOmWCaYcNCAvWE1uQeniS3" >> ${IMAGE_ROOTFS}/home/root/.ssh/authorized_keys

    #syslog is started in rcS (sololink.bb); the rc6.d entry is left as-is
    rm ${IMAGE_ROOTFS}/etc/rc[0-5].d/[SK]*syslog
    #this was started as S41 (sololink.bb)
    rm ${IMAGE_ROOTFS}/etc/rcS.d/S40networking

    # pick controller's syslog.conf
    rm ${IMAGE_ROOTFS}/etc/syslog.conf.busybox.solo
    mv ${IMAGE_ROOTFS}/etc/syslog.conf.busybox.controller \
       ${IMAGE_ROOTFS}/etc/syslog.conf.busybox

    # pick controller's logrotate-sololink.conf
    rm ${IMAGE_ROOTFS}/etc/logrotate-sololink.conf.solo
    mv ${IMAGE_ROOTFS}/etc/logrotate-sololink.conf.controller \
       ${IMAGE_ROOTFS}/etc/logrotate-sololink.conf

    # the private key corresponding to this public key is added to solo root's  ~/.ssh directory in 3dr-solo.bb
    # this is used by dataFlashMAVLink-to-artoo.py (sololink.bb)
    MAV_DF_RSA_PUB_KEY="
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCs1jMmFt8YXua73/trYpRPBmyqABEsSWGlH2qdYEMG6A/8jzgnbV2ECfYUBWQ+Q/qNjkOLV6VpR6WRN/u0bTAdAC+Zwtt3Qxhuby4gXyMPP/6BUkjgCv4ryI9E4QaFzfVHg2wYxhaEIXGfeF4yTqS0M/MpttewQl9ho6ZIe1giaFYCFayX18MBKbeWv88wfiViDvkaANdX/aClY2/YdxDXY+CXXzxcWFqG+8GCOQKfDwYtqcdAnc0DohnBjjf3VpXhNylay91gb23AVSsUaA+6eynufmkdJutbqbNn/uHTq+aidc6bDuLZKYz4ulRYgeqp6aH/7gZPdHZQPHb//Bed root@3dr_solo
"
    echo "$MAV_DF_RSA_PUB_KEY" >>${IMAGE_ROOTFS}/home/root/.ssh/authorized_keys
}

ROOTFS_POSTPROCESS_COMMAND += "update_config_files"

IMAGE_FSTYPES = "squashfs sdcard"

export IMAGE_BASENAME = "3dr-controller"
