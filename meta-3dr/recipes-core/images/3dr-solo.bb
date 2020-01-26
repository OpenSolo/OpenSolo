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
    gst-plugins-bad-mpegtsmux \
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
    shotmanager \
    rpm \
    util-linux \
    arducopter \
    gimbal-firmware \
    e2fsprogs-e2fsck \
    dosfstools \
    nano \
    vim \
    openssh-sftp-server \
    persist-logs \
    rsync \
    compat-wireless-all \
"

update_config_files() {
    # update /etc/network/interfaces
    mv ${IMAGE_ROOTFS}/etc/network/interfaces-solo \
            ${IMAGE_ROOTFS}/etc/network/interfaces
    rm ${IMAGE_ROOTFS}/etc/network/interfaces-controller
    # AP disabled by default, Station enabled
    sed -i 's/^ApEnable=.*/ApEnable=False/' ${IMAGE_ROOTFS}/etc/sololink.orig
    sed -i 's/^StationEnable=.*/StationEnable=True/' ${IMAGE_ROOTFS}/etc/sololink.orig
    # Create golden config files
    mv ${IMAGE_ROOTFS}/etc/hostapd.conf ${IMAGE_ROOTFS}/etc/hostapd.orig
    mv ${IMAGE_ROOTFS}/etc/wpa_supplicant.conf ${IMAGE_ROOTFS}/etc/wpa_supplicant.orig
    # Solo-specific startup
    ln -s ../init.d/pixhawk ${IMAGE_ROOTFS}/etc/rcS.d/S60pixhawk
    ln -s ../init.d/updateGimbal.sh ${IMAGE_ROOTFS}/etc/rcS.d/S62updateGimbal.sh
    # Change hostname so solo and controller are different
    echo "3dr_solo" > ${IMAGE_ROOTFS}/etc/hostname
    #Filesystem available over USB OTG port
    echo "g_acm_ms file=/dev/mmcblk0p4" >> ${IMAGE_ROOTFS}/etc/modules
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

    # pick solo's syslog.conf
    rm ${IMAGE_ROOTFS}/etc/syslog.conf.busybox.controller
    mv ${IMAGE_ROOTFS}/etc/syslog.conf.busybox.solo \
       ${IMAGE_ROOTFS}/etc/syslog.conf.busybox

    # pick solo's logrotate-sololink.conf
    rm ${IMAGE_ROOTFS}/etc/logrotate-sololink.conf.controller
    mv ${IMAGE_ROOTFS}/etc/logrotate-sololink.conf.solo \
       ${IMAGE_ROOTFS}/etc/logrotate-sololink.conf

    # the public key corresponding to this private key is added to authorized_keys file in 3dr-controller.bb
    # this is used by dataFlashMAVLink-to-artoo.py (sololink.bb)
    ID_XFER_FILEPATH="${IMAGE_ROOTFS}/home/root/.ssh/id_rsa-mav-df-xfer"
    cat >>$ID_XFER_FILEPATH <<'EOF'
-----BEGIN RSA PRIVATE KEY-----
MIIEpgIBAAKCAQEArNYzJhbfGF7mu9/7a2KUTwZsqgARLElhpR9qnWBDBugP/I84
J21dhAn2FAVkPkP6jY5Di1elaUelkTf7tG0wHQAvmcLbd0MYbm8uIF8jDz/+gVJI
4Ar+K8iPROEGhc31R4NsGMYWhCFxn3heMk6ktDPzKbbXsEJfYaOmSHtYImhWAhWs
l9fDASm3lr/PMH4lYg75GgDXV/2gpWNv2HcQ12Pgl188XFhahvvBgjkCnw8GLanH
QJ3NA6IZwY4391aV4TcpWsvdYG9twFUrFGgPunsp7n5pHSbrW6mzZ/7h06vmonXO
mw7i2SmM+LpUWIHqqemh/+4GT3R2UDx2//wXnQIDAQABAoIBAQCDvkaAuyBU8EnK
XYHEqgDId+oubxyn+Etw1RCsYyrUQeGlrvmrvAZzVjB3tGBjwedjLVS5CxbvuAgx
OE4piq0I/hJKjyhAsSkXTLIJRNtxjWMO6kzYUijJ8PecFjalmYdken3UKHITR3bX
iqWqjR2oqoyoeFHSbdVMlLR0PWjB2Cs1lxTlakrLF+yG6MoqJjBW3tBHto0EROg6
OZ6NBBpZaWl/LmvRkX26OxBWWlQQyzXITREIQsiwisfiaio89/m3O4ulGwMXAZDS
B7XYP+v+F38PlNTZm8dOkIAeKCXHppfRmSqaXEfd5Q1JtxdtY8tNroXN5SlzXHS6
j2/RtT31AoGBANYKKXQWlL9icJIJxIl4Lh+W6d9qgeobVfXftQ3aACE0Uy69P815
PTiffniaMFNaWAkDL6PHPxv9sQBPwI+Pi+vbR+HtRpS8zI1mWGlATwbWnWn8rv03
uZBWZoF/yqxqUjjBr+8i/NNKIL6UCEbY1jnaImpYJpMB50EIcHZxSQevAoGBAM64
N5ntJ4ZPnwSqu8CdFW4xG8nDtpjE1OeUhYUxE7jCjqM+bV+VyMSl4psP4Sa3pe+3
YQv4kE7pLMiXsHmWF2gmfXEGrTLHC0APk0M0ZURoQ2AMHDy4zc+6Cg6hh3AS8Ttp
6Fr8H0VXM8Exi3lSvfdztIaEEiusbdxED2jNMZxzAoGBAMInRaMAOL3CVcqjAZyR
X4VYJ515x47MbRUzb9C4xxVXmXz0PkPsjhQm2Vocw2lYsjK6qSQvQJfrb/uQXGPd
Glc/+dx+l1+kQwigpeITa5wQYYoao8EeIz1Cooklmnr7lsnVJ/oMCrq+qyU0sq1R
VEH2FPHSNGt1dogPV7SY3l4RAoGBAIYX2Xlv7QOjAnP0jHYVb6FbGbt3ySqwA6t1
HGeZvkFLc1tRU4F9mA53zNbpJhQHbQxi2AD77CBEAVjdjQxR4D0fOp/mxNL7asDT
WaNuiYImYA4dzPNWrarh80QqY8C/iNwRhzf99Ar21gusJ907Xx71X1Uitua9o0YO
oDBLarMhAoGBALrJJLMxFOmpecQ3yybmV9xXvj7+5qO/UMPZiTbnVm1arQUek0UN
wq69pf0PfMts5o8YLEmM6Y66oO/Fx8LO/04nBBz4yb0eybW1d4PViXXE8glxSZnH
IPOZ7eN9wAEYTa6FkyTkmRPxGvLBq59gwPtS1dgFNJCpvBeU4w3i8qcJ
-----END RSA PRIVATE KEY-----
EOF
	chmod 600 "$ID_XFER_FILEPATH"

    MAV_DF_RSA_PUB_KEY="
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCs1jMmFt8YXua73/trYpRPBmyqABEsSWGlH2qdYEMG6A/8jzgnbV2ECfYUBWQ+Q/qNjkOLV6VpR6WRN/u0bTAdAC+Zwtt3Qxhuby4gXyMPP/6BUkjgCv4ryI9E4QaFzfVHg2wYxhaEIXGfeF4yTqS0M/MpttewQl9ho6ZIe1giaFYCFayX18MBKbeWv88wfiViDvkaANdX/aClY2/YdxDXY+CXXzxcWFqG+8GCOQKfDwYtqcdAnc0DohnBjjf3VpXhNylay91gb23AVSsUaA+6eynufmkdJutbqbNn/uHTq+aidc6bDuLZKYz4ulRYgeqp6aH/7gZPdHZQPHb//Bed root@3dr_solo
"
	ID_XFER_PUB_FILEPATH="${IMAGE_ROOTFS}/home/root/.ssh/id_rsa-mav-df-xfer.pub"
	echo $MAV_DF_RSA_PUB_KEY >"$ID_XFER_PUB_FILEPATH"
}

ROOTFS_POSTPROCESS_COMMAND += "update_config_files"

IMAGE_FSTYPES = "squashfs sdcard"

export IMAGE_BASENAME = "3dr-solo"
