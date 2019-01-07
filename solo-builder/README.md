# Solo Builder #
The solo-builder will create file system images for the Solo's IMX and the controller's IMX. The Open Solo vagrant virual machine is used for the build environment. The vagrant VM used for solo-builder is also used for the Artoo STM32 firmware builder. So if you already installed and setup the VM for artoo, you can skip right to executing the build.

## Instructions ##

### Initial Vagrant VM Setup ###

Visit the [Open Solo Vagrant VM readme](/vagrant_readme.md) for first time installation and initialization of the Vagrant VM.

### Executing Build ###

 1. `vagrant up` from the root of root of the OpenSolo repo directory (windows command prompt or ubuntu terminal) starts the VM
 
 2. `vagrant ssh` connects you to the vagrant VM, where you will do all the building
    * FYI `vagrant@vagrant-ubuntu-trusty-64:~$` is what the prompt will look like once you're connected. You will land in the home directory (`~/`)
    * FYI `/vagrant` within the vagrant VM is symlink to the root of the OpenSolo repo outside the vagrant VM.
 
 3. `$ cd /vagrant/solo-builder` changes to the solo-builder directory

 4. `$ ./builder.sh` executes the build. See below for command line options. On first run, you will be prompted to restart the builder after syc completes.

#### Command line options ####

`% builder.sh` with no options will build the copter IMX, controller IMX, and the Artoo STM32 firmware.

`$ builder.sh -a -m -c -n ` option arguments are available:
 * `-a false` will skip building the Artoo STM32 FW and use what is already in the recipe files directory. Default is true if not specified.
 * `-m both` will build both the copter and controller IMX. This is the default if not specified.
 * `-m solo` will build only the copter's IMX, not the controller.
 * `-m controller` will build only the controller's IMX, not the copter.
 * `-c true` will clean the build recipies prior to beginning the build.  Default is false if not specified.
 * `-n true` nuclear option deletes the build directory (`/vagrant/solo-build/`) to start from a totally clean slate. Default is false if not specified.

#### Completed files ####

Completed binaries will be copied to a date-time stamped folder in /solo-build/binaries.
 * `3dr-solo.tar.gz` and `3dr-solo.tar.gz.md5` for the copter's IMX
 * `3dr-controller.tar.gz` and `3dr-controller.tar.gz.md5` for the controller's IMX
 * `artoo.bin` for the controller's STM32 (already included within the controller IMX build)

### Exiting The Builder ###

 * `$ exit` will exit the vagrant SSH session, returning you to the PC's command prompt.
 * `vagrant halt` will shutdown the VM.

## TO-DO ##

`ERROR: Function failed: Fetcher failure for URL: 'git://git.gnome.org/gtk-doc-stub'. Unable to fetch URL from any source` will happen the first time you run the build from scratch.  This is a false error, as the repo is fetched and available.  Restart the build, and it will proceed just fine.  Needs to be fixed somehow.
