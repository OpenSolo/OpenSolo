#!/bin/bash

XMITFILE=/sys/kernel/debug/ieee80211/phy0/ath9k/xmit

LASTBYTES=0
while [ True ]; do

    #Scrape the number of transmitted bytes

    #Needs to handle output like this (colums run together):
    #TX-Pkts-All:           4508487          0    784093    369638
    #TX-Bytes-All:       1050712988          01076297731  40691534
    #HW-put-tx-buf:         1050315          0    318996    368833
    # NF is the number of fields (normally 5, 4 when they run together
    # $NF is the last field

    BYTES=`cat $XMITFILE | grep 'TX-Bytes-All' | awk '{ print $NF }'`

    #So we don't put out bogus data
    if [ $LASTBYTES -ne 0 ]; then

        #Calculate the delta
        DELTA=$((BYTES-LASTBYTES))

        logger -t wifi -p local2.info -- "${DELTA}"

    fi

    LASTBYTES=$BYTES

    #Log every second
    sleep 1

done
