#!/bin/bash

SCPARGS="-o StrictHostKeyChecking=no -i ../updater/updater_id_rsa"
SSHCMD="ssh $SCPARGS root@10.1.1.1"
GOLDPARTDEV="/dev/mmcblk0p1"

#Sets the regulatory domain of the Artoo to the input argument.
#Note  the country code must be a 2-letter all-caps code

COUNTRY_LIST='AD,AE,AF,AI,AL,AM,AN,AR,AT,AU,AW,AZ,BA,BB,BD,BE,BF,BG,BH,BL,BN,BO,BR,BT,BY,BZ,CA,CF,CH,CI,CL,CN,CO,CR,CY,CZ,DE,DK,DM,DO,DZ,EC,EE,EG,ES,FI,FM,FR,GE,GB,GD,GH,GR,GL,GT,GU,GY,HN,HK,HR,HT,HU,ID,IE,IL,IN,IS,IR,IT,JM,JP,JO,KE,KH,KN,KP,KR,KW,KZ,LB,LC,LI,LK,LS,LT,LU,LV,MC,MA,MD,ME,MF,MO,MH,MK,MR,MT,MY,MX,NL,NO,NP,NZ,OM,PA,PE,PG,PH,PK,PL,PM,PT,PR,PW,QA,RO,RS,RU,RW,SA,SE,SG,SI,SK,SN,SV,SY,TC,TD,TG,TW,TH,TT,TN,TR,UA,US,UY,UZ,VC,VE,VN,VU,WF,YE,ZA,ZW'

usage() {
echo "
Usage ./setCountryCode.sh CODE

where CODE is a two-letter country code in the following list:
--------------------------------------------------------------
AD,AE,AF,AI,AL,AM,AN,AR,AT,AU,AW,AZ,BA,BB,BD,BE,BF,BG,BH,BL,BN,
BO,BR,BT,BY,BZ,CA,CF,CH,CI,CL,CN,CO,CR,CY,CZ,DE,DK,DM,DO,DZ,EC,
EE,EG,ES,FI,FM,FR,GE,GB,GD,GH,GR,GL,GT,GU,GY,HN,HK,HR,HT,HU,ID,
IE,IL,IN,IS,IR,IT,JM,JP,JO,KE,KH,KN,KP,KR,KW,KZ,LB,LC,LI,LK,LS,
LT,LU,LV,MC,MA,MD,ME,MF,MO,MH,MK,MR,MT,MY,MX,NL,NO,NP,NZ,OM,PA,
PE,PG,PH,PK,PL,PM,PT,PR,PW,QA,RO,RS,RU,RW,SA,SE,SG,SI,SK,SN,SV,
SY,TC,TD,TG,TW,TH,TT,TN,TR,UA,US,UY,UZ,VC,VE,VN,VU,WF,YE,ZA,ZW"
exit
}

if [ -z "$1" ]; then usage; fi 
if [[ ! $1 =~ ^[A-Z]{2}$ ]]; then usage; fi
if [[ "${COUNTRY_LIST}" =~ "$1" ]]; then
	echo "Setting to country $1"
else
	usage
fi
COUNTRY=$1

ssh-keygen -R 10.1.1.1 &> /dev/null

#See if we're booted from the GOLDEN partiton
#if so, remount it rw.  Otherwise mount the GOLDEN partition and set the .reg file.
BOOTPART=`ssh $SCPARGS root@10.1.1.1 grep 'boot' /proc/mounts | awk '{print $1}'`
if [ $BOOTPART == $GOLDPARTDEV ]; then

    echo "operating from GOLDEN partition."

    echo "remounting GOLDEN partition read-write"
    ssh $SCPARGS root@10.1.1.1 "mount $GOLDPARTDEV /mnt/boot -o remount,rw"

    echo "removing any existing reg file"
    ssh $SCPARGS root@10.1.1.1 "rm -f /mnt/boot/.reg"
    
    echo "creating reg file"
    ssh $SCPARGS root@10.1.1.1 "echo $COUNTRY >> /mnt/boot/.reg"

    echo "syncing"
    ssh $SCPARGS root@10.1.1.1 "sync"

    echo "remounting boot partition read-only"
    ssh $SCPARGS root@10.1.1.1 "mount $GOLDPARTDEV /mnt/boot -o remount,ro"
    
    echo "done"

else
    
    echo "operating from LATEST partition"

    ssh $SCPARGS root@10.1.1.1 "mkdir -p /tmp/bootmnt"
    
    echo "mounting GOLDEN partition read-write"
    ssh $SCPARGS root@10.1.1.1 "mount $GOLDPARTDEV /tmp/bootmnt"

    echo "removing any existing reg file"
    ssh $SCPARGS root@10.1.1.1 "rm -f /tmp/bootmnt/.reg"
    
    echo "creating reg file"
    ssh $SCPARGS root@10.1.1.1 "echo $COUNTRY >> /tmp/bootmnt/.reg"

    echo "syncing"
    ssh $SCPARGS root@10.1.1.1 "sync"

    echo "unmounting GOLDEN partition"
    ssh $SCPARGS root@10.1.1.1 "umount /tmp/bootmnt"

    ssh $SCPARGS root@10.1.1.1 "rm -rf /tmp/bootmnt"
    
    echo "done"

fi


