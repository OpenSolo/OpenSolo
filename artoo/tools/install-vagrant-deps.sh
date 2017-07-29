
apt-add-repository 'deb http://ppa.launchpad.net/anatol/tup/ubuntu precise main' -y
add-apt-repository 'ppa:terry.guo/gcc-arm-embedded' -y

apt-get -qq --assume-yes update
apt-get -qq --assume-yes install tup freetype* python-pip python-dev gcc-arm-none-eabi git

sudo pip install --upgrade pip
sudo pip install pillow
