# Open Solo Releases For Users #
The team working on safe, reliable releases of Open Solo publishes them here. You can read all the details in the release notes, and link directly to installation instructions. These are the "official" instructions. These instructions superceed any other older instructions, videos, and wikis that came before Open Solo.

### _Release notes and instructions_ ###
- [Open Solo Release Notes](https://github.com/OpenSolo/documentation/releases)
- [Install using the Solex app on Android](../master/install_solex.md)
- [Install using SidePilot app on iOS](../master/initial_sidepilot.md)
- Install using SSH/SFTP on widows or mac (No procedure has been created yet)
- [New green cube installation procedure](../master/green_cube_install.md)

### _Support, Social Media, and other useful links_ ###
* [Solo Beta Test](https://www.facebook.com/groups/617648671719759/) group on Facebook (primary Open Solo support group!!)
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


# Building Open Solo For Developers #
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
