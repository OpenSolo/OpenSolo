WARNING - WORK IN PROGRESS

```
This code is known to be broken and/or incomplete. IT DOES NOT WORK. 

We are actively working on fixing it, and we really, really do not recommend you download it just yet.

We will remove this warning from the repository when it is no longer required.
```


# solo-builder

## using vagrant

Works in [vagrant](http://vagrantup.com), typically useful for local builds.
First install this plugin:
```
$ vagrant plugin install vagrant-guest_ansible
$ vagrant up
```

(If `vagrant up` fails, run `vagrant provision` to try provisioning your VM
again.)

To fire off the builder:

```
$ vagrant ssh -c /vagrant/builder.sh
```


## using docker

DOCKER IS UNTESTED OUTSIDE 3DR , USE VAGRANT FOR NOW.
 
Works in Docker and boot2docker. 
Copy `id_rsa` and `solo-builder.pem` to this directory (sorry). Then run

```
docker build -t 3drobotics/solo-builder .
```

Then run

```
docker run -i 3drobotics/solo-builder su -l ubuntu /solo-build/builder.sh
```

TODO: write a script that gets the files off after

## using something else

`playbook.yml` is an ansible file for an Ubuntu 14.04 distro. `builder.sh` is the build script for a user named `ubuntu`. Make it happen!

## repos

3dr Private:

* https://github.com/3drobotics/mavlink-solo
* https://github.com/3drobotics/sculpture_proprietary
* https://github.com/3drobotics/solo-gimbal
* https://github.com/3drobotics/artoo
* https://github.com/3drobotics/SoloLink

Public:

* https://github.com/3drobotics/imx6-uboot
* https://github.com/3drobotics/imx6-linux
* https://github.com/3drobotics/MAVProxy
* https://github.com/3drobotics/stm32loader
* https://github.com/3drobotics/ardupilot-solo

* https://github.com/OpenSolo/ardupilot-solo
* https://github.com/OpenSolo/sololink
* https://github.com/OpenSolo/artoo
* https://github.com/OpenSolo/imx6-uboot
* https://github.com/OpenSolo/imx6-linux
* https://github.com/OpenSolo/3dr-arm-yocto-bsp
* https://github.com/OpenSolo/meta-3dr
* https://github.com/OpenSolo/dronekit-python-solo
* https://github.com/OpenSolo/sololink-python
* https://github.com/OpenSolo/solo-builder
* https://github.com/OpenSolo/3dr-yocto-bsb-base
* https://github.com/OpenSolo/stm32loader
* https://github.com/OpenSolo/MAVProxy


