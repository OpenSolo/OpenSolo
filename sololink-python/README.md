WARNING - WORK IN PROGRESS

```
This code is known to be high risk , but also early-adopter friendly.  


We will remove this warning from the repository when it is no longer required.

```

pip -i install requirements.txt
python setup.py build


# sololink-python

This is a Python interface for SoloLink. 

## Overview

*sololink-python* is used by the ShotManager button manager to get information about Controller (Artoo) button events (A,B,Pause,Fly), to get and remap RC stick values (from PWM into the more easily processed -1 to 1 range), and to send information for display on the Controller (for example, the current shot if in a shot or the mode).

## Dependencies (upstream and downstream)

This project is dependent on:

* SoloLink - This contains all the *3DR-created* software in the Yocto image running on the Companion Computer (i.MX6).


The project is a dependency of:

* ShotManager - ShotManager is a Python application that governs smart shots, GoPro control, and some Solo Controller (Artoo) functionality.

* meta-3dr - This contains the central definition of how the whole i.MX6 Yocto image is constructed. It contains [Bitbake](https://www.yoctoproject.org/tools-resources/projects/bitbake) recipes for the different included software, including ShotManager, SoloLink etc. 


## Developer Setup

sololink-python is tested as part of ShotManager (for example, RC Mapping is tested as part of `/shotmanager/sim/TestRC.py`.)

## Resources

* The API is documented in-source.

