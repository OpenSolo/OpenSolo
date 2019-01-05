#!/bin/sh

ELF=artoo.elf

arm-none-eabi-objdump -d $ELF | arm-none-eabi-c++filt -n | less
