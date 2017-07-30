sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6AF0E1940624A220
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6D1D8367A3421AFB
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 5BB92C09DB82666C

# fix broken  urllib3 or some ssl stuff diesn't work
sudo apt-get install -y --force-yes python-pip
sudo pip install urllib3[secure]

# fix broken python2.7.x by moving it forward to something newer than 2.7.8:
sudo add-apt-repository -y ppa:fkrull/deadsnakes-python2.7
sudo apt-get -y --force-yes update
sudo apt-get install -y --force-yes python2.7 python2.7-dev 

## get deps for pillow, and note that we get Pillow from easy_install instead of 'pip' or apt-get becuase this method actually works.
#sudo apt-get install -y python-dev python-setuptools
sudo apt-get install -y --force-yes libtiff4-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.5-dev tk8.5-dev python-tk
sudo  easy_install Pillow

sudo apt-add-repository 'deb http://ppa.launchpad.net/anatol/tup/ubuntu precise main' -y
sudo add-apt-repository 'ppa:terry.guo/gcc-arm-embedded' -y

sudo apt-get --assume-yes update
sudo apt-get --assume-yes install tup freetype* python-pip python-dev gcc-arm-none-eabi git

sudo pip install --upgrade pip
sudo pip install pillow

echo ""
echo To build the artoo stm32 binary enter the VM with:
echo vagrant ssh
echo Then type this:
echo cd /vagrant
echo tup

