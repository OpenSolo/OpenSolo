# install shots code to a vehicle and reboots python interpreter

function control_c {
    exit $?
}

function update_version {
	VERSION=$(git describe --tags)
	echo Installing ${VERSION} ...
	>"./shotManager_version.py"
	echo VERSION = \"${VERSION}\" >> "./shotManager_version.py"
}

trap control_c SIGINT
trap control_c SIGTERM

update_version

SCPARGS="-o StrictHostKeyChecking=no"

scp $SCPARGS *.py root@10.1.1.10:/usr/bin


echo Rebooting all Python
ssh $SCPARGS root@10.1.1.10 "killall python"