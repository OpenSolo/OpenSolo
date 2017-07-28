WARNING - WORK IN PROGRESS

```
This code is known to be broken and/or incomplete. IT DOES NOT WORK. 

We are actively working on fixing it, and we really, really do not recommend you download it just yet.

We will remove this warning from the repository when it is no longer required.
```


3DR Yocto BSP
===============================

This BSP supports the following
processors:

 * i.MX6

   * 3DR i.MX6Solo HDTC product family

Quick Start Guide
-----------------

Once you have downloaded the source of all projects, you will have to
call:

$: MACHINE=imx6solo-3dr-1080p EULA=1 DISTRO=3dr source ./setup-environment build

After this step, you will be with everything need for build an image.

Contributing
------------

To contribute to the development of this BSP and/or submit patches for
new boards please send the patches against the respective project as
informated bellow:

The following layers are included on this release:

 * poky: base build system and metadata
   Path: sources/poky
   GIT: git://git.yoctoproject.org/poky
   Mailing list: https://lists.yoctoproject.org/listinfo/yocto

 * meta-openembedded: extra packages and features
   Path: sources/meta-openembedded
   GIT: git://git.openembedded.org/meta-openembedded
   Mailing list: http://lists.linuxtogo.org/cgi-bin/mailman/listinfo/openembedded-devel
   Note: Use [meta-oe] in subject to easy the processing

 * meta-fsl-arm: support for Freescale's processors and board
   Path: sources/meta-fsl-arm
   Project: https://github.com/Freescale/meta-fsl-arm
   GIT: git://github.com/Freescale/meta-fsl-arm.git
   Mailing list: https://lists.yoctoproject.org/listinfo/meta-freescale

 * meta-fsl-arm-extra: support for boards using Freescale's processors
   Path: sources/meta-fsl-arm-extra
   Project: https://github.com/Freescale/meta-fsl-arm-extra
   GIT: git://github.com/Freescale/meta-fsl-extra.git
   Mailing list: https://lists.yoctoproject.org/listinfo/meta-freescale
   Note: Use [meta-fsl-arm-extra] in subject to easy the processing

 * meta-fsl-demos: demo images and recipes
   Path: sources/meta-fsl-demos
   Project: https://github.com/Freescale/meta-fsl-demos
   GIT: git://github.com/Freescale/meta-fsl-demos.git
   Mailing list: https://lists.yoctoproject.org/listinfo/meta-freescale
   Note: Use [meta-fsl-demos] in subject to easy the processing

 * meta-3dr: 3DR kernel and support recipes
   Path: sources/meta-3dr
   Project: https://github.com/3drobotics/meta-3dr
   GIT: git@github.com:3drobotics/meta-3dr.git
