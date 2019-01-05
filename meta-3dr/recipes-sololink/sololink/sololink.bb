SUMMARY = "SoloLink software for RC, telemetry and video"

LICENSE = "GPLv3"
LIC_FILES_CHKSUM = "file:///vagrant/LICENSE-APACHE;md5=3b83ef96387f14655fc854ddc3c6bd57"

SRCREV = "${AUTOREV}"
SRC_URI = "git:///vagrant/;protocol=file"

PV = "${SRCPV}"
S = "${WORKDIR}/git/sololink"

INHIBIT_PACKAGE_DEBUG_SPLIT = "1"

DEPENDS += "libnl"
DEPENDS += "gstreamer"

RDEPENDS_${PN} += "dronekit"
RDEPENDS_${PN} += "imx-vpu libfslvpuwrap gst-fsl-plugin"

# These need to match the environment variables in Sololink/config/sololink
# All should come from the machine configuration meta-3dr/conf/machine/*
soloconfdir = "${SOLOLINK_CONFIG_DIR}"

FILES_${PN} += "${bindir}/"
FILES_${PN} += "${libdir}/"
FILES_${PN} += "${sysconfdir}/"
FILES_${PN} += "/"

# This is for the builds in flightcode. Building with the --sysroot flag
# causes the preprocessor to find the correct include files if they are on
# the default include path (relative to sysroot/usr/include), but using
# -I to add additional include paths does not work; the full path with
# sysroot has to be used with -I.
do_compile_prepend () {
	export OECORE_TARGET_SYSROOT="${STAGING_DIR_TARGET}"
}

do_install () {
	install -d ${D}${bindir}
	install -d ${D}${libdir}
	install -d ${D}/

	install -d ${D}${sysconfdir}
	install -d ${D}${sysconfdir}/init.d
	install -d ${D}${sysconfdir}/rcS.d
	install -d ${D}${sysconfdir}/rc0.d
	install -d ${D}${sysconfdir}/rc3.d
	install -d ${D}${sysconfdir}/rc6.d

	install -m 0755 ${S}/flightcode/python/stm32_defs.py ${D}${bindir}
	install -m 0755 ${S}/flightcode/python/lsproc.py ${D}${bindir}

	install -m 0755 ${S}/px_uploader/uploader.py ${D}${bindir}
	install -m 0755 ${S}/px_uploader/loadPixhawk.py ${D}${bindir}
	install -m 0755 ${S}/flightcode/python/pixhawk.py ${D}${bindir}
	install -m 0644 ${S}/flightcode/python/gpio.py ${D}${bindir}
	install -m 0644 ${S}/flightcode/python/led_solo.py ${D}${bindir}/led.py
	install -m 0644 ${S}/flightcode/python/usb_solo.py ${D}${bindir}/usb.py
    install -m 0755 ${S}/flightcode/python/led_control.py ${D}${bindir}
    install -m 0755 ${S}/flightcode/python/SoloLED.py ${D}${bindir}
	install -m 0755 ${S}/init/pixhawk ${D}${sysconfdir}/init.d
	# link rcS.d/S60pixhawk -> ../init.d/pixhawk created in image recipe

	install -m 0755 ${S}/STM32Loader/updateArtoo.sh ${D}${bindir}
	install -m 0755 ${S}/STM32Loader/checkArtooAndUpdate.py ${D}${bindir}
	install -m 0755 ${S}/STM32Loader/reset_artoo ${D}${bindir}

	install -m 0755 ${S}/init/shutdownArtoo.sh ${D}${bindir}
	ln -sf ../../usr/bin/shutdownArtoo.sh ${D}${sysconfdir}/rc0.d/S89shutdownArtoo
    
    install -m 0755 ${S}/init/golden_to_system.sh ${D}${sysconfdir}/init.d
	ln -sf ../init.d/golden_to_system.sh ${D}${sysconfdir}/rc3.d/S100golden_to_system

	install -m 0755 ${S}/init/clock_sync ${D}${bindir}/clock_sync

	install -m 0755 ${S}/flightcode/video/app/app_streamer ${D}${bindir}
	install -m 0755 ${S}/flightcode/video/vid/vidlaunch ${D}${bindir}
	install -m 0755 ${S}/flightcode/video/hdmi/hdmiout ${D}${bindir}
	install -m 0755 ${S}/flightcode/video/cleanLibs.sh ${D}${bindir}
	ln -sf ../../usr/bin/cleanLibs.sh ${D}${sysconfdir}/rcS.d/S61cleanLibs

	install -m 0755 ${S}/net/etc/init.d/hostapd ${D}${sysconfdir}/init.d
	install -m 0755 ${S}/net/etc/init.d/netinit ${D}${sysconfdir}/init.d
	install -m 0755 ${S}/net/etc/init.d/networking ${D}${sysconfdir}/init.d
	ln -sf ../init.d/netinit ${D}${sysconfdir}/rcS.d/S41netinit
	ln -sf ../init.d/networking ${D}${sysconfdir}/rcS.d/S41networking

	install -m 0755 ${S}/net/usr/bin/clock.py ${D}${bindir}
	install -m 0755 ${S}/net/usr/bin/configfile.py ${D}${bindir}
	install -m 0755 ${S}/net/usr/bin/getmaclocal.py ${D}${bindir}
	install -m 0755 ${S}/net/usr/bin/hostapdconfig.py ${D}${bindir}
	install -m 0755 ${S}/net/usr/bin/ip.py ${D}${bindir}
	install -m 0755 ${S}/net/usr/bin/iw.py ${D}${bindir}
	install -m 0755 ${S}/net/usr/bin/wpa_supplicant.py ${D}${bindir}

	install -m 0755 ${S}/pair/pair.py ${D}${bindir}
	install -m 0755 ${S}/pair/pair_server.py ${D}${bindir}
	install -m 0755 ${S}/pair/pair_button.py ${D}${bindir}
	install -m 0755 ${S}/pair/pair_confirm.py ${D}${bindir}
	install -m 0755 ${S}/pair/pair_solo.py ${D}${bindir}
	install -m 0755 ${S}/pair/hostapd_ctrl.py ${D}${bindir}
	install -m 0755 ${S}/pair/ifconfig.py ${D}${bindir}
	install -m 0755 ${S}/pair/ip_util.py ${D}${bindir}
	install -m 0755 ${S}/pair/runlevel.py ${D}${bindir}
	install -m 0755 ${S}/pair/udhcpc.py ${D}${bindir}
	install -m 0755 ${S}/pair/wpa_cli.py ${D}${bindir}
	install -m 0755 ${S}/pair/wpa_control.py ${D}${bindir}

	install -m 0755 ${S}/net/usr/bin/rc_cli.py ${D}${bindir}
	install -m 0755 ${S}/net/usr/bin/rc_remap_sample.py ${D}${bindir}

	install -m 0755 ${S}/flightcode/telem_ctrl/telem_ctrl ${D}${bindir}

	install -m 0755 ${S}/flightcode/python/app_server.py ${D}${bindir}

	install -d ${D}${sysconfdir}/profile.d

	# This script sets environment variables (none are used yet)
	echo "export SOLOLINK_CONFIG_DIR=${SOLOLINK_CONFIG_DIR}" >> ${S}/config/sololink
	echo "alias ls='ls -aF'" >> ${S}/config/sololink
	echo "alias ll='ls -l'" >> ${S}/config/sololink
	echo "alias hi='history'" >> ${S}/config/sololink
	install -m 0644 ${S}/config/sololink ${D}${sysconfdir}/profile.d

	# Only the .orig file is installed; it is the "golden config" that
	# configinit uses to create sololink.conf (and md5) on first boot
	install -m 0644 ${S}/config/sololink.orig ${D}${soloconfdir}

	install -m 0755 ${S}/config/max_dgram_qlen ${D}${sysconfdir}/init.d
	ln -sf ../init.d/max_dgram_qlen ${D}${sysconfdir}/rcS.d/S10max_dgram_qlen

	install -m 0755 ${S}/config/configinit ${D}${sysconfdir}/init.d
	ln -sf ../init.d/configinit ${D}${sysconfdir}/rcS.d/S41configinit

	install -m 0755 ${S}/config/checknet ${D}${sysconfdir}/init.d
	ln -sf ../init.d/checknet ${D}${sysconfdir}/rc3.d/S01checknet

	install -m 0755 ${S}/init/startwd ${D}${sysconfdir}/init.d
	ln -sf ../init.d/startwd ${D}${sysconfdir}/rc6.d/S80startwd

	install -m 0755 ${S}/config/sololink_config ${D}${bindir}

	install -m 0755 ${S}/wifi/wifistats ${D}${bindir}
	install -m 0755 ${S}/wifi/survey_dump ${D}${bindir}
	install -m 0755 ${S}/wifi/survey_log ${D}${bindir}
	install -m 0755 ${S}/wifi/logRCUp.sh ${D}${bindir}

	install -m 0755 ${S}/flightcode/telem/telem_forwarder ${D}${bindir}
	install -m 0755 ${S}/flightcode/rssi/rssi_send ${D}${bindir}
	install -m 0755 ${S}/flightcode/pixrc/pixrc ${D}${bindir}
	install -m 0755 ${S}/flightcode/stm32/stm32 ${D}${bindir}
	install -m 0755 ${S}/flightcode/tlog/tlog ${D}${bindir}
	install -m 0755 ${S}/flightcode/proc_top/proc_top ${D}${bindir}
	install -m 0755 ${S}/flightcode/thermal/log_temp ${D}${bindir}

	# busybox's syslogd configuration
	# Note: By default, syslogd is started in runlevel 2. We need it in as a
	# startup item since we'd like to log from some of our other startup items.
	# The old links are deleted in the image recipe (this is not the correct way
	# to change when it starts).
	ln -sf ../init.d/syslog ${D}${sysconfdir}/rcS.d/S40syslog
	# One of these will be renamed at image build time to syslog.conf.busybox,
	# and the other will be deleted.
	install -m 0644 ${S}/config/syslog.conf.busybox.solo ${D}${sysconfdir}
	install -m 0644 ${S}/config/syslog.conf.busybox.controller ${D}${sysconfdir}

	# rotate 3dr logs each boot
	install -m 0755 ${S}/init/3dr_rotate ${D}${sysconfdir}/init.d
	ln -sf ../init.d/3dr_rotate ${D}${sysconfdir}/rcS.d/S433dr_rotate

	# One of these will be renamed at image build time to logrotate-sololink.conf,
	# and the other will be deleted.
	install -m 0644 ${S}/config/logrotate-sololink.conf.solo ${D}${sysconfdir}
	install -m 0644 ${S}/config/logrotate-sololink.conf.controller ${D}${sysconfdir}

	# Inject updater screen messages
	install -m 0755 ${S}/flightcode/stm32/updater_msg.py ${D}${bindir}

	# Inject lockout screen messages
	install -m 0755 ${S}/flightcode/stm32/lockout_msg.py ${D}${bindir}

	# Inject app connected messages
	install -m 0755 ${S}/flightcode/stm32/app_connected_msg.py ${D}${bindir}

	# Input report message test/demo
	install -m 0755 ${S}/flightcode/stm32/input_report_client.py ${D}${bindir}
	install -m 0755 ${S}/flightcode/stm32/input_report_msg.py ${D}${bindir}

	# Button event message test/demo
	install -m 0755 ${S}/flightcode/stm32/btn_client.py ${D}${bindir}

	# Stick axes configuration
	install -m 0644 ${S}/flightcode/stm32/config_stick_axes_msg.py ${D}${bindir}
	install -m 0755 ${S}/flightcode/stm32/config_stick_axes.py ${D}${bindir}

	# Camera tilt sweep dial configuration
	install -m 0644 ${S}/flightcode/stm32/config_sweep_time_msg.py ${D}${bindir}
	install -m 0755 ${S}/flightcode/stm32/config_sweep_time.py ${D}${bindir}

	# Param stored values message
	install -m 0755 ${S}/flightcode/stm32/param_stored_vals_msg.py ${D}${bindir}

	# Telemetry units configuration
	install -m 0644 ${S}/flightcode/stm32/set_telem_units_msg.py ${D}${bindir}
	install -m 0755 ${S}/flightcode/stm32/set_telem_units.py ${D}${bindir}

	# Watchdog support
	install -m 0755 ${S}/flightcode/wdog/wdog ${D}${bindir}

	# Stick calibration for artoo
	install -m 0755 ${S}/flightcode/python/stick-cal.py ${D}${bindir}
	install -m 0755 ${S}/flightcode/python/slip.py ${D}${bindir}
	install -m 0755 ${S}/flightcode/python/runStickCal.sh ${D}${bindir}

	#dataflash log downloading
	install -m 0755 ${S}/flightcode/dflog/dflog ${D}${bindir}
	install -m 0755 ${S}/flightcode/dflog/loadLog.py ${D}${bindir}

	#mavlink-downloaded-dataflash log transfers to artoo
	install -m 0755 ${S}/flightcode/dflog/dataFlashMAVLink-to-artoo.py ${D}${bindir}

	# the logger module is responsible for initiating and handling
	#          dataflash transfers from the pixhawk:
	#echo "module load logger" >> ${D}/.mavinit.scr

	# the logger binary is responsible for initiating and handling
	#          dataflash transfers from the pixhawk:
	install -m 0755 ${S}/flightcode/dataflash_logger/dataflash_logger ${D}${bindir}

	#Solo wifi production test
	install -m 0755 ${S}/tools/wifiTest/SoloTest.sh ${D}${bindir}

	#RC unlock
	install -m 0755 ${S}/flightcode/unlock/unlock ${D}${bindir}
	install -m 0755 ${S}/flightcode/python/rc_lock.py ${D}${bindir}

	#Gimbal
	install -d ${D}${bindir}/gimbal
	install -m 0644 gimbal/firmware_helper.py         ${D}${bindir}/gimbal
	install -m 0644 gimbal/firmware_loader.py         ${D}${bindir}/gimbal
	install -m 0644 gimbal/setup_comutation.py        ${D}${bindir}/gimbal
	install -m 0644 gimbal/setup_mavlink.py           ${D}${bindir}/gimbal
	install -m 0644 gimbal/setup_param.py             ${D}${bindir}/gimbal
	install -m 0644 gimbal/setup_factory_pub.py       ${D}${bindir}/gimbal
	install -m 0644 gimbal/setup_validate.py          ${D}${bindir}/gimbal
	install -m 0755 gimbal/setup.py                   ${D}${bindir}/gimbal
	# put this in gimbal subdir so as not to conflict with existing one
	ln -sf /usr/bin/gimbal/setup.py                   ${D}${bindir}/gimbal_setup
	install -m 0755 gimbal/loadGimbal.py              ${D}${bindir}
	install -m 0755 ${S}/init/updateGimbal.sh         ${D}${sysconfdir}/init.d
	# link rcS.d/S62updateGimbal.sh -> ../init.d/updateGimbal.sh created in image recipe
}
