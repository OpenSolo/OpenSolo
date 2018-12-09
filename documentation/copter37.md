# ArduCopter 3.7 Dev Testing

Once complete, ArduCopter 3.7.0 will be the first stable release version compatible with all Solos.  The next full release of Open Solo will include ArduCopter 3.7.0.

_Please read this entire set of release notes and instructions.  Every word is critical to doing this right._

## WHO

- This test version is compatible with all Solos, whether they have a stock cube, a green cube, or a new black cube
- Contains motor output slew time limit, previously only present in the old 3DR firmware which is required with the stock cube
- You must already have Open Solo installed and working properly!!!
- You must already have Open Solo installed and working properly!!!
- You must already have Open Solo installed and working properly!!!

**Stock/Black Cube Users:** This will be a huge upgrade for you. You are leaping 3+ years into the future of ArduPilot from the old circa 2015 modified ArduCopter 3.2.  This is the first time the slew rate limiting code has been brought into ArduCopter master, and as such is the first time you can safely fly it in a stock/black cube Solo.  You are the most important test users!

**Green Cube Users:** You can still install and fly this. It will handle the same as a stock/black cube Solo will handle.  The slew limiting parameter is enabled by default, and the PID tuning parameters reflect that as well.  You may notice a slight reduction in how crisp and snappy it handles, as is the nature of the slew rate limiting. But there are no other ill-effects.  You will also have all the other new features that come with 3.7 to test out (flight modes, ChibiOS, etc).  The more uses that test and tune this, the better.  So even if you have a Green Cube, please give this a whirl.

## WHAT

### ArduCopter 3.7-Dev + Patches

The test package contains ArduCopter 3.7-dev (master) as of Saturday 12/8/2018.  This build of ArduCopter 3.7-dev has upcoming patches for the slew rate limiting required by the stock cubes and restoring the GoPro automatic power-off.  These two patches will be merged into master once we do this testing.  ArduCopter 3.7-dev is light years ahead of the old 3DR firmware, which was based on ArduCopter 3.2 in 2015.  It is also significantly ahead of the version that shipped with Open Solo for Green Cubes, which was ArduCopter 3.5.4.  _All required parameter values are baked in by default!! You do NOT need to load any parameter files._

### Updated Python Files For IMX

Numerous python files are included which will be loaded onto the Solo's IMX companion computer.  These files allow access to all of ArduCopter's new flight modes.  They also add error handling and anti-brick code to the firmware loading process.

## WHEN

Testing is needed ASAP. ArduCopter 3.7.0 will likely be released in the next few months.  By getting all of this tested now, we can ensure that 3.7.0 is 100% compatible with all Solos.

## HOW

### Prepare

- You must already have Open Solo installed and working properly!!! It doesn't matter if it's the Green Cube or stock cube ArduCopter on there.  It just has to be Open Solo already.
- You must have the Solex or SidePilot app to load the installer packages and use the new features.  And the app must be updated with the latest for the Play Store / App Store.
- You must be willing to be a test pilot. This may not be perfect yet.  It could explode in mid-air, or crash, or do something else we couldn't predict. Please give us your feedback!!

### INSTALL

#### ArduCopter Firmware

1. **While connected to the Internet**, go to the Solex FW Updates menu.  Press refresh and cleanup.
2. Tap the _ArduCopter 3.7-Dev Slew Test_ package.  Tap download. Available will change to downloaded once complete.
3. Tap the _ArduCopter 3.6 and 3.7 Controller Update_ package.  Tap download. Available will change to downloaded once complete.
4. **Reconnect to Solo WiFi** and Connect Solex to the Solo. Allow parameter download to complete.
5. In the Solex FW Updates menu, tap the _ArduCopter 3.7-Dev Slew Test_ package. Tap install and proceed.
6. When prompted, you can close the FW install menus in Solex.
7. Turn the Solo off and back on. It will click and the lights will go disco.
8. Completing Installation:
   - _**If you are upgrading from the old 3DR firmware on a stock cube:** it will not stop the disco lights and will not play the happy tones when it is done installing.  Therefore, just wait 3 minutes. Then power off the Solo and power it back on.  When it boots back up, you'll have the new lights and everything will be fine._
   - _**If you are upgrading from ArduCopter 3.5 or 3.6 on a Green Cube:** The lights will go back to normal and you'll get the happy tones once installation is complete._
9. If the Solo and Controller do not automatically reconnect promptly, simply reboot both of them.

#### Parameter Reset

1. Connect Solex to the Solo. Allow parameter download to complete.
2. In the Solex FW Updates menu, tape the _RESET PARAMS_ button and proceed.
3. Turn the Solo off and back on.
4. You will probably get warnings about calibrations required, since all prior calibrations were wiped out.
5. If you have a HERE, you should now go back into the Solex FW updates menu to reload that parameter package and reboot again.

#### Controller Update

1. Connect Solex to the Solo. Allow parameter download to complete.
2. In the Solex FW Updates menus, tap the _ArduCopter 3.6 and 3.7 Controller Update_ package. Tap install and proceed.
3. Controller screen will eventually go black during install.
4. When prompted, press A button to continue.
5. If the Solo and Controller do not automatically reconnect promptly, simply reboot both of them.

### Post-Install Calibrations & Settings

Proceed to the [post-installation instructions](../master/install_post.md) to do all the usual calibrations.

## TESTING

- Fly it.  We need people to report how it handles and how the flight modes are working out.
- Tune it.  If you are familiar with ArduCopter PID tuning, and want to try dialing it even better, please do so and report your results
- Feedback is needed.  Please tell us everything you like or dislike. Tell us what worked and didn't work. 

## WARNING: Do not use the _very fast_ speed slider setting in Solex until further notice.  There is an error in the acceleration value sent to the Solo, and it will handle very poorly.  All other speed sliders from very slow up to and including fast work fine.  Once this is fixed in the next Solex update, this warning will be removed.
