#!/bin/sh
clear

echo "Solo Test Script"
SSHARGS="-o StrictHostKeyChecking=no -o ConnectTimeout=3"
MAC=`ifconfig -a | grep HWaddr | awk '{print $5}' | tr '[:upper:]' '[:lower:]'`
DEBUGFSDIR=/sys/kernel/debug/ieee80211/phy0/

connectToTF() {
    SSID=$1
    rm -f /tmp/wpa*
    killall wpa_supplicant &> /dev/null
    echo "Connecting"
    cp /etc/wpa_supplicant.conf /tmp/
    wpa_passphrase $SSID sololink > /tmp/wpa_supplicant.conf
    wpa_supplicant -c/tmp/wpa_supplicant.conf -Dnl80211 -B -iwlan0 &> /dev/null
    ifconfig wlan0 10.1.1.10
    ping 10.1.1.1 -c1 -W5 &> /dev/null
    if [ $? -ne 0 ]; then
	    echo "Unable to connect"
        echo "********************FAIL************************"
	    disconnectFromTF
	    exit 1
    fi
}

disconnectFromTF() {
    echo "Disconnecting"
    ifconfig wlan0 down
    killall wpa_supplicant
}

if [ "$#" -ne 1 ]; then
    echo "Please specify the SoloLink_TEST network SSID"
    exit 1
fi

TFSSID=$1

echo "Initializing system"
init 2
sleep 2
ssh-keygen -R 10.1.1.1 &> /dev/null

echo "Attempting to connect to $TFSSID"
connectToTF $TFSSID
#ssh $SSHARGS root@10.1.1.1 "iw phy0 set txpower fixed 100"
#iw phy0 set txpower fixed 100

echo "Testing connection"
PASS=1
for ant in 1 2; do
    echo "Antenna ${ant}: "
    ifconfig wlan0 down
    iw phy0 set antenna 0x${ant} 0x${ant}
    ifconfig wlan0 10.1.1.10
    sleep 1
    rx=0
    tx=0
    rxWorst=0
    txWorst=0
    rxBest=-200
    txBest=-200
    for i in {1..20}; do
        rxSig=`cat ${DEBUGFSDIR}netdev:wlan0/stations/*/last_signal`
        txSig=`ssh $SSHARGS root@10.1.1.1 "cat ${DEBUGFSDIR}netdev:wlan0-ap/stations/${MAC}/last_signal"`
        if [ $? -ne 0 ]; then
            echo "Unable to connect to read signal value."
            echo "********************FAIL************************"
            PASS=0
            break
        fi

        echo -n "."
        #echo "$txSig $txWorst $txBest"
        #echo "$rxSig $rxWorst $rxBest"
        rx=$((rx+rxSig))
        tx=$((tx+txSig))
        if [ $rxSig -le $rxWorst ]; then
            rxWorst=$rxSig
        fi
        if [ $txSig -le $txWorst ]; then
            txWorst=$txSig
        fi
        if [ $rxSig -ge $rxBest ]; then
            rxBest=$rxSig
        fi
        if [ $txSig -ge $txBest ]; then
            txBest=$txSig
        fi
    done
    echo ""
    rx=$((rx/20))
    tx=$((tx/20))
    echo "Rx best: ${rxBest} avg: ${rx} worst: $rxWorst"
    echo "Tx best: ${txBest} avg: ${tx} worst: $txWorst"

    if [ $rx -le -42 ] && [ $rxBest -le -40 ]; then
        echo "********************FAIL************************"
        disconnectFromTF
        #echo "Done"
        #exit
        PASS=0
        break
    fi
    
    if [ $tx -le -42 ] && [ $rxBest -le -40 ]; then
        echo "********************FAIL************************"
        disconnectFromTF
        #echo "Done"
        #exit
        PASS=0
        break
    fi
done

if [ $PASS -eq 1 ]; then
    echo "********************PASS************************"
    disconnectFromTF
fi
#iw phy0 set txpower fixed 2700
#ssh $SSHARGS root@10.1.1.1 "iw phy0 set txpower fixed 2700"
echo "Done"

