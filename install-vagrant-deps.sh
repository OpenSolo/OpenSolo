sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6AF0E1940624A220
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 6D1D8367A3421AFB
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 5BB92C09DB82666C
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys E601AAF9486D3664

#apt packages
sudo apt-add-repository 'deb http://ppa.launchpad.net/anatol/tup/ubuntu precise main' -y
sudo add-apt-repository 'ppa:terry.guo/gcc-arm-embedded' -y
sudo add-apt-repository 'ppa:fkrull/deadsnakes-python2.7' -y
sudo apt-get --assume-yes update
sudo apt-get install -y --assume-yes python2.7 python2.7-dev 
sudo apt-get install -y --assume-yes git python-pip freetype* python-setuptools libtiff5-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.5-dev tk8.5-dev python-tk libffi* ansible libssl-dev gcc-arm-none-eabi gcc-multilib build-essential chrpath socat libsdl1.2-dev xterm texinfo tup gawk wget git-core diffstat unzip curl

# pip packages
sudo pip install --upgrade pip
sudo pip install --upgrade setuptools
sudo pip install urllib3[secure] bcrypt pynacl cryptography==2.0.3 pillow

#wgets
sudo wget "http://stedolan.github.io/jq/download/linux64/jq" -O "/usr/local/bin/jq"
sudo chmod 0755 /usr/local/bin/jq

sudo wget "https://storage.googleapis.com/git-repo-downloads/repo" -O "/usr/local/bin/repo"
sudo chmod 0755 /usr/local/bin/repo

ssh-keyscan -t rsa github.com
ssh-keyscan -t rsa bitbucket.org

cp /vagrant/vagrant.gitconfig ~/.gitconfig
sudo chmod +x /vagrant/solo-builder/builder.sh
