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
- Fedora 21 server
- Kernel version 3.19.7-200.fc21.x86_64

Pre-requisites
==============
- Fedora 21 server fresh installation
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

Relax SELINUX control
=====================
| sudo cat /etc/selinux/config
| SELINUX=permissive

Check kernel version
====================
DPDK currently supports kernel versions up to 3.19. This guide details
downgrading the kernel to version version 3.19.7-200.fc21.x86_64.

Download and install required kernel packages

| sudo yum install -y https://kojipkgs.fedoraproject.org//packages/kernel/3.19.7/200.fc21/x86_64/kernel-core-3.19.7-200.fc21.x86_64.rpm
| sudo yum install -y https://kojipkgs.fedoraproject.org//packages/kernel/3.19.7/200.fc21/x86_64/kernel-modules-3.19.7-200.fc21.x86_64.rpm
| sudo yum install -y https://kojipkgs.fedoraproject.org//packages/kernel/3.19.7/200.fc21/x86_64/kernel-3.19.7-200.fc21.x86_64.rpm
| sudo yum install -y https://kojipkgs.fedoraproject.org//packages/kernel/3.19.7/200.fc21/x86_64/kernel-modules-extra-3.19.7-200.fc21.x86_64.rpm
| sudo yum install -y https://kojipkgs.fedoraproject.org//packages/kernel/3.19.7/200.fc21/x86_64/kernel-headers-3.19.7-200.fc21.x86_64.rpm
| sudo yum install -y https://kojipkgs.fedoraproject.org//packages/kernel/3.19.7/200.fc21/x86_64/kernel-devel-3.19.7-200.fc21.x86_64.rpm

Modify grub to boot into the required kernel version and reboot.

Internal proxy config
=====================
If you are working behind a proxy, you will need complete the following steps
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
git and socat.

| sudo yum install -y git socat

Libvirt configuration
---------------------
Some libvirt configurations are required for DPDK support, but first we need
to install libvirt.

| sudo yum install -y libvirt

Modify your libvirt config file to include the following:

| sudo cat /etc/libvirt/qemu.conf

| cgroup_controllers = [ "cpu", "devices", "memory", "blkio", "cpuset", "cpuacct" ]
| cgroup_device_acl = [
|  "/dev/null", "/dev/full", "/dev/zero",
|  "/dev/random", "/dev/urandom",
|  "/dev/ptmx", "/dev/kvm", "/dev/kqemu",
|  "/dev/rtc", "/dev/hpet","/dev/net/tun",
|  "/mnt/huge", "/dev/vhost-net","/dev/vfio/vfio"
| ]

| hugetlbfs_mount = "/mnt/huge"

Restart libvirtd

| sudo service libvirtd restart

Devstack configuration
----------------------
Clone the devstack repo.

| cd ~
| git clone https://github.com/openstack-dev/devstack.git

When you have cloned devstack, the next step is to configure you controller
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
| firewall_driver = openvswitch

By default, the multicast support is enabled. The default aging time for the
IGMP subscriptions in the bridges is 3600 seconds. To configure the multicast
support both variables could be setup in local.conf:

| [[local|localrc]]
| OVS_ENABLE_SG_FIREWALL_MULTICAST=[True/False]
| OVS_MULTICAST_SNOOPING_AGING_TIME=[15..3600]

`More info on the Open vSwitch Firewall Driver in OpenStack
<http://docs.openstack.org/developer/neutron/devref/openvswitch_firewall.html>`_

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

Additional more general issues relating to OVS and OVS with DPDK can be found at the
following link.

 https://github.com/openstack/networking-ovs-dpdk/tree/master/doc/source/known_issues

Using with OpenDaylight
=======================

To use this plugin with OpenDaylight you need Neutron and Networking-ODL plugin:

  https://github.com/openstack/networking-odl

In your local.conf you should enable following lines::

  enable_plugin networking-odl http://git.openstack.org/openstack/networking-odl master
  disable_service q-agt

Because both Networking-ODL and Networking-OVS-DPDK are going to try to install
a different version of Open vSwitch this is order to enable both plugins this
order matter::

  enable_plugin networking-odl http://git.openstack.org/openstack/networking-odl master
  enable_plugin networking-ovs-dpdk http://git.openstack.org/openstack/networking-ovs-dpdk master

In fact Networking-OVS-DPDK plugin will install OVS-DPDK on the system.
By default the Networking-ODL plugin will try to install Kernel OVS.
To workaround this conflict it is possible to forbid Networking-ODL from
installing any version of Open vSwitch by adding followning to the local.conf::

  SKIP_OVS_INSTALL=True

To enable integration of odl with neutron the opendaylight mechanism provided by
Networking-ODL must be enabled::

  Q_ML2_PLUGIN_MECHANISM_DRIVERS=opendaylight

OVS with DPDK exposes accelerated virtual network interfaces such as vhost-user
that can be requested by a VM. The OpenDaylight mechanism driver is capable of
detecting the supported virtual interface types supported by OVS and OVS with DPDK
allowing coexistence of Kernel and DPDK OVS.

To detect if 'vhostuser' is supported the Networking-ODL driver (running on control node)
must be able to translate the host name of compute nodes to their IP addresses on the
management network (the one used by OVS to connect to OpenDaylight).
To archive that you could edit file /etc/hosts on control node where the neutron server
is running adding all compute nodes where you want to use 'vhostuser', or configure DNS
in your environment to enable name resolution.
