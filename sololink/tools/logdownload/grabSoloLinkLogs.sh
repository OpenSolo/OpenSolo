#!/bin/sh

SCPARGS="-o StrictHostKeyChecking=no -i ../updater/updater_id_rsa"

DATE=`date "+%Y-%m-%d-%H:%M:%S"`

mkdir sololink-$DATE
mkdir artoolink-$DATE

ssh-keygen -R 10.1.1.1 &> /dev/null
ssh-keygen -R 10.1.1.10 &> /dev/null

scp $SCPARGS -r root@10.1.1.1:/log/* ./artoolink-$DATE/
scp $SCPARGS -r root@10.1.1.10:/log/* ./sololink-$DATE/
