#!/bin/bash

#  Create the build directory and make sure we own it.
build_dir=/solo-build
source_dir=$build_dir/sources
sudo mkdir -p $source_dir
sudo chown -R $USER $build_dir
cd $build_dir

echo "----------------------------------------------------------------------------"
mkdir -p $source_dir/poky
git clone git://git.yoctoproject.org/poky $source_dir/poky 2>&1 |  grep -v 'fatal'
cd $source_dir/poky
git fetch
git checkout bee7e3756adf70edaeabe9d43166707aab84f581

## This BB file has a bad source URI, but it isn't our file to fix.
cp -f /vagrant/solo-builder/gtk-doc-stub_git.bb $source_dir/poky/meta/recipes-gnome/gtk-doc-stub/gtk-doc-stub_git.bb

echo "----------------------------------------------------------------------------"
mkdir -p $source_dir/meta-fsl-arm
git clone git://git.yoctoproject.org/meta-fsl-arm $source_dir/meta-fsl-arm 2>&1 |  grep -v 'fatal'
cd $source_dir/meta-fsl-arm
git fetch
git checkout af392c22bf6b563525ede4a81b6755ff1dd2c1c6

echo "----------------------------------------------------------------------------"
mkdir -p $source_dir/meta-openembedded
git clone git://git.openembedded.org/meta-openembedded $source_dir/meta-openembedded 2>&1 |  grep -v 'fatal'
cd $source_dir/meta-openembedded
git fetch
git checkout eb4563b83be0a57ede4269ab19688af6baa62cd2

echo "----------------------------------------------------------------------------"
mkdir -p $source_dir/base
rsync -r /vagrant/solo-builder/3dr-yocto-bsp-base/ $source_dir/base --delete
cp $source_dir/base/README.md $build_dir
cp $source_dir/base/setup-environment $build_dir

echo "----------------------------------------------------------------------------"
mkdir -p $source_dir/meta-3dr
rsync -r /vagrant/meta-3dr/ $source_dir/meta-3dr --delete

echo "----------------------------------------------------------------------------"
mkdir -p $source_dir/meta-fsl-arm-extra
git clone git://github.com/Freescale/meta-fsl-arm-extra $source_dir/meta-fsl-arm-extra 2>&1 |  grep -v 'fatal'
cd $source_dir/meta-fsl-arm-extra
git fetch
git checkout 07ad83db0fb67c5023bd627a61efb7f474c52622

echo "----------------------------------------------------------------------------"
mkdir -p $source_dir/meta-fsl-demos
git clone git://github.com/Freescale/meta-fsl-demos $source_dir/meta-fsl-demos 2>&1 |  grep -v 'fatal'
cd $source_dir/meta-fsl-demos
git fetch
git checkout 5a12677ad000a926d23c444266722a778ea228a7

echo "----------------------------------------------------------------------------"
mkdir -p $source_dir/meta-browser
git clone git://github.com/OSSystems/meta-browser $source_dir/meta-browser 2>&1 |  grep -v 'fatal'
cd $source_dir/meta-browser
git fetch
git checkout fc3969f63bda343c38c40a23f746c560c4735f3e

echo "----------------------------------------------------------------------------"
mkdir -p $source_dir/meta-fsl-bsp-release
git clone git://git.freescale.com/imx/meta-fsl-bsp-release $source_dir/meta-fsl-bsp-release 2>&1 |  grep -v 'fatal'
cd $source_dir/meta-fsl-bsp-release
git fetch
git checkout dora_3.10.17-1.0.0_GA
cd $build_dir
cp $source_dir/meta-fsl-bsp-release/imx/tools/fsl-setup-release.sh $build_dir
