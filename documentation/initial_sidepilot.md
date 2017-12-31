## Detailed Install Using The SidePilot App ##

1. **Download packages:** With your device connected to the Internet, go into the SidePilot 'Help & Settings' menu, and tap the '3DR Solo Firmware Upgrade' menu and download the Open Solo Clean Install packages (solo and controller). You can do this either before or after connecting to Solo's WiFi_.  The installation packages are 75MB each, so it will take a little longer to download than you may be used to. If you don't see the Firmware Updates menu, make sure you have 3DR Solo selected as your connection type.

2. **Connect:** Once you've downloaded both, connect your mobile device to the Solo WiFi and tap the connect button in the top right corner of the SidePilot main screen. Ensure you begin receiving telemetry data before continuing. Again, your solo and controller must be fully charged, powered on, paired, connected, and not malfunctioning. 

3. **Install:** From the firmware updates menu in SidePilot, tap the _Open Solo 2.5-RC1 Clean Install_ package that you previously downloaded. Read the instructions and continue with the installation by tapping the 'Install' button. Again, be patient while numerous large files are extracted and scripts execute. Do not push buttons, exit the app, mess with the Solo, etc. Let it do its thing. Do this for both the controller package and the copter package. The process the same. You must do both.

4. **Reboot:** Power cycle the Solo and controller once the Solex installation packages have both completed successfully. When they power back on, they will automatically begin a factory reset procedure. Since we just installed Open Solo on the recovery partitions, they are factory resetting to Open Solo! They will then automatically execute a second update procedure, cleanly installing Open Solo on the system partition.
    - You will likely hear the Pixhawk reboot 2-3 times. This is normal.
    - You will likely see the controller reboot and say update success twice. This is also normal.
    - It is difficult to know exactly what stage it is at since it can't speak and isn't telepathic. The process takes about 6 minutes on both the solo and the controller.  So just wait about 6 minutes.

5. **Pair:** Hit the pair button under the Solo with a small pointy poking apparatus like a paper clip for 2 seconds to get the controller and solo re-paired. When the controller tells you it has detected the solo, hold the A and B button for 3 seconds... which is the second set of vibrations... until the the screen says pairing in progress.

6. **Reconnect mobile device:** You will need to reconnect your mobile device to Solo's WiFi now.  Since it did a factory reset, the Solo and controller are using their default WiFi SSID and password (the default password is `sololink`).

7. **Load applicable parameter packages:** If you have a HERE GPS/Compass or a retractable landing gear mod, you will need to install some applicable parameter packages now.  If you have none of these modifications, you can skip this step.
   - Tap each package in the SidePilot Firmware Updates menu to install the parameters. You do not need to reboot after each one.
   - If you have the HERE gps/compass, load the _HERE Parameters_ package.
   - If you have the landing gear mod, load the _Landing Gear Parameters__ package.
   - You do _not_ need to load the ArduCopter parameters or ArduCopter firmware packages!!!
   - Reboot the solo after loading all the applicable parameter packages.
   
### Installation Complete! ### 
Proceed to the [post-installation instructions!](../master/install_post.md)
