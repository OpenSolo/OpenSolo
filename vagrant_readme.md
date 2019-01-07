# Open Solo Vagrant VM #
The solo-builder and Artoo STM32 builder both operate with Open Solo's vagrant virtual machine (VM).

You must use the vagrant virtual machine, which will have everything configured by script. We can assure you with 100% confidence that trying to run the builders natively on your own linux machine or otherwise outside of this vagrant VM will not work.  The vagrant VM is configured to have all required packages, and uses Ubuntu 14.04.  Nothing newer will work.  Do not attempt to upgrade the Vagrant VM, even if it suggests you do so.  Everything will explode.

_The vagrant VM is used for aolo-builder and the Artoo builder (tup).  The instructions for both will reference this readme for intial VM setup._

### Install Applications ###

***Windows Users*** download and install the following if you don't already have them:
* Virtual Box: https://www.virtualbox.org/wiki/Downloads
* Vagrant: https://www.vagrantup.com/downloads.html
  
 ***Ubuntu Users*** install the following packages if you don't already have them:
 * `$ sudo apt-get install virtualbox`
 * `$ sudo apt-get install vagrant`

### Initialize The VM ###

`$ vagrant up` from the root of root of the OpenSolo repo directory (windows command prompt or ubuntu terminal). The vagrant VM will create itself. Scripts will run to install all the required packages in the VM. This will take approx 30 minutes on a typical internet connection. Once complete, you will be returned to the commmand prompt.

### Vagrant VM Control ###

The follownig vagrant commands are available and useful. From the root of root of the OpenSolo repo directory (windows command prompt or ubuntu terminal): 
 * `vagrant up` starts up the VM and returns you to the command prompt once complete.  Do this to begin.
 * `vagrant halt` stops the VM and returns you to the command prompt once complete.  Do this when you're done.
 * `vagrant destroy` deletes the VM entirely.  Do this if you break it and start over with the initial vagrant VM setup above.
 * `vagrant status` returns the status of the VM.
 * `vagrant ssh` brings you into the VM. This is where you will execute and monitor the build.

### Executing Builds ###

 * Visit [solo-builder](../master/solo-builder) for steps to build the complete copter and controller firmware
 * Visit [artoo](../master/artoo) for steps to build just the Artoo STM32 firmware
