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
sudo pip install --upgrade "pip < 21.0"
sudo pip install --upgrade setuptools
sudo pip install urllib3[secure] bcrypt pynacl cryptography==2.0.3 pillow

#git-with-openssl as gnutls can't do modern https/tls 
cd /home/vagrant
#like https://raw.githubusercontent.com/paul-nelson-baker/git-openssl-shellscript/main/compile-git-with-openssl.sh but simplified and tied to version 2.32.2
set -x
BUILDDIR=${BUILDDIR:-$(mktemp -d)}
mkdir -p "${BUILDDIR}"
cd "${BUILDDIR}"
git_tarball_url="https://api.github.com/repos/git/git/tarball/refs/tags/v2.32.2"
curl -L --retry 5 "${git_tarball_url}" --output "git-source.tar.gz"
tar -xf "git-source.tar.gz" --strip 1
# Don't use gnutls, this is the problem package.
if sudo apt-get remove --purge libcurl4-gnutls-dev -y; then
  # Using apt-get for these commands, they're not supported with the apt alias on 14.04 (but they may be on later systems)
  sudo apt-get autoremove -y
  sudo apt-get autoclean
fi
sudo apt-get install build-essential autoconf dh-autoreconf -y
sudo apt-get install libcurl4-openssl-dev tcl-dev gettext asciidoc libexpat1-dev libz-dev -y
make configure
./configure --prefix=/usr --with-openssl
make 
# If you have an apt managed version of git, remove it
if sudo apt-get remove --purge git -y; then
sudo apt-get autoremove -y
sudo apt-get autoclean
fi
# Install the version we just built
sudo make install #install-doc install-html install-info
echo "Make sure to refresh your shell!"
bash -c 'echo "$(which git) ($(git --version))"'

#chmod 755 ./compile-git-with-openssl.sh
#./compile-git-with-openssl.sh --skip-tests
git config --global http.sslVerify false

cd /home/vagrant

#wgets
sudo wget "http://stedolan.github.io/jq/download/linux64/jq" -O "/usr/local/bin/jq"
sudo chmod 0755 /usr/local/bin/jq

sudo wget "https://storage.googleapis.com/git-repo-downloads/repo" -O "/usr/local/bin/repo"
sudo chmod 0755 /usr/local/bin/repo

ssh-keyscan -t rsa github.com
ssh-keyscan -t rsa bitbucket.org

cp /vagrant/vagrant.gitconfig ~/.gitconfig
sudo chmod +x /vagrant/solo-builder/builder.sh
