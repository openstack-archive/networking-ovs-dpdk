..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

      Convention for heading levels in networking-ovs-dpdk documentation:

      =======  Heading 0 (reserved for the title in a document)
      -------  Heading 1
      ~~~~~~~  Heading 2
      +++++++  Heading 3
      '''''''  Heading 4

      Avoid deeper levels because they do not render well.

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
- CentOS 7.2 server
- Kernel version 3.10.0-327.13.1.el7.x86_64

Pre-requisites
==============
- CentOS 7.2 server minimal fresh installation
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
├── duritong-sysctl (v0.0.11)
├── nanliu-staging (v1.0.3)
├── openstack-cinder (v8.0.1)
├── openstack-glance (v8.0.1)
├── openstack-horizon (v8.0.1)
├── openstack-keystone (v8.0.1)
├── openstack-neutron (v8.0.1)
├── openstack-nova (v8.0.1)
├── openstack-openstack_extras (v7.0.0)
├── openstack-openstacklib (v8.0.1)
├── openstack-vswitch (v4.0.0)
├── ovsdpdk (???)
├── puppetlabs-apache (v1.9.0)
├── puppetlabs-apt (v2.2.2)
├── puppetlabs-concat (v1.2.5)
├── puppetlabs-corosync (v0.7.0)
├── puppetlabs-firewall (v1.8.0)
├── puppetlabs-inifile (v1.5.0)
├── puppetlabs-mysql (v3.7.0)
├── puppetlabs-postgresql (v4.7.1)
├── puppetlabs-rabbitmq (v5.3.1)
├── puppetlabs-stdlib (v4.12.0)
├── puppetlabs-vcsrepo (v1.3.2)
└── saz-memcached (v2.8.1)

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

Versioning
================
For proper verification over this centos kernel, following versions were used:

| OVS 'f3ea2ad27fd076735fdb78286980749bb12fe1ce'
| DPDK v2.2.0
| QEMU 2.3.0-31
| libvirt 1.2.17-13

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
    ovs_socket_mem         => 'auto',   # will get 512 per numa node + keeping 3G for VM's
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

1) OVS_PMD_CORE_MASK default value is '4', which means core 3 and it's hyperthread
sibling will be used by default. This default value doesn't work for NIC's from
numa nodes other than 0.
It's value is used for other_config:pmd-cpu-mask parameter in ovsdb and we
are subsequently using it for vcpu_pin_set in nova.conf. Unfortunatelly if DPDK
NIC's from numa nodes other than 0 are used, there is no PMD thread generated for
them. If you are using a host with multiple numa nodes, cores from each numa node
should be added to the OVS_PMD_CORE_MASK.
On a system with Hyper-Threading it is recommended to also allocate the hyper thread
sibling of any core assigned to the dpdk pmds.

2) Some of the puppet scripting requires to be executed inside terminal, following
row in /etc/sudoers file should be commented-out
#Defaults    requiretty

3) SELinux should be set to "Permissive" mode to avoid unwanted behaviour from puppet
openstack deployments in general

4) For downloading proper/newer QEMU, add centos-virt-sig.repo into /etc/yum.repos.d/
with following content:

| [virt7-kvm-common-release]
| name=virt7-kvm-common-release
| baseurl=http://cbs.centos.org/repos/virt7-kvm-common-release/x86_64/os
| enabled=1
| gpgcheck=0


5) To avoid following problem:
Error: Could not find resource 'File[/etc/openstack-dashboard/local_settings.py]'
Described in https://bugs.launchpad.net/puppet-horizon/+bug/1548529
concat puppet module 1.x should be used
