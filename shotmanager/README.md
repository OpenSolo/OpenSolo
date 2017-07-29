WARNING - WORK IN PROGRESS

```
This code is known to be broken and/or incomplete. IT DOES NOT WORK. 

We are actively working on fixing it, and we really, really do not recommend you download it just yet.

We will remove this warning from the repository when it is no longer required.
```


# ShotManager

<img align="left" src="https://cloud.githubusercontent.com/assets/5368500/12708704/85440436-c8f6-11e5-9bfe-45327c174b28.png"> ShotManager is a Python application that governs smart shots, GoPro control, and some Solo Controller (Artoo) functionality.

## Overview

ShotManager is a Python application that runs on the i.MX6 Companion Computer (sometimes referred to as "SoloLink") and manages smart shots, GoPro control, and some Solo Controller (Artoo) functionality.

The diagram below shows the main ShotManager communications. 

<img width="700px" src="https://www.lucidchart.com/publicSegments/view/4257006a-9401-4daf-a77c-afb8e7f316d9/image.png" />

The diagram is fairly straightforward. Shots are implemented using DroneKit-Python scripts and communicated to the autopilot using MAVLink messages. The App<->ShotManager communication travels over TCP on port 5507; the message format and messages are documented in [App-ShotManager Communication](/docs/App-ShotManager%20communication.md).


## Dependencies (upstream and downstream)

The main dependencies of this project are:

* [dronekit-python](https://github.com/dronekit/dronekit-python) - ShotManager uses *DroneKit Python* to implement the movement behavior required by shots. ([Docs here](http://python.dronekit.io/)).
* [dronekit-python-solo](https://github.com/dronekit/dronekit-python-solo) - An extension for dronekit-python that enables Solo-specific functionality. 
* [sololink-python](https://github.com/3drobotics/sololink-python) - ShotManager uses this to acquire information about Artoo buttons (A,B,Pause,Fly) and to get and remap RC stick values. This is the Python interface for [SoloLink](https://github.com/3drobotics/SoloLink). 
* [mavlink-solo](https://github.com/3drobotics/mavlink-solo) - ShotManager uses this C-library to package (and read) MAVLink messages in communications with the Pixhawk and GoPro.
* [numpy](https://github.com/numpy/numpy) - A popular mathematics library for Python.

The project is a dependency of:

* [SoloLink]() - This contains all the *3DR-created* software in the Yocto image running on the Companion Computer (i.MX6).
* [meta-3dr]() - This contains the central definition of how the whole i.MX6 Yocto image is constructed. It contains [Bitbake](https://www.yoctoproject.org/tools-resources/projects/bitbake) recipes for the different included software, including ShotManager, SoloLink etc. 


## Developer Setup

### Creating feature branches

The shotmanager software plays several roles in the Solo software environment. Due to this, it is one of the most actively developed-upon repositories at 3DRobotics. In order to maintain repository cleanliness, branches should be only kept on origin if they have a purpose. Branches should also be named by their creators e.g. (john/some-feature-branch). There are periodic manual audits of any un-claimed branches to keep the branch count low.

### Setting up a simulation environment (OS X ONLY)

These instructions explain how to setup the ardupilot SITL under a virtual machine and setup the shotmanager environment on OS X. 

#### Ardupilot Solo simulated in Ubuntu 14.04

1] Download & install [VirtualBox](https://www.virtualbox.org/wiki/Downloads).

2] Download & install [Ubuntu 14.04](http://www.ubuntu.com/download/desktop) in VirtualBox.

3] Install VirtualBox tools.

3] Install required packages.
```
sudo apt-get update
sudo apt-get install python-matplotlib python-serial python-wxgtk2.8 python-lxml
sudo apt-get install python-scipy python-opencv ccache gawk git python-pip python-pexpect
sudo pip install pymavlink MAVProxy==1.4.38
```

4] Clone [ardupilot-solo](https://github.com/3drobotics/ardupilot-solo) to your home directory.
```
git clone https://github.com/3drobotics/ardupilot-solo.git
```

5] Navigate to the ArduCopter directory.
```
cd ~/ardupilot-solo/ArduCopter
```

6] Clear unwanted APM parameter set.
```
../Tools/autotest/sim_vehicle.sh -w
```
**NOTICE**: Wait until you see *GPS Lock* before exiting this process and continuing.

**NOTICE**: Repeat steps 7-9 everytime you want to start up ardupilot-solo.

7] Get your OS X IPv4 address.
In OS X terminal.app:
```
ifconfig | grep inet
```
Sample output:
```
silva$ ifconfig | grep inet
	inet6 ::1 prefixlen 128 
	inet 127.0.0.1 netmask 0xff000000 
	inet6 fe80::1%lo0 prefixlen 64 scopeid 0x1 
	inet6 fe80::a299:9bff:fe05:a25d%en0 prefixlen 64 scopeid 0x4 
	inet 10.1.48.164 netmask 0xfffffc00 broadcast 10.1.51.255
	inet6 fe80::f0c4:ffff:fe2f:a1f%awdl0 prefixlen 64 scopeid 0x9 
	inet6 fe80::9082:2385:dea6:4452%utun0 prefixlen 64 scopeid 0xa 
	inet6 fdd5:617c:442a:d75a:9082:2385:dea6:4452 prefixlen 64 
	inet 10.211.55.2 netmask 0xffffff00 broadcast 10.211.55.255
	inet 10.37.129.2 netmask 0xffffff00 broadcast 10.37.129.255
```
In this case, our IPv4 address is 10.1.48.164.

8] Navigate to the ArduCopter directory.
```
cd ~/ardupilot-solo/ArduCopter
```

9] Run ardupilot-solo within a simulated environment.

**NOTICE**: If your mobile device is the iOS simulator, then MOBILE_DEVICE_IP is the same as OS_X_IPv4.
```
../Tools/autotest/sim_vehicle.sh --console --map --out OS_X_IPv4_HERE:14560 --out MOBILE_DEVICE_IP_HERE:14550
```

#### Shotmanager simulated in OS X

1] Create a virtualenv for Python to install shotmanager dependencies.
```
sudo pip install virtualenv
virtualenv shotman_venv
source shotman_venv/bin/activate
```

2] Install shotmanager dependencies.
```
pip install dronekit dronekit-solo numpy nose mock
git clone https://github.com/3drobotics/sololink-python.git
cd ~/sololink-python
sudo python setup.py install
cd ..
```

3] Clone this repository.
```
git clone ...
```

4] Copy shotmanager.conf to /etc.
```
sudo cp ~/shotmanager/sim/shotmanager.conf /etc/
```

**NOTICE**: Repeat steps 5-7 everytime you want to launch shotmanager.

5] Launch the Artoo emulator program (TestRC.py).
```
cd ~/shotmanager/sim/
python TestRC.py
```

6] Open a new terminal and launch shotmanager.
```
source shotman_venv/bin/activate
cd ~/shotmanager/
python main.py udp:0.0.0.0:14560 udpout:127.0.0.1:14550
```

7] Open a new terminal and tail the shotmanager logs.
```
tail -f /log/shotlog
```

### Tests

[ShotManager Tests](/Test) are run automatically when a patch is submitted (as part of continuous integration).

To run tests locally, navigate to the root of the ShotManager repository and run:
```
nosetests -s ./Test
```
The `-s` (optional) enables debug printing of commands to the screen.

The tests require that “mock” and “nose” be present. These should already be have been installed when you set up the developer environment, but if not you can do so via pip:

```
sudo pip install nose mock
```

## Resources

* **Documentation:**
  * [App-ShotManager Communication](/docs/App-ShotManager%20communication.md)
