===========================================
Getting started with Openstack and OVS-DPDK
===========================================

This getting started guide describes the setup of Openstack with OVS-DPDK
in a dual node configuration.

Some command line examples are provided to match the described topology,
tailor these to suit your environment.

Requirements
------------
This getting started is executed with the following hardware and software.

Hardware
========
- 2 * Intel grizzly pass server board
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
- NTP is running and synchronised on both nodes
- Topology as detailed below

- Puppet installed together with openstack modules

  E.g.:

| puppet module list

| /etc/puppet/modules
| ├── dprince-qpid (v1.0.3)
| ├── duritong-sysctl (v0.0.11)
| ├── nanliu-staging (v1.0.3)
| ├── openstack-cinder (v7.0.0)
| ├── openstack-glance (v7.0.0)
| ├── openstack-horizon (v7.0.0)
| ├── openstack-keystone (v7.0.0)
| ├── openstack-neutron (v7.0.0)
| ├── openstack-nova (v7.0.0)
| ├── openstack-openstack_extras (v7.0.0)
| ├── openstack-openstacklib (v7.0.0)
| ├── openstack-vswitch (v3.0.0)
| ├── ovsdpdk (???)
| ├── puppetlabs-apache (v1.8.1)
| ├── puppetlabs-apt (v1.8.0)
| ├── puppetlabs-concat (v1.2.5)
| ├── puppetlabs-corosync (v0.7.0)
| ├── puppetlabs-firewall (v1.8.0)
| ├── puppetlabs-inifile (v1.4.3)
| ├── puppetlabs-mysql (v3.6.2)
| ├── puppetlabs-postgresql (v3.4.2)
| ├── puppetlabs-rabbitmq (v5.3.1)
| ├── puppetlabs-stdlib (v4.11.0)
| ├── puppetlabs-vcsrepo (v1.3.2)
| └── saz-memcached (v2.8.1)


Topology
========
::

       Controller                           Compute
    +---------------+                   +---------------+
    |               |-+  API network  +-|   +----+      |
    |               | |---------------| |   | VM |      |
    |               |-+               +-|   +----+      |
    |               |                   |     |         |
    | +----------+  |                   | +-----------+ |
    | | OVS DPDK |  |                   | | OVS DPDK  | |
    | +----------+  |                   | +-----------+ |
    +-----+---+-----+                   +-----+---+-----+
          +---+                               +---+
            |                                   |
            +-----------------------------------+
                        Data network



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


Install required packages
-------------------------
Puppet will pull down the required packages all you should need before deployment is puppet to
be present on the system together will all of it's required modules plus all of the configuration
stuff mentioned earlier (if needed).


Puppet ovsdpdk configuration
----------------------------

ovsdpdk preparation
===================
Copy ovsdpdk puppet module into puppet module directory:

E.g.
| sudo cp -R ./puppet/ovsdpdk /etc/puppet/modules

customizing ovsdpdk
===================
Before installation is triggered you should get familiar with all configuration variables,
Parameters for DPDK build are described in ./ovsdpdk/manifests/init.pp
Environment variables are in ./ovsdpdk/manifests/param.pp and are not supposed to be changed frequently

There are several examples stored in ./ovsdpdk/examples relevant for complete openstack deployment
of controller, compute & allinone scenarios.

Hint:
It's recommended to configure hugepages already during booting to prevent fragmentation by
configuring kernel boot params:

e.g.
| hugepagesz=2M hugepages=2048

which created 4G during booting and not needed anymore to be handled during ovs-dpdk startup
| ovs_allocate_hugepages => 'False'

one or more nic's should be specified, which should be visible and added to dpdk during deployment:
| ovs_bridge_mappings => 'default:br-eth2'

Result looks as follows:

  class { '::ovsdpdk':
    ovs_bridge_mappings    => 'default:br-eth2',
    ovs_allocate_hugepages => 'False',
    ovs_socket_mem         => '3096',   # keeping 1G for VM's
    compute                => 'True'
  }


deploy ovsdpdk
==============
When node declaration is finished, you can launch deployment with some more verbosity
(as a root or user from sudoers file, which has full visibility of all required puppet modules)

| root@compute:/etc/puppet/modules/ovsdpdk/examples# puppet apply compute.pp  -d -v
| root@compute:/etc/puppet/modules/ovsdpdk/examples# puppet apply controller.pp  -d -v


Boot a VM with OVS-DPDK
-----------------------
OVS-DPDK uses hugepages to communicate with guests, before you boot a VM with
OVS-DPDK you will need to create a flavor that requests hugepages.

E.g.
| cd /etc/puppet/modules/ovsdpdk/examples
| source openrc
| nova flavor-key <FLAVOR> set hw:mem_page_size=large


Known Issues
------------
To work around bug LP 1513367, set security_driver="none" in /etc/libvirt/qemu.conf
then restart service libvirt-bin, or remove AppArmor or placed all Libvirt AppArmor
profiles into complain mode, otherwise you can't spawn vms successfully and will get
the error "Permission denied".

OVS_PMD_CORE_MASK default value '4' doesn't work for NIC's from numa nodes other
than 0. It's value is used for other_config:pmd-cpu-mask parameter in ovsdb and we
are subsequently using it for vcpu_pin_set in nova.conf. Unfortunatelly if DPDK
NIC's from numa nodes other than 0 are used, there is no PMD thread generated for
them. If you are using host with multiple numa nodes please consider using not
default OVS_PMD_CORE_MASK value.
