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
- 2 * Intel grizzly pass server boards
- CPU: 2 * Intel Xeon CPU E5-2680 v2 @ 2.80GHz
- RAM: Minimum 16GB, recommended 64GB
- 2 * physical networks

Software
========
- CentOS-7-x86_64-Minimal-1503-01
- Kernel version 3.10.0-229.14.1.el7.x86_64

Pre-requisites
==============
- CentOS 7 minimal fresh installation
- A non root user
- VT-d enabled in BIOS
- VT-x enabled in BIOS
- Access to the internet
- NTP is running and synchronised on both nodes
- Topology as detailed below

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
To elevate user privileges, add them to the sudoers file, you will need admin
privileges for this.

| sudo cat /etc/sudoers
| <USER> ALL=(ALL) NOPASSWD: ALL

Check kernel version
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
Devstack will pull down the required packages, but for the initial clone we need
git, socat, kernel-devel and redhat-lsb-core and update all packages for yum.

| sudo yum install -y kernel-devel git socat redhat-lsb-core
| sudo yum update

The system will need to be rebooted for the changes to take effect.
| sudo reboot

Libvirt configuration
---------------------
Libvirt and qemu on CentOS 7 are out of date for networking-ovs-dpdk.
As a result libvirt will be uninstalled and reinstalled from binaries
which are downloaded from repos.fedorapeople.org and cbs.centos.org.
the binaries are downloaded if they are not present or while RECLONE is true.

Devstack configuration
----------------------
Clone the devstack repo.

| cd ~
| git clone https://github.com/openstack-dev/devstack.git

When you have cloned devstack, the next step is to configure your controller
and compute nodes.

Here are some local.conf examples based on the topology described above.

Controller node config example

.. include:: _downloads/local.conf.controller_node
   :literal:

Compute node config example

.. include:: _downloads/local.conf.compute_node
   :literal:

Add the local.conf file to /home/<USER>/devstack directory and stack.

| cd ~/devstack
| ./stack.sh

Boot a VM with OVS-DPDK
-----------------------
OVS-DPDK uses hugepages to communicate with guests, before you boot a VM with
OVS-DPDK you will need to create a flavor that requests hugepages.

| cd /home/<USER>/devstack
| source openrc admin demo
| nova flavor-key <FLAVOR> set hw:mem_page_size=large

Enable the OVS firewall
-----------------------
To enable the OVS firewall, you will need to modify (or add) the following
variable to local.conf:

| [[post-config|/etc/neutron/plugins/ml2/ml2_conf.ini]]
| [securitygroup]
| firewall_driver = networking_ovs_dpdk.agent.ovs_dpdk_firewall.OVSFirewallDriver

By default, the multicast support is enabled. The default aging time for the
IGMP subscriptions in the bridges is 3600 seconds. To configure the multicast
support both variables could be setup in local.conf:

| [[local|localrc]]
| OVS_ENABLE_SG_FIREWALL_MULTICAST=[True/False]
| OVS_MULTICAST_SNOOPING_AGING_TIME=[15..3600]

Enable overlay networks
-----------------------
To enable overlay networking (vxlan/gre) with the dpdk netdev datapath
the tunnel enpoint ip must be assigned to a phyical bridge(a bridge with
a dpdk phyical port). This can be done by setting the OVS_TUNNEL_CIDR_MAPPING
variable in the local.conf. e.g. OVS_TUNNEL_CIDR_MAPPING=br-phy:192.168.50.1/24
assigns the ip of 192.168.50.1 with subnetmask 255.255.255.0 to the br-phy local port.

Known Issues
------------
OVS_PMD_CORE_MASK default value '4' doesn't work for NIC's from numa nodes other
than 0. It's value is used for other_config:pmd-cpu-mask parameter in ovsdb and we
are subsequently using it for vcpu_pin_set in nova.conf. Unfortunatelly if DPDK
NIC's from numa nodes other than 0 are used, there is no PMD thread generated for
them. If you are using host with multiple numa nodes please consider using not
default OVS_PMD_CORE_MASK value.
