===========================================
Getting started with Openstack and OVS-DPDK
===========================================

This is a getting started guide that describes the setup of Openstack with
OVS-DPDK in a dual node configuration.

The command line examples provided match the described topology,
tailor these to suit your environment.

Requirements
------------
The implementation outlined below is executed with the following hardware
and software.

Hardware
========
- 2 * Intel grizzly pass server boards
- CPU: 2 * Intel Xeon CPU E5-2680 v2 @ 2.80GHz
- RAM: Minimum 16GB, recommended 64GB
- 2 * physical networks

Software
========
- Ubuntu 16.04 server
- Kernel version >= 4.4

Pre-requisites
==============
- Ubuntu 16.04 server fresh installation
- A non-root user
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
For this setup it is recommended that a non-root user is used, hence this users
privileges must be elevated. To achieve this the new user must be added to the
sudoers file, this will require admin privileges.

| sudo cat /etc/sudoers
| <USER> ALL=(ALL) NOPASSWD: ALL

Check kernel version
====================
Ubuntu 16.04 requires a kernel version of 4.4. It is no longer compatible with
kernel versions below this.

Internal proxy config
=====================
If you are working behind a proxy, you will need to complete the following steps
to provide git with access to the outside world.

Configure apt-get proxy:

| cat /etc/apt/apt.conf
| Acquire::http::Proxy "http://<PROXY>:<PROXY PORT NUMBER>";

Here is a sample script to provide git access through a proxy:

| sudo cat ~/git-proxy-wrapper

| #!/bin/sh
| _proxy=<PROXY>
| _proxyport=<PROXY PORT NUMBER>
| exec socat STDIO SOCKS4:$_proxy:$1:$2,socksport=$_proxyport

| sudo chown <USER>:<USER> /home/<USER>/git-proxy-wrapper
| sudo chmod +x /home/<USER>/git-proxy-wrapper

Add proxy variables and export to shell:

| cat /home/<USER>/.bashrc

| export GIT_PROXY_COMMAND=~/git-proxy-wrapper
| export http_proxy=http://<PROXY>:<PROXY PORT NUMBER>
| export HTTP_PROXY=http://<PROXY>:<PROXY PORT NUMBER>
| export https_proxy=https://<PROXY>:<PROXY PORT NUMBER>
| export HTTPS_PROXY=https://<PROXY>:<PROXY PORT NUMBER>
| export NO_PROXY=localhost,127.0.0.1,127.0.1.1,<IP OF CONTROLLER NODE>,<IP OF COMPUTE NODE>
| export no_proxy=localhost,127.0.0.1,127.0.1.1,<IP OF CONTROLLER NODE>,<IP OF COMPUTE NODE>

Export these variables:

| source /home/<USER>/.bashrc

Install required packages
-------------------------
Devstack will pull down the required packages, but for the initial clone we need
git, socat.

| sudo apt-get install git socat

Devstack configuration
----------------------
Clone the devstack repo.

| cd /home/<USER>
| git clone https://github.com/openstack-dev/devstack.git

Configure your controller and compute nodes.

The following is a link to a single node local.conf example:

https://github.com/openstack/networking-ovs-dpdk/blob/master/doc/source/_downloads/local.conf.single_node

Certain modifications to this file are required to match the users environment.
E.g. Including the appropriate IP address:

| HOST_IP=<SINGLE NODE IP>

the correct VLAN ranges

| ML2_VLAN_RANGES=default:<VLAN RANGES>

and OVS bridges mappings.

| OVS_BRIDGE_MAPPINGS="default:br-<SINGLE NODE DATA INTERFACE>

Once the local.conf is edited, it must be added to the /home/<USER>/devstack
directory and then it can be stacked:

| cd /home/<USER>/devstack
| ./stack.sh

Boot a VM with OVS-DPDK
-----------------------
OVS-DPDK uses hugepages to communicate with guests. Before you boot a new VM,
which uses OVS-DPDK as a backend to speed up packet processing, you will need to
create a flavor that requests hugepages.

| cd /home/<USER>/devstack
| source openrc admin demo
| nova flavor-key <FLAVOR> set hw:mem_page_size=large

Enable the OVS firewall
-----------------------
To enable the OVS firewall integrated in Neutron, you will need to modify
(or add) the following variable to local.conf:

| [[post-config|/etc/neutron/plugins/ml2/ml2_conf.ini]]
| [securitygroup]
| firewall_driver = openvswitch

This is a stateful firewall and uses connection tracking to control the traffic
flows. In this repository also can be found a stateless firewall based in
OpenFlow 'learn action', which can be enabled by setting the following
variable:

| firewall_driver = networking_ovs_dpdk.agent.ovs_dpdk_firewall.OVSFirewallDriver

By default, the multicast support is enabled. The default aging time for the
IGMP subscriptions in the bridges is 3600 seconds. To configure the multicast
support, both variables could be setup in local.conf:

| [[local|localrc]]
| OVS_ENABLE_SG_FIREWALL_MULTICAST=[True/False]
| OVS_MULTICAST_SNOOPING_AGING_TIME=[15..3600]

`More info on the Open vSwitch Firewall Driver in OpenStack
<http://docs.openstack.org/developer/neutron/devref/openvswitch_firewall.html>`_

Enable overlay networks
-----------------------
To enable overlay networking (vxlan/gre) with the dpdk netdev datapath
the tunnel enpoint ip must be assigned to a physical bridge (a bridge with
a dpdk physical port). This can be done by setting the OVS_TUNNEL_CIDR_MAPPING
variable in the local.conf.
e.g. OVS_TUNNEL_CIDR_MAPPING=br-phy:192.168.50.1/24 assigns the ip of
192.168.50.1 with subnetmask 255.255.255.0 to the br-phy local port.

Known Issues
------------
To work around bug LP 1513367, in /etc/libvirt/qemu.conf set
security_driver="none" then restart service libvirt-bin. Alternatively, remove
apparmor or place all Libvirt apparmor profies into complain mode. Otherwise
you can't spawn VMs successfully and will get the error "Permission denied".

OVS_PMD_CORE_MASK default value '4' doesn't work for NICs from NUMA nodes
other than 0. Its value is used for other_config:pmd-cpu-mask parameter
in ovsdb and we are subsequently using it for vcpu_pin_set in nova.conf.
Unfortunatelly if DPDK NICs from NUMA nodes other than 0 are used, there
is no PMD thread generated for them. If you are using a host with multiple
NUMA nodes please consider not using default OVS_PMD_CORE_MASK value.

Additional more general issues relating to OVS and OVS with DPDK can be found
at the following link.

https://github.com/openstack/networking-ovs-dpdk/tree/master/doc/source/known_issues

Using OVS-DPDK with OpenDaylight
--------------------------------
To use this plugin with OpenDaylight you need Neutron networking and
Networking-ODL plugin:

https://github.com/openstack/networking-odl

In your local.conf you should enable following lines::

 enable_plugin networking-odl http://git.openstack.org/openstack/networking-odl master
 disable_service q-agt

Because both Networking-ODL and Networking-OVS-DPDK are going to try to install
a different version of Open vSwitch, it is important to enable both plugins in
the correct order::

 enable_plugin networking-odl http://git.openstack.org/openstack/networking-odl master
 enable_plugin networking-ovs-dpdk http://git.openstack.org/openstack/networking-ovs-dpdk master

In fact Networking-OVS-DPDK plugin will install OVS-DPDK on the system. By
default the Networking-ODL plugin will try to install Kernel OVS. To workaround
this conflict it is possible to forbid Networking-ODL from installing any
version of Open vSwitch by adding the following to the local.conf::

 SKIP_OVS_INSTALL=True

To enable integration of ODL with Neutron, the OpenDaylight mechanism provided
by Networking-ODL must be enabled::

 Q_ML2_PLUGIN_MECHANISM_DRIVERS=opendaylight

OVS with DPDK exposes accelerated virtual network interfaces such as vhost-user
that can be requested by a VM. The OpenDaylight mechanism driver is capable of
detecting the supported virtual interface types. These interface types are
supported by OVS and OVS with DPDK, this allows the coexistence of Kernel and
DPDK OVS.

To detect if 'vhostuser' is supported the Networking-ODL driver (running on
control node) must be able to translate the host name of compute nodes to their
IP addresses on the management network (the one used by OVS to connect to
OpenDaylight).
