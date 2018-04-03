WARNING - WORK IN PROGRESS

```
This code is known to be high risk , but also early-adopter friendly.  

We will remove this warning from the repository when it is no longer required.
```


# artoo

firmware for Artoo, the Solo controller

### requirements

* ARM GCC Embedded - toolchain to build firmware. https://launchpad.net/gcc-arm-embedded
* tup - build tool. http://gittup.org/tup/ (install via homebrew on OS X)
  * fuse-dev is required as a prerequisite to set up tup on Ubuntu (install via `apt-get install libfuse-dev`)
* pillow - image manipulation in tools/image-codegen.py. http://python-pillow.github.io (install via `pip install pillow` or similar for your env)
  * note - you'll also need libfreetype installed *before* installing pillow. (`brew install freetype` on OS X)
  * on at least one Ubuntu 14.04 image, `apt-get install python-pillow` was required, rather than `pip install pillow`
  * on at least one other Ubuntu 14.04 image, `pip install --upgrade pillow' was required, to force getting pillow 2.7.0 rather than using Ubuntu's 2.3.0
* pymavlink - only required when running tools/slip-mavlink.py. http://qgroundcontrol.org/mavlink/pymavlink (install via `pip install pymavlink` or similar for your env)

To build with tup, simply invoke it at the root of the project directory:

    $ tup

# to build inside vagrant: 
cd OpenSolo/artoo
vagrant up
vagrant ssh
cd /vagrant
tup

### dev environment

I'm primarily using Qt Creator (https://qt-project.org/downloads) for editing, which is tracked in the following project files: artoo.{config, creator, files, includes}

Any editor you like should be fine, though.

I've been using a Black Magic Probe for debug, the easiest way to setup is to copy the sample gdbinit file:

    cp gdbinit.sample .gdbinit

Start a debug session:

    $ arm-none-eabi-gdb artoo.elf
    $ ... GDB startup ...
    $ (gdb) load
    $ (gdb) run

If you get super hosed, you may need to execute `mon connect_srst enable`, possibly with the reset button held, in order to recover.

#### stick calibration

Stick calibration data (along with other params) are stored in the STM32's MCU flash. There exists as GUI to calibrate them as part of the manufacturing process, but if you're interested in calibrating an existing Artoo, use `tools/stick-cal.py` as follows:

* copy both `tools/slip.py` and `tools/stick-cal.py` to the iMX6 board in your Artoo unit, via `scp` or similar
* `ssh` into the iMX6, and run `python stick-cal.py`, move the sticks and camera controls to their extremes, then press `ctrl-C` to complete the calibration

#### test against simulation

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

#### semihosting

For print/log-based debugging, semihosting support is available (i've only tested this with Black Magic Probe, though hopefully openocd supports it as well).

In the top level Tupfile, uncomment `SEMIHOSTING := yes` and rebuild. You can now use the `DBG_LOG()` macro in the same way that you'd use `printf()` (it's aliased directly to printf when semihosting is enabled) and you should see the output in your gdb session.

Code should not be checked in with semihosting enabled, since we don't want to link against those libraries in a production build.


