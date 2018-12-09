# Open Solo Releases For Users #

***NEW: ARDUCOPTER 3.7-DEV TESTING***

[Click here for release notes and instructions](../master/install_solex.md) as of December 8, 2018 for beta testing ArduCopter 3.7-dev on the Solo.  You must already be on Open Solo to do this.  This is a major beta testing project.

## INFORMATION CURRENT FOR STABLE RELEASE OPEN SOLO v3.0.0 ON JANUARY 1, 2018 ##

The team working on safe, reliable releases of Open Solo publishes them here. You can read all the details in the release notes, and link directly to installation instructions. These are the "official" instructions. These instructions supersede any other older instructions, videos, and wikis that came before Open Solo.

### _Release notes and instructions_ ###

- Release notes for each version:
  - [Current stable release: v3.0.0](https://github.com/OpenSolo/documentation/releases/tag/v3.0.0)
  - [All releases including old betas](https://github.com/OpenSolo/documentation/releases/)

- For _stock solos and previously installed and working green cubes_, go straight to the Open Solo installation procedures:
  - [Install using the Solex app on Android](../master/install_solex.md)
  - [Install using SidePilot app on iOS](../master/initial_sidepilot.md)
  - [Install using SSH/SFTP on widows or mac](../master/initial_ssh.md)
  - [Install / recovery with SD card images](../master/install_sdimage.md)
  
- For a _brand new Green Cube installation_ please follow these updated instructions!
  - [New green cube installation procedure](../master/green_cube_install.md)

### _Support, Social Media, and other useful links_ ###

* [Solo Beta Test](https://www.facebook.com/groups/617648671719759/) group on Facebook (primary Open Solo and Green Cube support group!!)
* [Solo Mod Club](https://www.facebook.com/groups/3DRSOLOModClub/) group on Facebook
* [Solex Users](https://www.facebook.com/groups/176789056089526/) group on Facebook
* [Solex App](http://www.solexapp.com/) official website. This app is truely the future of Solo's user interface!
* [SidePilot Community](https://www.facebook.com/sidepilotapp/) on Facebook
* [Jester's Drones](http://jestersdrones.org/store/l) for the Green Cube and other cool gear
* [ProfiCNC](http://www.proficnc.com/3dr-solo-accessories/79-the-cube.html) for the Green Cube and other cool gear
* [ArduPilot](http://ardupilot.org/) homepage
* [ArduCopter Full Parameter List](http://ardupilot.org/copter/docs/parameters.html) details all 700 something parameters in ArduCopter.
* [ArduCopter introduction](http://ardupilot.org/copter/docs/introduction.html): Learn what you're getting yourself into :)
* [Mission Planner](http://ardupilot.org/planner/docs/common-install-mission-planner.html) ground station app for Windows
* [Filezilla](https://filezilla-project.org/download.php?type=client) for moving files to/from the companion computer
* [WinSCP](https://winscp.net/eng/download.php) for moving files to/from the companion computer

## Tech and Contributors ##
If you're the geeky type that wants to read all the commits to see what has been changed in Open Solo, they can all be found in the Open Solo github repositories.

- **The Build System** compiles all the code from all the repositories into functioning binaries to be loaded onto the Solo and Controller. This was a HUGE lift to make work outside of 3DR's environment. David Buzz (@davidbuzz) was the brains behind the move of _everything_ from 3DR, setup of new repos and servers, build system engineering, and a new AWS based auto-build system. The AWS system can compile from scratch in 1hr, whereas a home PC takes up to 5hrs.
  - [Meta-3DR](https://github.com/OpenSolo/meta-3dr/commits/master) is all the Yocto bitbake recipes.
  - [Solo-Builder](https://github.com/OpenSolo/solo-builder/commits/master) is the virtual machine and scripts to carry out the build.

- **The Flight Code** has numerous components that got fixes and new features. Matt Lawrence (@Pedals2Paddles) worked most of these changes.  Other contributors to the code were Tim (@FLYBYME), Morten Enholm (@Spawn32), and Hugh Eaves (@hugheaves),
  - [Sololink](https://github.com/OpenSolo/sololink/commits/master) is mostly behind the scenes stuff related to booting, networking connections, firmware loading, etc. This compiles into a version for both the Copter and Controller's IMX companion computers.
  - [Shotmanager](https://github.com/OpenSolo/shotmanager/commits/master) is all the smart shots, button and control handling, camera stuff, and most other user facing operational stuff. This compiles primarily into the Copter's IMX companion computer.
  - [Artoo](https://github.com/OpenSolo/artoo/commits/master) is the controller's STM32 firmware for the screen, buttons, and sticks.
  - [Mavlink-Solo](https://github.com/OpenSolo/mavlink-solo/commits/master) is a rather old fork of Mavlink. The flight modes were brought up to current enumerations.
  - [Sololink-python](https://github.com/OpenSolo/sololink-python/commits/master) is some misc helper python files.
  - [ArduPilot-solo](https://github.com/OpenSolo/ardupilot-solo/commits/master) is 3DR's fork of ArduCopter used on the stock Solo pixhawk 2.0 cube.



# For Developers #
***FOR DEVELOPERS!! Not for general users that just want to put Open Solo releases on their solo!!!***

## [Building Open Solo (everything)](https://github.com/OpenSolo/documentation/blob/master/SOLO-BUILDER.md)
If you want to build Open Solo, take a look at solo-builder [here](https://github.com/OpenSolo/documentation/blob/master/SOLO-BUILDER.md).  It contains everything you need to build OpenSolo from scratch and update your artoo/solo. If you want to make customisations or build something specific take a look below.
> Note: solo-builder is producing corrupt artoo stm32 binaries for some users. See the [artoo docs](https://github.com/OpenSolo/documentation/tree/master/artoo) if your artoo becomes "bricked" or doesn't turn on. (this is normally easily recoverable)

## [Artoo (the controller)](https://github.com/OpenSolo/documentation/tree/master/artoo)

[How to build the stm32 firmware](https://github.com/OpenSolo/documentation/blob/master/artoo/build-artoo-firmware.md)

[How to flash the stm32 firmware](https://github.com/OpenSolo/documentation/blob/master/artoo/flash-custom-firmware.md)

[How to unbrick artoo](https://github.com/OpenSolo/documentation/blob/master/artoo/flash-custom-firmware.md#bricked-artoo)

[How to customise start/shutdown image](https://github.com/OpenSolo/documentation/blob/master/artoo/customisation/custom-boot-screen.md)

[How to customise strings/text](https://github.com/OpenSolo/documentation/tree/master/artoo) (coming soon!)

## [Solo](https://github.com/OpenSolo/documentation/tree/master/solo)
Nothing yet :(

## How to get involved
This documentation is pretty empty right now.  If you know how Solo or Artoo works (or don't know!) and want to get involved pull requests are welcome on this documentation and all of the sub projects. (artoo, solo-builder etc)  Most of the developers are hanging out on [gitter](https://gitter.im/ArduPilot/OpenSolo) and [Facebook](https://www.facebook.com/groups/3DRSOLOModClub/).

## Special Mentions!
All of this would not be possible without 3DR.  They very generously open sourced most of their internal code and build tools to make this possible. You can see the official 3DR release statement [here](https://3dr.com/blog/announcing-opensolo/) and the ardupilot team's statement [here](https://discuss.ardupilot.org/t/opensolo-initiative-by-the-ardupilot-team).

Special thanks to Buzz and Peter for making this happen, and everyone else who has contributed to make solo even better.
