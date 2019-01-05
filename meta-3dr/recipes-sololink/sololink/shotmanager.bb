SUMMARY = "shotmanager"
HOMEPAGE = "https://github.com/OpenSolo/shotmanager"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file:///vagrant/LICENSE-APACHE;md5=3b83ef96387f14655fc854ddc3c6bd57"

SRCREV = "${AUTOREV}"
SRC_URI = "git:///vagrant/;protocol=file"
PV = "${SRCPV}"
S = "${WORKDIR}/git/shotmanager"

RDEPENDS_${PN} += "dronekit dronekit-solo"

FILES_${PN} += "/"
FILES_${PN} += "${bindir}/"
FILES_${PN} += "${sysconfdir}/"

do_compile () {
    echo "# auto-generated `date`" > shotManager_version.py
    echo 'VERSION = "4-DEV"' >> shotManager_version.py
}

do_install () {
    install -d ${D}/
    install -d ${D}${bindir}
    install -d ${D}${sysconfdir}

    # Only the .orig file is installed; it is the "golden config" that
    # configinit uses to create shotmanager.conf (and md5) on first boot
    install -m 0644 ${S}/config/shotmanager.orig ${D}${sysconfdir}

    install -m 0755 ${S}/appManager.py ${D}${bindir}
    install -m 0755 ${S}/app_packet.py ${D}${bindir}
    install -m 0755 ${S}/buttonManager.py ${D}${bindir}
    install -m 0755 ${S}/cable_cam.py ${D}${bindir}
    install -m 0755 ${S}/cableController.py ${D}${bindir}
    install -m 0755 ${S}/camera.py ${D}${bindir}
    install -m 0755 ${S}/catmullRom.py ${D}${bindir}
    install -m 0755 ${S}/extFunctions.py ${D}${bindir}
    install -m 0755 ${S}/extSettings.conf ${D}${bindir}
    install -m 0755 ${S}/flyController.py ${D}${bindir}
    install -m 0755 ${S}/follow.py ${D}${bindir}
    install -m 0755 ${S}/GeoFenceHelper.py ${D}${bindir}
    install -m 0755 ${S}/GeoFenceManager.py ${D}${bindir}
    install -m 0755 ${S}/GoProConstants.py ${D}${bindir}
    install -m 0755 ${S}/GoProManager.py ${D}${bindir}
    install -m 0755 ${S}/leashController.py ${D}${bindir}
    install -m 0755 ${S}/lookAtController.py ${D}${bindir}
    install -m 0755 ${S}/location_helpers.py ${D}${bindir}
    install -m 0755 ${S}/main.py ${D}${bindir}
    install -m 0755 ${S}/modes.py ${D}${bindir}
    install -m 0755 ${S}/multipoint.py ${D}${bindir}
    install -m 0755 ${S}/orbit.py ${D}${bindir}
    install -m 0755 ${S}/orbitController.py ${D}${bindir} 
    install -m 0755 ${S}/pano.py ${D}${bindir} 
    install -m 0755 ${S}/pathHandler.py ${D}${bindir}
    install -m 0755 ${S}/rcManager.py ${D}${bindir}
    install -m 0755 ${S}/returnHome.py ${D}${bindir}
    install -m 0755 ${S}/rewind.py ${D}${bindir}
    install -m 0755 ${S}/rewindManager.py ${D}${bindir}
    install -m 0755 ${S}/selfie.py ${D}${bindir}
    install -m 0755 ${S}/settings.py ${D}${bindir}
    install -m 0755 ${S}/shotFactory.py ${D}${bindir}
    install -m 0755 ${S}/shotLogger.py ${D}${bindir}
    install -m 0755 ${S}/shotManager.py ${D}${bindir}
    install -m 0755 ${S}/shotManager_version.py ${D}${bindir}
    install -m 0755 ${S}/shotManagerConstants.py ${D}${bindir}
    install -m 0755 ${S}/shots.py ${D}${bindir}
    install -m 0755 ${S}/transect.py ${D}${bindir}
    install -m 0755 ${S}/vector2.py ${D}${bindir}
    install -m 0755 ${S}/vector3.py ${D}${bindir}
    install -m 0755 ${S}/vectorPathHandler.py ${D}${bindir}
    install -m 0755 ${S}/yawPitchOffsetter.py ${D}${bindir}
    install -m 0755 ${S}/zipline.py ${D}${bindir}
    install -m 0755 ${S}/run_shotmanager.sh ${D}${bindir}
}
