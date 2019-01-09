# ARTOO STM32 FIRMWARE #

The controller's STM32 is the hardware behind the buttons, sticks, and display.  It is a separate piece of hardware from the IMX linux computers.  When the solo-builder runs to compile the full copter and controller images, this Artoo STM32 firmware is included.  You can aso run the Artoo STM32 builder here separately if you only want to make changes to it.  It is fast and simple compared to the entire copter and controller builds.

Some compiled versions of the Artoo STM32 firmware can be found in the [/Firmware/Artoo STM32](/Firmware/Artoo) directory.

***

## Building the Artoo STM32 Firmware ##

To build the Artoo STM32 firmware, you must use the vagrant virtual machine, which will have everything configured by script. We can assure with 100% confidence that trying to run the builder natively on your own linux machine will not work.  The vagrant VM is configured to have all required packages, and uses Ubuntu 14.04.  Nothing newer will work.  Do not attempt to upgrade the Vagrant VM, even if it suggests you do so.  Everything will explode.

_The vagrant VM used for Artoo is also used for solo-builder.  So if you already installed and setup the VM for solo-builder, you can skip right to executing the build._

### Initial Vagrant VM Setup ###

Visit the [Open Solo Vagrant VM readme](/vagrant_readme.md) for first time installation and initialization of the Vagrant VM.

### Executing Build ###

 1. `vagrant up` from the root of root of the OpenSolo repo directory (windows command prompt or ubuntu terminal) starts the VM
 
 2. `vagrant ssh` connects you to the vagrant VM, where you will do all the building  
 FYI `vagrant@vagrant-ubuntu-trusty-64:~$` is what the prompt will look like once you're connected. You will land in the home directory (`~/`)  
 FYI `/vagrant` within the vagrant VM is symlink to the root of the OpenSolo repo outside the vagrant VM.
 
 3. `$ cd /vagrant/artoo` changes to the artoo directory

 4. `$ ./tup` executes the build.

 #### Completed files ####
 
 The build produces `artoo.bin` which is deposited in the /artoo directory.  You can use it as is, or you can rename it.  If you rename the file, it must always begin with `artoo_` and must have a `.bin` extension.

***

## Install Artoo STM32 Firmware On Controller ##

The default filename is `artoo.bin`.  You can rename it, as long as it begins with `artoo_`.  For example, you can name the file `artoo_1234xyz.bin`.  This firmware can be installed directly using SCP or and SFTP application. Connect your PC to the Solo's WiFi. If you never changed the Solo's wifi password, the default is sololink.

_Doublecheck the .bin file to make sure it is about 200-300kb in size. If it's 0kb, the build failed and it shouldn't be loaded_
  1. Connect via SCP or an SFTP application to the **controller** with IP 10.1.1.10, username root, password TjSDBkAu
  2. Copy `artoo.bin` to the `/firmware` directory on the controller.
  3. Reboot the controller.  When powering up, the display will go out and come back on during the update.

If you inadvertantly flash an empty or bad .bin file, it is generally easy to fix.  Simply redo these steps using a known good .bin file and it will load.

[How to customise start/shutdown image](/documentation/artoo/customisation/custom-boot-screen.md)

***

## Stick Calibration ##

--THIS NEEDS TO BE UPDATED--
Stick calibration data (along with other params) are stored in the STM32's MCU flash. There exists as GUI to calibrate them as part of the manufacturing process, but if you're interested in calibrating an existing Artoo, use `tools/stick-cal.py` as follows:

* copy both `tools/slip.py` and `tools/stick-cal.py` to the iMX6 board in your Artoo unit, via `scp` or similar
* `ssh` into the iMX6, and run `python stick-cal.py`, move the sticks and camera controls to their extremes, then press `ctrl-C` to complete the calibration

***

## Using with ArduPilot SITL ##

It is possible to do some basic testing against a simulated vehicle with the SITL environment provided by ardupilot. http://dev.ardupilot.com/wiki/setting-up-sitl-on-linux should get you set up to run it.

To connect your board to the simulation environment:

* connect an FTDI cable (or similar) to the UART that is normally connected to the iMX6
* if using a VM, pass the virtual serial device into the VM
* run `tools/slip-mavlink.py` (within the VM if you're using one) - this translates mavlink data from SITL into SLIP encoded data, and passes it to the STM32. It should print the IP address it's listening on - pass this to the `--out` argument of SITL when you start it below.

From within the ardupilot project folder, start up SITL and then :

    $ cd ArduCopter
    $ ../Tools/autotest/sim_vehicle.sh --console --out xxx.xxx.xxx.xxx
    $ ... SITL starts up ...

Now, stick values and mavlink data are sent bidirectionally between artoo<->SITL, and you should be able to fly as normal.
