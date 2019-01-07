## Detailed Open Solo 4 Install Using The Solex App ##
_Note: If you are doing a brand new green cube install, please be sure to start off with the [New Green Cube Install Instructions](../master/green_cube_install.md). This warning does not apply to stock solos and existing green cube solos._

**Please read all the instructions carefully prior to beginning. Skipping steps or doing things out of order will generally result in failure that is difficult to diagnose and repair.**

***These instructions are for Solex version XXX released on XXX, or higher versions.  Please ensure your mobile device has the latest version of Solex installed via the Google Play Store.***

1. **Download packages:** If you haven't recently downloaded the latest files, you will need to do this first.
   - First connect your mobile device to the Solo's WiFi and open Solex.  Allow Solex to connect to the Solo and download parameters.
   - Make sure you have _Advanced Mode_ checked in the Solex application settings menu, or you will not see the firmware updates menu.
   - Switch your mobile device WiFi over to your home WiFi as you will need high speed internet to download the packages
   - With your device connected to the internet, go into the Solex _Firmware Updates_ menu.
   - Press the _clean up_ button, then the _refresh_ button to make sure you're seeing the latest files.
   - Download the Open Solo Clean Install packages (solo and controller) by tapping the packages. _Available_ will change to _downloaded_ once complete. The installation packages are ~75MB each, so it will take a little longer to download than you may be used to.
   - If you have the HERE GPS or retractable landing gear mods, also download those parameter packages.
   - You do _not_ need the ArduCopter parameter package or the ArduCopter firmware package for this process.

2. **Reconnect:** Once you've downloaded both, reconnect your mobile device to the Solo WiFi and make sure Solex says connected to vehicle. Again, your solo and controller must be fully charged, powered on, paired, connected, and not malfunctioning. You may need to press the connect button in Solex to force it to reconnect.

3. **Install Copter Package:** From the firmware updates menu in Solex, tap one of the _Open Solo Clean Install (Copter)_ package that you previously downloaded.
   - Press install. Press install again when prompted again to confirm. _This is your last chance to change your mind_.
   - Again, be patient while numerous large files are extracted and scripts execute. Do not push buttons, exit the app, mess with the Solo, etc. Let it do its thing. Until it says it has completed.
   - The solo will click and lights will go disco.  At this time, ArduCopter 3.7 firmware is being pre-installed on the Cube. This step takes about 1 minute and Solex will tell you when the whole process is complete.
   - _Stock cube users upgrading from the old firmware:_ you will not get any happy tones to indicate firmware loading completed, and the lights will stay disco. This is not a problem, and this is why we're pre-loading the firmware now.  
   - **DO NOT REBOOT THE COPTER YET!** You must do the install for both the copter and controller before rebooting anything. Once Solex tells you the install is complete, leave the copter and move on to the controller install.

4. **Install Controller Package:** From the firmware updates menu in Solex, tap one of the _Open Solo Clean Install (Controller)_ package that you previously downloaded.
   - Press install. Press install again when prompted again to confirm. _This is your last chance to change your mind_.
   - Again, be patient while numerous large files are extracted and scripts execute. Do not push buttons, exit the app, mess with the Solo, etc. Let it do its thing. Until it says it has completed.
   - Solex will tell you when the whole process is complete.

5. **Reboot:** Power cycle the Solo and controller once the Solex installation packages have both completed successfully. When they power back on, they will automatically begin installations.
    - *If you began this installation while already in a factory reset state*, the installer scripts will install Open Solo directly to the system partition.  The recovery partition will not be updated to Open Solo 4, since that's the partition you're currently on.  Updating the recovery partition can be done later very easily.  You will likely hear the cube reboot and flash its lights twice (firmware install and parameter reset). You will see the controller reboot and say update success once.
    - *If you began this installation in a working state (not factory reset)*, the installer scripts will install Open Solo into the recovery partition, then execute a factory reset procedure automatically. Since we just installed Open Solo on the recovery partitions, they are factory resetting to Open Solo! They will then automatically execute a second update procedure, cleanly installing Open Solo on the system partition. You will likely hear the Cube reboot 3 times (firmware install at factory reset, firmware install on system, parameter reset). You will see the controller reboot and say update success twice.
    - It is difficult to know exactly what stage it is at since it can't speak and isn't telepathic. The process takes about 6 minutes on both the solo and the controller.  So just wait about 6 minutes.

6. **Pair:** Hit the pair button under the Solo with a small pointy poking apparatus like a paper clip for 2 seconds to get the controller and solo re-paired. When the controller tells you it has detected the solo, hold the A and B button for 3 seconds... which is the second set of vibrations... until the the screen says pairing in progress.  If they are not pairing, they may have timed out.  Reboot both and try again.

7. **Reconnect mobile device:** You will need to reconnect your mobile device to Solo's WiFi now.  Since it did a factory reset, the Solo and controller are using their default WiFi SSID and password (the default password is `sololink`).

8. **Load applicable parameter packages:** If you have a HERE GPS/Compass or a retractable landing gear mod, you will need to install some applicable parameter packages now.  If you have none of these modifications, you can skip this step.
   - Tap each package in the Solex Firmware Updates menu to install the parameters. You do not need to reboot in between
   - If you have the HERE gps/compass, load the _HERE Compass Parameters_ package.
   - If you have the landing gear mod, load the _Landing Gear Parameters_ package.
   - You do _not_ need to load the ArduCopter parameters or ArduCopter firmware packages!!!
   - Reboot the solo after loading all the applicable parameter packages.

9. In the Solex vehicle settings menu, you can verify everything installed by scrolling to the bottom and looking at the listed version information. Controller and Vehicle should say 3.0.0.  Controller FW should say Open Solo 3.0.0.  And autopilot FW should say 1.5.4 for a stock cube, and 3.5.4 for a green cube.

### Installation Complete! ###
Proceed to the [post-installation instructions!](../master/install_post.md)
