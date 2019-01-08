#! /bin/sh
### BEGIN INIT INFO
# Provides:          Auto update from recovery
# Required-Start:
# Required-Stop:
# Default-Start:     4
# Default-Stop:
# Short-Description: Auto update from recovery to system after factory reset
### END INIT INFO

echo "Beginning golden_to_system.sh update script."

isGolden() {
    boot_dev=`grep 'boot' /proc/mounts | awk '{print $1}'`
    # boot_dev should be either:
    #   /dev/mmcblk0p1 when running golden, or
    #   /dev/mmcblk0p2 when running latest
    if [ ${boot_dev} == "/dev/mmcblk0p1" ]; then
        echo "Boot is on recovery partition"
        return 0
    elif [ ${boot_dev} == "/dev/mmcblk0p2" ]; then
        echo "Boot is on system partition"
        return 1
    else
        echo "Can't determine boot partition"
        return 1
    fi
}

makeFilename() {
    if [ -f "/mnt/boot/imx6solo-3dr-1080p.dtb" ]; then
        updateFilename="solo_1.1.0.tar.gz"
        return 0
    elif [ -f "/mnt/boot/imx6solo-3dr-artoo.dtb" ]; then
        updateFilename="controller_1.1.0.tar.gz"
        return 0
    else
        return 1
    fi
}

makeSystem() {
    # Makes the golden image boot partition into a system update
    sololink_config --update-prepare sololink
    cd /mnt/boot
    tar -czvf /log/updates/$updateFilename *
    cd /log/updates
    md5sum "$updateFilename" > "$updateFilename".md5
    ls -lh /log/updates/
    sed -i '1s/.*/golden/' /VERSION
    echo "Applying Update"
    sololink_config --update-apply sololink --reset
}

if ! isGolden; then
    # If we're not on the recovery partion, there is nothing to do, so exit.
    echo "Not on recovery partition. Nothing to do. Exiting."
    exit 0
fi

echo "Creating recovery_to_system.log in /log/ directory."
exec > /log/recovery_to_system.log
exec 2>&1

updateFilename=nothing
if ! makeFilename; then
    echo "Couldn't make update filename. Aborting update. See log."
    exit 1
fi
echo "updateFilename is $updateFilename"

if ! makeSystem; then
    echo "Making system update failed. Aborting. See log."
    exit 1
fi
