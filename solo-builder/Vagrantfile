# -*- mode: ruby -*-
# vi: set ft=ruby :



Vagrant.configure(2) do |config|

  config.vm.box = "ubuntu/trusty64"
  config.vm.box_check_update = false
  
  config.vm.provision "shell", path: "install-vagrant-deps.sh"

  # detect number of cores,
  # http://stackoverflow.com/questions/891537/detect-number-of-cpus-installed
  def self.processor_count
    case RbConfig::CONFIG['host_os']
    when /darwin9/
      `hwprefs cpu_count`.to_i
    when /darwin/
      ((`which hwprefs` != '') ? `hwprefs thread_count` : `sysctl -n hw.ncpu`).to_i
    when /linux/
      `cat /proc/cpuinfo | grep processor | wc -l`.to_i
    when /freebsd/
      `sysctl -n hw.ncpu`.to_i
    when /mswin|mingw/
      require 'win32ole'
      wmi = WIN32OLE.connect("winmgmts://")
      cpu = wmi.ExecQuery("select NumberOfCores from Win32_Processor") # TODO count hyper-threaded in this
      cpu.to_enum.first.NumberOfCores
    end
  end

  # fwd host ssh for git access
  config.ssh.forward_agent = true

  config.vm.provider "virtualbox" do |vb|
    # not recommended to use less than 6GB
    vb.memory = "6144"
    vb.cpus = processor_count
  end

  config.vm.provision "guest_ansible" do |ansible|
    ansible.extra_vars = {
      build_dir_owner: "vagrant"
    }
    ansible.playbook = "playbook.yml"
  end
end


