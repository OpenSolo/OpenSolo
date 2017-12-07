## Detailed Open Solo Install Using The Solex App ##
_WARNING: If you are doing a brand new green cube install, please be sure to start off with the [New Green Cube Install Instructions](../master/green_cube_install.md). This warning does not apply to stock solos and existing green cube solos._

**Please read all the instructions carefully prior to beginning. Skipping steps or doing things out of order will generally result in failure that is difficult to diagnose and repair.**

1. **Download packages:** If you haven't recently downloaded the latest files, you will need to do this first.
   - First connect your mobile device to the Solo's WiFi and open Solex.  Allow Solex to connect to the Solo and download parameters. It must make this connection first, or you will not see the firemware updates menu. This is how Solex determines it is connected to a Solo and no some other type of drone.
   - Make sure you have _Advanced Mode_ checked in the Solex application settings menu, or you will not see the firmware updates menu.
   - Switch your mobile device WiFi over to your home WiFi (or whatever WiFi, as long as it has the internet).
   - With your device connected to the internet, go into the Solex firmware updates menu.
   - Press the _clean up_ button, then the _refresh_ button to make sure you're seeing the latest files.
   - Download the Open Solo Clean Install packages (solo and controller) by tapping the packages. _Available_ will change to _downloaded_ once complete.
   - The installation packages are ~80MB each, so it will take a little longer to download than you may be used to.

2. **Reconnect:** Once you've downloaded both, reconnect your mobile device to the Solo WiFi and make sure Solex says connected to vehicle. Again, your solo and controller must be fully charged, powered on, paired, connected, and not malfunctioning. 

3. **Install:** From the firmware updates menu in Solex, tap the _Open Solo Clean Install_ package that you previously downloaded. Again, be patient while numerous large files are extracted and scripts execute. Do not push buttons, exit the app, mess with the Solo, etc. Let it do its thing. Do this for both the controller package and the copter package. The process the same. You must do both.  Do no reboot or do anything else between installs.

4. **Reboot:** Power cycle the Solo and controller once the Solex installation packages have both completed successfully. When they power back on, they will automatically begin a factory reset procedure. Since we just installed Open Solo on the recovery partitions, they are factory resetting to Open Solo! They will then automatically execute a second update procedure, cleanly installing Open Solo on the system partition.
    - You will likely hear the Pixhawk reboot 4 to 5 times. You may hear the firmware success happy tones from the pixhawk as well. All normal.
    - You will likely see the controller reboot and say update success twice. This is also normal.
    - It is difficult to know exactly what stage it is at since it can't speak and isn't telepathic. The process takes about 10 minutes on both the solo and the controller.  So just wait about 10 minutes.
    - If you have a green cube, the lights should switch to "aviation mode" after the 4th or 5th reboot, which is good indication it is done. There is no such indication for the stock cube, so just go by the 4 or 5 reboots.

5. **Pair:** Hit the pair button under the Solo with a small pointy poking apparatus like a paper clip for 2 seconds to get the controller and solo re-paired. When the controller tells you it has detected the solo, hold the A and B button for 3 seconds... which is the second set of vibrations... until the the screen says pairing in progress.

6. **Reconnect mobile device:** You will need to reconnect your mobile device to Solo's WiFi now.  Since it did a factory reset, the Solo and controller are using their default WiFi SSID and password (the default password is `sololink`).

7. **Load applicable parameter packages:** If you have a Green Cube, and/or a HERE GPS/Compass, and/or Ian's landing gear mod, you will need to install some applicable parameter packages now.  If you have none of these modifications, you can skip this step.
   - Tap each package in the Solex Firmware Updates menu to install the parameters. You do not need to reboot after each one. Install all the applicable pacakges in this order, then reboot the Solo at the end.
   - If you have a green cube, load the _ArduCopter 3.5.x Parameters_ package first before any others.
   - If you have the HERE gps/compass, load the _HERE Parameters_ package.
   - If you have the landing gear mod, load the _Landing Gear Parameters__ package.
   - Reboot the solo after loading all the applicable packages.

8. In the Solex vehicle settings menu, you can verify everything installed by scrolling to the bottom and looking at the listed version information. Controller and Vehicle should say 2.4.93 for now since I can't put "-RC3") in it.  Controller FW should say Open Solo 2.5-RCx.  And autopilot FW should say 1.5.4 for a stock cube, and 3.5.x for a green cube.

### Installation Complete! ###
Proceed to the [post-installation instructions!](../master/install_post.md)
