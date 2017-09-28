# GREEN CUBE INSTALLATION #

1. Prior to installing the Green Cube, you must install Open Solo. This installation needs to be complete and operational. Follow all the instructions up to and including all calibrations and test flying.  Open Solo can be found here: https://github.com/OpenSolo/documentation/releases.

2. **Remove the battery tray:** Remove the battery and pop off the GPS cover.  Then unscrew all the small black screws around the battery tray. The battery tray can now be lifted up.  Unplug the GPS from the carrier board.  Set the battery tray aside. We highly recommend you do not lose the screws.
   ![Battery Tray Screws](https://github.com/ArduPilot/SoloScripts/blob/master/Misc/battery_tray_screws.jpg)

3. **Lift up the carrier board:** Locate the comparatively large silver screw on the right side toward the front. Unscrew that and set it aside with all the other screws that you're not going to lose.  The carrier board can now be lifted up very carefully.  You will need to fidget with the wires from the motor pods a bit.  The board will need to go up a bit, then shift back, then shift up the rest of the way. The left side can go up higher than the right, which is convenient.  It's kind of tight and generally annoying.  Be careful not to break the small wires.  Don't break any of the other wires either.  You will need to get the board high enough up to expose the Pixhawk mounted underneath it.  It's the black cube looking device.
   ![carrier screw](https://github.com/ArduPilot/SoloScripts/blob/master/Misc/carrier_retainer_screw.jpg)
   ![wires](https://github.com/ArduPilot/SoloScripts/blob/master/Misc/carrier_board_wires.jpg)

4. **Unscrew the stock pixhawk:** There are 4 very small screws on the top of the carrier board. Unscrew them and set them aside. The stock Pixhawk can now be removed. It will pull down off the carrier board. Set the stock Pixhawk aside somewhere safe. You will want to keep it.
   ![Pixhawk screws](https://github.com/ArduPilot/SoloScripts/blob/master/Misc/pixhawk_screws.jpg)

5. **Install the green cube:** The green cube installs the same way the old one came off.  Plug it into the carrier board from the bottom. When it's lined up properly, it should only take a gentle squeeze and you should hear a click as the connector seats.  Then put in the four screws.
  ![cube installed](https://github.com/ArduPilot/SoloScripts/blob/master/Misc/cube_installed.jpg)
  
6. **Do not reassemble yet:** It is best to do the initial firmware install with the Solo still opened up. If anything goes wrong, it avoids having to disassemble it again. 

7. **Power up the Solo and reconnect to controller:** Put the battery onto the solo. It will just sit atop the carrier board. Obviously you should avoid manhandling the Solo while like this since the battery can just fall off. So get everything situated first.  Turn on the battery.  The solo will power up as usual. After a short while, the Solo will reconnect with the controller as usual. It will probably give you all kinds of warnings about calibration. This is normal and expected.

8. **IF THE SOLO DOES NOT BOOT UP PROPERLY, DO NOT CONTINUE BEYOND THIS STEP UNTIL IT IS FIXED:**
    - Connect via WinSCP or Filezilla
    - Download 3dr-solo.log, boot.log, and python_stderr.log. Post them in the Facebook beta group or forum for analysis
    - Most likely, this can be fixed by hooking up to the cube via USB and using Mission Planner to load ArduCopter Firmware
    - Help and troubleshooting is again available in the Facebook beta testing group.
    
9. **Load the firmware and parameters using Solex**
     * In the Solex menu all the way at the bottom, select `Firmware Updates`.
     * While your device has an internet connection, hit the refresh button to pull down the latest from the server.
     * While your device has an Internet connection, click the required packages to download them. `ArduCopter_x_Firmware.zip`, and `ArduCopter_x_parameters.zip`. The available status will change to downloaded for each one.
     * If not already, reconnect to the Solo's WiFi and make sure Solex says it's connected to vehicle.
     * **Install ArduCopter:** In the Solex firmware updates menu, tap the `ArduCopter 3.5.x Firmware` package. Read the notice and select `install`. All the files will be copied to the Solo in all the right places. When prompted, power cycle the Solo. It will reboot, then switch into bootloader mode. Normally you will see disco lights while it's doing this. But if the LED driver isn't enabled, you may not. Don't worry. It's working. Give it 3-5 minutes to process. You may hear some clicks as the Pixhawk reboots. After 3-5 minutes, you will hear some tones signalling completion. It will come back to life, reconnecting with the controller and Solex. 
     * **Reset Parameters:** With the Solex app reconnected to the Solo, click the `Reset Params` button on the firmware update screen of Solex.  When prompted, power cycle the solo.
     * **Load Parameters:** With the Solex app reconnected to the Solo, click the `ArduCopter 3.5.x Parameters` package. Read the notice and select `install`. If you have the HERE or landing gear, go ahead and load those parameter packages now too, prior to rebooting. One you've loaded the parameters pacakges, reboot the solo.
     * **Complete:** The solo will reboot and reconnect to the controller and apps.  You will notice the LEDs now look like an aircraft rather than a car. Installation complete!

10. **Reassemble the Solo** once the installation has completed successfully. Make sure you don't have any screws left over.  Make sure all the wires, including the GPS and motor pods, are plugged back in.

### Installation Complete! ###
Proceed to the [post-installation instructions!](../master/install_post.md)

