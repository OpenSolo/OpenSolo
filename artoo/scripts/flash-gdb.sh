#!/bin/sh

# flash the specified binary via gdb
#   usage: ./scripts/gdb-flash.sh (<mybinary>.elf)

ELF=artoo.elf

if [ "$#" -eq  "1" ]
  then
ELF=$1
fi

arm-none-eabi-gdb ${ELF} -q -ex load -ex quit
