#!/bin/bash

RWFS=/mnt/rootfs.rw
LIBDIR=/usr/lib

if [ -e $RWFS/$LIBDIR/sndast* ] ||
   [ -e $RWFS/$LIBDIR/libvpu* ] ||
   [ -e $RWFS/$LIBDIR/libfsl* ] ||
   [ -e $RWFS/$LIBDIR/gstrea* ] ; then

  #Remove all the sculpture libraries
  rm -rf $RWFS/$LIBDIR/sndast
  rm -rf $RWFS/$LIBDIR/libvpu*
  rm -rf $RWFS/$LIBDIR/libfslvpu*
  rm -rf $RWFS/$LIBDIR/gstreamer*
  rm -rf $RWFS/$LIBDIR/.*libfslvpu*

  #Remove the gstreamer registry
  rm -f ~/.gstreamer-0.10/registry.arm.bin

  #Rebuild the gstreamer library
  gst-inspect > /dev/null 2>&1

fi
