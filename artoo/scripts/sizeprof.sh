#!/bin/sh

ELF=artoo.elf

echo
echo Top Flash consumers:
arm-none-eabi-readelf -W -s $ELF | grep -v NOTYPE | grep ": 080" | sort -n -k 3 -r | head -n 30 | arm-none-eabi-c++filt -n

echo
echo Top RAM consumers:
arm-none-eabi-readelf -W -s $ELF | grep -v NOTYPE | grep ": 2000" | sort -n -k 3 -r | head -n 20 | arm-none-eabi-c++filt -n

echo
echo Program segment summary:
arm-none-eabi-readelf -l $ELF | grep LOAD
