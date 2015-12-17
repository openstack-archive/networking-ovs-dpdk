===========================================
Getting started with Openstack and OVS-DPDK
===========================================

This getting started guide describes the setup of Openstack with OVS-DPDK
in all-in-node configuration based on puppet modules.

Some command line examples are provided to match the described topology,
tailor these to suit your environment.

Requirements
------------
This getting started is executed with the following hardware and software.

Hardware
========
- 1 * Intel grizzly pass server board
- CPU: 2 * Intel Xeon CPU E5-2699 v3 @ 2.30GHz
- RAM: 32G (Minimum 16GB, recommended 64GB)
- 2 * physical networks

Software
========
- Ubuntu 14.04 LTS server
- Kernel version 3.13.0-24-generic

Pre-requisites
==============
- Ubuntu 14.04 server minimal fresh installation
- Root access is required as of now (e.g. non root user from sudoers)
- VT-d enabled in BIOS
- VT-x enabled in BIOS
- Access to the internet

All-in-One Topology
===================

                 -----------
                 - Horizon -
                 -----------
                  [apache2]

                 ------------
                 - Nova-API -
                 ------------
                [nova-compute]
                     ...
                     ...
      --------------------------------------
      - Keystone | DB | Rabbit-MQ | Cinder -
      --------------------------------------
                 -----------
                 - Neutron -
                 -----------
              [neutron-server]

         [neutron-openvswitch-agent]
          [neutron-metering-agent]
          [neutron-metadata-agent]
            [neutron-dhcp-agent]
             [neutron-l3-agent]



Linux configuration
-------------------

Add user to sudoers file 
========================
To elevate user privileges, add them to the suoders file, you will need admin
privileges for this.

| sudo cat /etc/sudoers
| <USER> ALL=(ALL) NOPASSWD: ALL

Downgrade kernel
================
DPDK 2.1 has issues with kernel versions later than 3.19 due to changes in
kernel synchronization mechanisms.

Internal proxy config
=====================
If you are working behind a proxy, you will need to complete the following steps
to provide git and yum with access to the outside world.

Configure yum proxy:

| cat /etc/yum.conf
| proxy=http://<PROXY>:<PROXY PORT NUMBER>

Here is a sample script to provide git access through a proxy.

| sudo cat ~/git-proxy-wrapper

| #!/bin/sh
| _proxy=<PROXY>
| _proxyport=<PROXY PORT NUMBER>
| exec socat STDIO SOCKS4:$_proxy:$1:$2,socksport=$_proxyport

| sudo chown <USER>:<USER> /home/<USER>/git-proxy-wrapper
| sudo chmod +x /home/<USER>/git-proxy-wrapper

Add proxy variables and export to shell:

| cat ~/.bashrc

| export GIT_PROXY_COMMAND=~/git-proxy-wrapper
| export http_proxy=http://<PROXY>:<PROXY PORT NUMBER>
| export HTTP_PROXY=http://<PROXY>:<PROXY PORT NUMBER>
| export https_proxy=https://<PROXY>:<PROXY PORT NUMBER>
| export HTTPS_PROXY=https://<PROXY>:<PROXY PORT NUMBER>
| export NO_PROXY=localhost,127.0.0.1,127.0.1.1,<IP OF CONTROLLER NODE>,<IP OF COMPUTE NODE>
| export no_proxy=localhost,127.0.0.1,127.0.1.1,<IP OF CONTROLLER NODE>,<IP OF COMPUTE NODE>

Export these variables

| source ~/.bashrc


Installation instructions
-------------------------

Fresh OS installation
=====================
Let's start with fresh OS install, please ensure that you have supported version of Ubuntu.
Explicitly ensure that you have correct version of kernel due to DPDK restrictions mentioned above
together with all of the stuff from "Linux configuration" chapter above.

Openstack deployment
====================
It's expected that you will run openstack environment based on puppet modules.
You can use easy way how to deploy openstack in all-in-one setup like puppet-openstack-integration project.

Instructions how to deploy Openstack via puppet-openstack-integration are covered there:
https://wiki.openstack.org/wiki/Puppet/Deploy
This project is newly available on launchpad for bug reporting
https://bugs.launchpad.net/puppet-openstack-integration
Liberty version of deployment scripts is in remotes/origin/stable/liberty branch

After ./all-in-one.sh run finished successfully you can cross-check that all services are running.
Please check explicitly nova services:

| source ~/openrc
| nova service list

and neutron agents:

| source ~/openrc
| neutron agent-list

When all is up and openstack environment is in good shape, we can proceed with ovsdpdk deployment.


OVSDPDK puppet module deployment
================================

We are keeping original ovs db configuration, all existing bridges are just remapped to new datapath from userspace.
We are patching qemu-kvm wrapper with additional capabilities, which might be harmfull to running VM's. 
Please clean or stop all VM's first. They will not have access to new ovs running with hugepages anyway.

ovsdpdk preparation
===================
Copy ovsdpdk puppet module into puppet module directory:

| sudo cp -R ./puppet/ovsdpdk /etc/puppet/modules

customizing ovsdpdk
===================
Before installation is triggered you should get familiar with all configuration variables,
Parameters for DPDK build are described in ./ovsdpdk/manifests/init.pp
Environment variables are in ./ovsdpdk/manifests/param.pp and are not supposed to be changed frequently

One of installation examples with minimal config changes is in ./ovsdpdk/examples/install_small.pp
Instructions how to use it are in this file, but you will most likely need to customize it differently.

You're supposed to declare ovsdpdk class with your settings similarly to example file.

Example:
It's recommended to configure hugepages during booting as kernel argument by adding:

| hugepagesz=2M hugepages=2048

which created 4G during booting and not needed anymore to be handled during ovs-dpdk startup
| ovs_allocate_hugepages => 'False'
just enough for this showcase and modified example file also with adding one nic to dpdk
| ovs_bridge_mappings => 'default:br-eth2'

Result looks as follows:

node /ovsdpdk-install/ {

  class { '::ovsdpdk':
    ovs_bridge_mappings => 'default:br-eth2',
    ovs_allocate_hugepages => 'False',
    ovs_socket_mem => '4096',
  }

}

deploy ovsdpdk
==============
When node declaration is finished, you can launch deployment with some more verbosity

| sudo puppet apply install_small.pp --certname ovsdpdk-install -d -v

#TODO(MichalPtacek) I would like to remove sudo from here later on, commands inside manifest files which are
considered to be executed with root permissions are properly configured but now it's not working w/o it.

Boot a VM with OVS-DPDK
-----------------------
OVS-DPDK uses hugepages to communicate with guests, all flavors are changed accordingly
during deployment: 

e.g.
nova flavor-key <FLAVOR> set hw:mem_page_size=large

Known Issue
-----------
To work around bug LP 1513367, set security_driver="none" in /etc/libvirt/qemu.conf
then restart service libvirt-bin, or remove AppArmor or placed all Libvirt AppArmor
profiles into complain mode, otherwise you can't spawn vms successfully and will get
the error "Permission denied".
