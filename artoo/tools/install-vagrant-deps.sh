sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6AF0E1940624A220
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6D1D8367A3421AFB
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 5BB92C09DB82666C

# included python 2.7.12 is broken. Install latest Python 2.7
sudo add-apt-repository -y ppa:jonathonf/python-2.7
sudo apt-get -y --force-yes update
sudo apt-get install -y --force-yes python2.7 python2.7

# install PIP. FYI the obvious apt-get install python-pip doesn't work. So this does.
sudo curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
sudo python get-pip.py
sudo pip install --upgrade pip

# install pillow dependencies, then install pillow
sudo apt-get install -y --force-yes freetype* python-dev libtiff4-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.5-dev tk8.5-dev python-tk git freetype* python-dev git
sudo pip install pillow

# install GCC Arm
sudo add-apt-repository 'ppa:team-gcc-arm-embedded/ppa' -y
sudo apt-get -y --force-yes update
sudo apt-get install -y --force-yes gcc-arm-embedded

# install TUP
sudo apt-add-repository 'deb http://ppa.launchpad.net/anatol/tup/ubuntu precise main' -y
sudo apt-get -y --force-yes update
sudo apt-get install -y --force-yes tup

echo ""
echo To build the artoo stm32 binary enter the VM with:
echo vagrant ssh
echo Then type this:
echo cd /vagrant
echo tup

