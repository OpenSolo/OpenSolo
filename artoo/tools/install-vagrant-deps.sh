sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6AF0E1940624A220
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6D1D8367A3421AFB

apt-add-repository 'deb http://ppa.launchpad.net/anatol/tup/ubuntu precise main' -y
add-apt-repository 'ppa:terry.guo/gcc-arm-embedded' -y

apt-get -qq --assume-yes update
apt-get -qq --assume-yes install tup freetype* python-pip python-dev gcc-arm-none-eabi git

sudo pip install --upgrade pip
sudo pip install pillow
