#!/bin/bash
# alternative to the 'sync' tool, which puts stuff in /solo-build, for now we'll use /solo-build-alt
# 
# 'master', 'tags/2.9.94' ( for a tag) or '2.9.94' ( for a branch ) is ok:
name=$1
echo "git reference: $name"
#  
sudo mkdir /solo-build-alt
sudo chown vagrant /solo-build-alt
cd /solo-build-alt

echo "----------------------------------------------------------------------------"
mkdir -p sources/poky
git clone git://git.yoctoproject.org/poky sources/poky 2>&1 |  grep -v 'fatal'
cd sources/poky
git fetch
git checkout bee7e3756adf70edaeabe9d43166707aab84f581
cd ../..

echo "----------------------------------------------------------------------------"
mkdir -p sources/meta-fsl-arm
git clone git://git.yoctoproject.org/meta-fsl-arm sources/meta-fsl-arm 2>&1 |  grep -v 'fatal'
cd sources/meta-fsl-arm
git fetch
git checkout af392c22bf6b563525ede4a81b6755ff1dd2c1c6
cd ../..

echo "----------------------------------------------------------------------------"
mkdir -p sources/meta-openembedded
git clone git://git.openembedded.org/meta-openembedded sources/meta-openembedded 2>&1 |  grep -v 'fatal'
cd sources/meta-openembedded
git fetch
git checkout eb4563b83be0a57ede4269ab19688af6baa62cd2
cd ../..

echo "----------------------------------------------------------------------------"
mkdir -p sources/base
git clone git://github.com/OpenSolo/3dr-yocto-bsp-base sources/base 2>&1 |  grep -v 'fatal'
cd sources/base
git fetch
echo git checkout $name
git checkout $name
cd ../..
cp sources/base/README.md .
cp sources/base/setup-environment .

echo "----------------------------------------------------------------------------"
mkdir -p sources/meta-3dr
git clone git://github.com/OpenSolo/meta-3dr sources/meta-3dr 2>&1 |  grep -v 'fatal'
cd sources/meta-3dr
git fetch
echo git checkout $name
git checkout $name
cd ../..

echo "----------------------------------------------------------------------------"
mkdir -p sources/meta-fsl-arm-extra
git clone git://github.com/Freescale/meta-fsl-arm-extra sources/meta-fsl-arm-extra 2>&1 |  grep -v 'fatal'
cd sources/meta-fsl-arm-extra
git fetch
git checkout 07ad83db0fb67c5023bd627a61efb7f474c52622
cd ../..

echo "----------------------------------------------------------------------------"
mkdir -p sources/meta-fsl-demos
git clone git://github.com/Freescale/meta-fsl-demos sources/meta-fsl-demos 2>&1 |  grep -v 'fatal'
cd sources/meta-fsl-demos
git fetch
git checkout 5a12677ad000a926d23c444266722a778ea228a7
cd ../..

echo "----------------------------------------------------------------------------"
mkdir -p sources/meta-browser
git clone git://github.com/OSSystems/meta-browser sources/meta-browser 2>&1 |  grep -v 'fatal'
cd sources/meta-browser
git fetch
git checkout fc3969f63bda343c38c40a23f746c560c4735f3e
cd ../..

echo "----------------------------------------------------------------------------"
mkdir -p sources/meta-fsl-bsp-release
git clone git://git.freescale.com/imx/meta-fsl-bsp-release sources/meta-fsl-bsp-release 2>&1 |  grep -v 'fatal'
cd sources/meta-fsl-bsp-release
git fetch
git checkout dora_3.10.17-1.0.0_GA
cd ../..
cp sources/meta-fsl-bsp-release/imx/tools/fsl-setup-release.sh .
