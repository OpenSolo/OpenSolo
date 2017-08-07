# Building artoo's firmware
This guide gets you up to speed with how to compile and flash your own firmware for artoo's stm32 chip.  This chip does all the hardware interfacing like processing inputs and drives the LCD screen.  This means you can customise graphics, text and even add new features.

## Requirements
* Currently ubuntu 17.04 is the only supported/tested operating system.
* At a minimum tup should be installed ([see here](http://gittup.org/tup/))

## Let's Start
First, clone the repository containing the artoo firmware:
```
git clone https://github.com/OpenSolo/artoo.git
```
Navigate into the directory:
```
cd artoo
```
Start the build process:
```
sudo tup
```
A successfull build should end with something like this:
```
 67) [0.015s] arm-none-eabi-objcopy -O binary artoo.elf artoo.bin              
 68) [0.019s] arm-none-eabi-objcopy -O ihex artoo.elf artoo.hex                
 [                   ETA=<1s Remaining=0  Active=0                    ] 100%
[ tup ] [10.613s] Updated. 
```
### Next steps
Now see [how to flash a custom firmware to artoo](https://github.com/OpenSolo/documentation/blob/master/artoo/flash-custom-firmware.md).

## Troubleshooting
If tup complains about not finding a tupfile double check the folder you are in.  It should be the root directory clone from git.

If you get other random issues try running tup as root.

If you get complaints about images being to large or having to many colours, reclone the repo and try again. Read the customisation instructions *carefully*.
