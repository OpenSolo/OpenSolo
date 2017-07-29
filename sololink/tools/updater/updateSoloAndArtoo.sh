#!/bin/bash

CLEAR=clear

SOLO_IP=10.1.1.10
ARTOO_IP=10.1.1.1

SCPARGS="-o StrictHostKeyChecking=no -i ./updater_id_rsa"

SERVERADDR="REDACTED"

system=`uname -a | awk '{print $1}'`

downloadTarAndMD5() {
    FILEPATH=$1
    FILES=`curl -u sololink:redacted -s "${SERVERADDR}${FILEPATH}update/" | grep href | sed 's/.*href="//' | sed 's/".*//' | grep 'tar.gz$' | sed 's/\b\([0-9]\)\b/0\1/g'  | sort | sed 's/\b0\([0-9]\)/\1/g'`

    for f in $FILES; do
        latestFile=$f
    done

    if [ -e $latestFile ] && [ -e ${latestFile}.md5 ]; then
        echo "Latest file is already downloaded."
        return
    fi

    echo "Downloading file" $latestFile "and its MD5 sum"
    curl --progress-bar -u sololink:redacted -O "${SERVERADDR}${FILEPATH}update/$latestFile"
    curl --progress-bar -u sololink:redacted -s -O "${SERVERADDR}${FILEPATH}update/${latestFile}.md5"
}

pingWait() {
    address=$1

    if [[ $system =~ ^MINGW32.* ]]; then
        while ! ping -n 1 $address &> /dev/null; do sleep 1; echo -n "."; done
        return
    else
        while ! ping -c1 -W1 $address &> /dev/null; do sleep 1; echo -n "."; done
        return
    fi
}

copyUpdate() {
    address=$1
    tarball=$2
    md5file=$3

    #Wait for the target to come up
    echo -n "Waiting to connect to $address"
    pingWait $address
    echo "Connected to $address"

    #Copy the update files to the target
    echo "Sending update file to $address"
    ssh-keygen -R $address &> /dev/null
    ssh $SCPARGS root@$address "sololink_config --update-prepare sololink" &> /dev/null
    # older versions don't have sololink-config and ssh returns 127
    if [ $? -ne 0 ]; then
        ssh $SCPARGS root@$address "rm -rf /log/updates" &> /dev/null
        ssh $SCPARGS root@$address "mkdir -p /log/updates" &> /dev/null
    fi
    scp $SCPARGS ${tarball} root@$address:/log/updates/
    scp $SCPARGS ${md5file} root@$address:/log/updates/
}

startUpdate() {
    address=$1
    reset=$2

    #Wait for the target to come up
    echo -n "Waiting to connect to $address"
    pingWait $address
    echo "Connected to $address"

    echo "Starting update on $address"
    ssh-keygen -R $address &> /dev/null
    if [ $reset == 1 ]; then
      ssh $SCPARGS root@$address "sololink_config --update-apply sololink --reset" &> /dev/null
    else
      ssh $SCPARGS root@$address "sololink_config --update-apply sololink" &> /dev/null
    fi
    if [ $? -ne 0 ]; then
        ssh $SCPARGS root@$address "touch /log/updates/UPDATE" &> /dev/null
        ssh $SCPARGS root@$address "shutdown -r now"
    fi
}

checkMD5() {
    thisfile=$1

    # require corresponding md5 file
    if [ ! -e ${thisfile}.md5 ]; then
        echo "No ${thisfile}.md5, please place one in this directory."
        exit
    fi
    # check md5 before upload
    if [[ $system == 'Darwin' ]] || [[ $system =~ ^MINGW32.* ]]; then
        md5sum --check ${thisfile}.md5 > /dev/null 2>&1
    else
        md5sum --check --quiet ${thisfile}.md5 > /dev/null 2>&1
    fi
    # $?==0 on success, !=0 on failure
    if [ $? -ne 0 ]; then
        echo "ERROR checking md5 for ${thisfile}.md5"
        cat ${thisfile}.md5
        exit
    fi
}

$CLEAR

if [ $system == "Darwin" ]; then
    if [ ! -e /usr/local/bin/md5sum ] && [ ! -e /opt/local/bin/md5sum ]; then
        echo "Please install md5sha1sum using macports or brew"
        exit
    fi
fi

menu() {
    echo "SoloLink Update, Reset and Configuration"
    echo ""
    echo "Commands:"
    echo ""
    echo "  i.MX6/System updates"
    echo "    update         <solo|artoo|both>     <download> <reset>"
    echo "    reset          <solo|artoo|both>     <factory|settings>"
    echo "    makegold       <solo|artoo|both>"
    echo ""
    echo "  Firmware updates"
    echo "    pixupdate"
    echo "    stm32update"
    echo ""
    echo "  Configuration options"
    echo "    setSSID        <SSID_NAME>"
    echo ""
    echo "Type any command followed by \"help\" for more information"
    while true; do
        read -p "Please enter a command (q to exit):" cmd
        args=`echo $cmd | awk '{$1=""; print $0}'`
        case $cmd in
            update* ) runUpdate $args; exit;;
            reset* ) runReset $args; exit;;
            makegold* ) runMakeGold $args; exit;;
            pixupdate* ) runUpdatePixhawk $args; exit;;
            stm32update* ) runUpdateSTM32 $args; exit;;
            setSSID* ) runSetSSID $args; exit;;
            q|quit|exit ) exit;;
            * ) echo "Please enter a valid command."; sleep 1; menu;;
        esac
    done
}

runUpdate() {
    if [ -z $1 ]; then
        echo "Invalid arguments.  Usage:"
        echo "    update <solo|artoo|both> <download> <reset>"
        menu
    fi

    artooonly=0
    soloonly=0
    if [ $1 == "solo" ]; then
        soloonly=1
    elif [ $1 == "artoo" ]; then
        artooonly=1
    elif [ $1 == "both" ]; then
        artooonly=0
        soloonly=0
    elif [ $1 == "help" ]; then
        echo "Performs an update of the Solo, Artoo, or both.  Software will not be"
        echo "automatically downloaded unless the download argument is specified."
        echo "The reset argument will perform a settings reset with the update, putting"
        echo "the Solo and Artoo in a default state after the update finishes"
        echo "The total software update will take between 2 and 5 minutes, depending"
        echo "on the internet connection and the number of components on the Solo/Artoo"
        echo "that require updating."
        echo ""
        menu
    else
        echo "Invalid arguments.  Usage:"
        echo "    update <solo|artoo|both> <download> <reset>"
        menu
    fi

    noDL=1
    reset=0
    if [ "_$2" == "_download" ]; then
        noDL=0
        if [ "_$3" == "_reset" ]; then
          reset=1
        fi
    fi

    if [ "_$2" == "_reset" ]; then
      reset=1
    fi

    $CLEAR

    if [ $noDL == 0 ]; then
        echo -n "Waiting for internet connectivity"
        pingWait "google.com"
        $CLEAR
    fi

    if [ $artooonly == 0 ]; then
        if [ $noDL == 0 ]; then
            # Check and/or download the latest update file
            echo "Checking for latest Solo software"
            downloadTarAndMD5 "/solo/1080p/"
        fi

        solofile=""
        # find the last file that matches *solo*.tar.gz
        for f in `ls *solo*.tar.gz`; do
            solofile=$f
        done

        checkMD5 $solofile
    fi

    if [ $soloonly == 0 ]; then
        if [ $noDL == 0 ]; then
            # Check and/or download the latest update file
            echo "Checking for latest Artoo software"
            downloadTarAndMD5 "/artoo/digital/"
        fi

        artoo=""
        # find the last file that matches *controller*.tar.gz
        for f in `ls *controller*.tar.gz`; do
            artoofile=$f
        done

        checkMD5 $artoofile
    fi

    $CLEAR

    if [ $soloonly == 1 ]; then
        echo "Please power-up Solo and connect to the SoloLink network"
    elif [ $artooonly == 1 ]; then
        echo "Please power-up Artoo and connect to the SoloLink network"
    else
        echo "Please power-up Solo and Artoo and connect to the SoloLink network"
    fi

    if [ $artooonly == 0 ]; then
        copyUpdate $SOLO_IP $solofile "${solofile}.md5"
    fi

    if [ $soloonly == 0 ]; then
        copyUpdate $ARTOO_IP $artoofile "${artoofile}.md5"
    fi

    if [ $artooonly == 0 ]; then
        startUpdate $SOLO_IP $reset
    fi

    if [ $soloonly == 0 ]; then
        startUpdate $ARTOO_IP $reset
    fi

    echo "Please wait at least three minutes for the update to complete."
}

runReset() {

    if [ -z $1 ]; then
        echo "Invalid arguments.  Usage:"
        echo "    reset <solo|artoo|both> <factory|settings>"
        menu
    fi

    artooonly=0
    soloonly=0
    if [ $1 == "solo" ]; then
        soloonly=1
        ADDRESSES="$SOLO_IP"
    elif [ $1 == "artoo" ]; then
        artooonly=1
        ADDRESSES="$ARTOO_IP"
    elif [ $1 == "both" ]; then
        artooonly=0
        soloonly=0
        ADDRESSES="$SOLO_IP $ARTOO_IP"
    elif [ $1 == "help" ]; then
        echo "Performs either a factory reset or a settings reset of the"
        echo "Solo, Artoo or both."
        echo ""
        echo "A factory reset resets to the \"Golden\" image stored in the"
        echo "SD card of the i.MX6.  This reverts all user settings and"
        echo "reverts the kernel, devicetree and rootfs to their original"
        echo "factory defaults.  Any prior updates are overridden, and the"
        echo "logging partition is erased."
        echo ""
        echo "A settings reset removes any user settings and erases the "
        echo "logging partition.  The latest update is preserved, but the"
        echo "system reverts to a default state and will need to be"
        echo "re-paired and re-configured by the user."
        echo ""
        menu
    else
        echo "Invalid arguments.  Usage:"
        echo "    reset <solo|artoo|both> <factory|settings>"
        menu
    fi

    if [ -z $2 ]; then
        echo "Invalid arguments.  Usage:"
        echo "    reset <solo|artoo|both> <factory|settings>"
        menu
    fi

    $CLEAR

    if [ $2 == "factory" ]; then
        mode="factory"
    elif [ $2 == "settings" ]; then
        mode="settings"
    else
        echo "Invalid arguments.  Usage:"
        echo "    reset <solo|artoo|both> <factory|settings>"
        menu
    fi

    echo -n "Performing a $mode reset on"
    if [ $artooonly == 1 ]; then
        echo " Artoo"
    elif [ $soloonly == 1 ]; then
        echo " Solo"
    else
        echo " both Solo and Artoo"
    fi

    while true; do
        read -p "Are you sure you would like to proceed(y/n)?" yn
        case $yn in
            [Yy]* ) break;;
            [Nn]* ) $CLEAR; menu;;
            * ) echo "Please answer yes or no.";;
        esac
    done

    if [ $soloonly == 1 ]; then
        echo "Please power-up Solo and Artoo and connect to the SoloLink network"
    elif [ $artooonly == 1 ]; then
        echo "Please power-up Artoo and connect to the SoloLink network"
    else
        echo "Please power-up Solo and Artoo and connect to the SoloLink network"
    fi

    for address in $ADDRESSES; do
        #Wait for the target to come up
        echo -n "Waiting to connect to $address"
        pingWait $address
        echo "Connected to $address"

        echo "Starting $mode reset on $address"
        ssh-keygen -R $address &> /dev/null
        if [ $mode == "factory" ]; then
            ssh $SCPARGS root@$address "sololink_config --factory-reset" &> /dev/null
            if [ $? -ne 0 ]; then
                ssh $SCPARGS root@$address "mkdir -p /log/updates" &> /dev/null
                ssh $SCPARGS root@$address "touch /log/updates/FACTORYRESET" &> /dev/null
                ssh $SCPARGS root@$address "shutdown -r now"
            fi
        else
            ssh $SCPARGS root@$address "sololink_config --settings-reset" &> /dev/null
            if [ $? -ne 0 ]; then
                ssh $SCPARGS root@$address "mkdir -p /log/updates" &> /dev/null
                ssh $SCPARGS root@$address "touch /log/updates/RESETSETTINGS" &> /dev/null
                ssh $SCPARGS root@$address "shutdown -r now"
            fi
        fi

    done

    echo "Please wait at least 2 minutes for the $mode reset to complete"
}

runMakeGold() {
    if [ -z $1 ]; then
        echo "Invalid arguments.  Usage:"
        echo "    makegold <solo|artoo|both>"
        menu
    fi

    artooonly=0
    soloonly=0
    if [ $1 == "solo" ]; then
        soloonly=1
        ADDRESSES="$SOLO_IP"
    elif [ $1 == "artoo" ]; then
        artooonly=1
        ADDRESSES="$ARTOO_IP"
    elif [ $1 == "both" ]; then
        artooonly=0
        soloonly=0
        ADDRESSES="$SOLO_IP $ARTOO_IP"
    elif [ $1 == "help" ]; then
        echo "Makes the current updated image on the i.MX6 the \"Golden\" image"
        echo "on the SD card.  This way, when a future factory reset is performed"
        echo "the system reverts to the image that is currently running instead"
        echo "of the older \"Golden\" image.  The original \"Golden\" image is"
        echo "overwritten.  This is useful for development boards, as it is"
        echo "likely that the older \"Golden\" image will become obsolete."
        echo ""
        menu
    else
        echo "Invalid arguments.  Usage:"
        echo "    makegold <solo|artoo|both>"
        menu
    fi

    $CLEAR

    echo -n "Overwriting the \"Golden\" partition on"
    if [ $artooonly == 1 ]; then
        echo " Artoo"
    elif [ $soloonly == 1 ]; then
        echo " Solo"
    else
        echo " both Solo and Artoo"
    fi

    while true; do
        read -p "Are you sure you would like to proceed(y/n)?" yn
        case $yn in
            [Yy]* ) break;;
            [Nn]* ) $CLEAR; menu;;
            * ) echo "Please answer yes or no.";;
        esac
    done

    if [ $soloonly == 1 ]; then
        echo "Please power-up Solo and Artoo and connect to the SoloLink network"
    elif [ $artooonly == 1 ]; then
        echo "Please power-up Artoo and connect to the SoloLink network"
    else
        echo "Please power-up Solo and Artoo and connect to the SoloLink network"
    fi

    for address in $ADDRESSES; do
        #Wait for the target to come up
        echo -n "Waiting to connect to $address"
        pingWait $address
        echo "Connected to $address"

        echo "Starting make golden on $address"
        ssh-keygen -R $address &> /dev/null
        ssh $SCPARGS root@$address "sololink_config --make-golden" &> /dev/null
        if [ $? -ne 0 ]; then
            scp $SCPARGS ./makeGolden.sh root@$address: &> /dev/null
            ssh $SCPARGS root@$address "chmod +x ./makeGolden.sh"
            ssh $SCPARGS root@$address "./makeGolden.sh"
        fi
    done
}

runUpdatePixhawk() {
    if [ $1 == "help" ]; then
        echo "Updates the Pixhawk on Solo with the Arducopter-X.X.X.px4 file"
        echo "stored in this folder.  The ArduCopter-X.X.X.px4 file must have"
        echo "been previously downloaded and placed here."
        echo ""
        menu
    fi

    $CLEAR

    echo "Checking for pixhawk update file."
    # find the last file that matches ArduCopter*.px4
    if [ ! -e ArduCopter-*.*.*.px4 ]; then
        echo "Error, no ArduCopter-*.*.*.px4 found.  Please download and retry"
        exit
    fi

    for f in `ls ArduCopter-*.*.*.px4`; do
        pixfile=$f
    done

    echo "Updating the pixhawk with $pixfile"

    while true; do
        read -p "Are you sure you would like to proceed(y/n)?" yn
        case $yn in
            [Yy]* ) break;;
            [Nn]* ) $CLEAR; menu;;
            * ) echo "Please answer yes or no.";;
        esac
    done

    echo "Please power-up Solo and Artoo and connect to the SoloLink network"

    address="10.1.1.10"
    #Wait for the target to come up
    echo -n "Waiting to connect to $address"
    pingWait $address
    echo "Connected to $address"

    echo "Starting pixhawk update on $address"
    ssh-keygen -R $address &> /dev/null

    ssh $SCPARGS root@$address "sololink_config --update-prepare pixhawk" &> /dev/null
    # okay if that returns an error

    scp $SCPARGS $pixfile root@$address:/firmware/ &> /dev/null

    ssh $SCPARGS root@$address "sololink_config --update-apply pixhawk" &> /dev/null
    if [ $? -ne 0 ]; then
        ssh $SCPARGS root@$address "shutdown -r now"
    fi
}

runUpdateSTM32() {
    if [ $1 == "help" ]; then
        echo "Updates the STM32 on the Artoo with the artoo_x.x.x.bin file"
        echo "stored in this folder.  The artoo_x.x.x.bin file must have"
        echo "been previously downloaded and placed here."
        echo ""
        menu
    fi

    $CLEAR

    echo "Checking for artoo update file."
    # find the last file that matches artoo
    if [ ! -e artoo_*.bin ]; then
        echo "Error, no artoo_x.x.x.bin found.  Please download and retry"
        exit
    fi

    for f in `ls artoo_*.bin`; do
        artoofile=$f
    done

    echo "Updating the Artoo with $artoofile"

    while true; do
        read -p "Are you sure you would like to proceed(y/n)?" yn
        case $yn in
            [Yy]* ) break;;
            [Nn]* ) $CLEAR; menu;;
            * ) echo "Please answer yes or no.";;
        esac
    done

    echo "Please power-up Artoo and connect to the SoloLink network"

    address="10.1.1.1"
    #Wait for the target to come up
    echo -n "Waiting to connect to $address"
    pingWait $address
    echo "Connected to $address"

    echo "Starting artoo update on $address"
    ssh-keygen -R $address &> /dev/null

    ssh $SCPARGS root@$address "sololink_config --update-prepare artoo" &> /dev/null
    # okay if that returns an error

    scp $SCPARGS $artoofile root@$address:/firmware/${artoofile} &> /dev/null

    ssh $SCPARGS root@$address "sololink_config --update-apply artoo" &> /dev/null
    if [ $? -ne 0 ]; then
        ssh $SCPARGS root@$address "init 2"
        ssh $SCPARGS root@$address "checkArtooAndUpdate.py"
        ssh $SCPARGS root@$address "init 3"
    fi
}

runSetSSID() {
    if [ -z $1 ]; then
        echo "Invalid arguments.  Usage:"
        echo "    setSSID <NAME>"
        menu
    fi

    if [ $1 == "help" ]; then
        echo "Sets the SSID of the currently connected Artoo.  After setting"
        echo "the SSID, the ArtooLink reboots.  You will be required to re-pair"
        echo "your Solo to the new SSID and re-connect your computer if necessary"
        echo ""
        menu
    fi

    echo "I will be renaming the Artoo SSID to SoloLink_${1}."
    while true; do
        read -p "Are you sure you would like to proceed (y/n)?" yn
        case $yn in
            [Yy]* ) break;;
            [Nn]* ) menu; break;;
            * ) echo "Please answer yes or no.";;
        esac
    done

    $CLEAR

    echo "Please power-up Solo and Artoo and connect to the SoloLink network"
    address="10.1.1.1"
    #Wait for the target to come up
    echo -n "Waiting to connect to $address"
    pingWait $address
    echo "Connected to $address"

    ssh-keygen -R $address &> /dev/null

    ssh $SCPARGS root@$address "sololink_config --set-wifi-ssid SoloLink_${1}" &> /dev/null
    if [ $? -ne 0 ]; then
        ssh $SCPARGS root@$address "sed -i \"s/^ssid=SoloLink_.*/ssid=SoloLink_${1}/\" /etc/hostapd.conf"
        ssh $SCPARGS root@$address "md5sum /etc/hostapd.conf > /etc/hostapd.conf.md5"
    fi

    while true; do
        read -p "Would you like to set the SSID on Solo as well (y/n)? Otherwise you will have to re-pair your Solo." yn
        case $yn in
            [Yy]* ) break;;
            [Nn]* )
                ssh $SCPARGS root@$address "shutdown -r now";
                echo "The Artoolink (and SoloLink) will now reboot.  Please re-pair your Solo after it";
                echo "has finished rebooting, which will take about 30s.";
                exit;;
            * ) echo "Please answer yes or no.";;
        esac
    done

    address="10.1.1.10"
    echo "Setting SSID on Solo."
    echo -n "Waiting to connect to $address"
    pingWait $address
    echo "Connected to $address"

    ssh-keygen -R $address &> /dev/null

    ssh $SCPARGS root@$address "sololink_config --set-wifi-ssid SoloLink_${1}" &> /dev/null
    if [ $? -ne 0 ]; then
        ssh $SCPARGS root@$address "sed -i \"s/ssid=\\\"SoloLink_.*/ssid=\\\"SoloLink_${1}\\\"/\" /etc/wpa_supplicant.conf"
        ssh $SCPARGS root@$address "md5sum /etc/wpa_supplicant.conf > /etc/wpa_supplicant.conf.md5"
    fi

    ssh $SCPARGS root@$address "shutdown -r now"
    ssh $SCPARGS root@10.1.1.1 "shutdown -r now"

    echo "The Artoolink & SoloLink will now reboot.  Please wait at least 30s for them to re-connect"

}

$CLEAR
menu
