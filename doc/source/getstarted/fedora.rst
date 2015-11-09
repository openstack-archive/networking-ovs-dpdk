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
- RAM: Minimum 16GB, recommened 64GB
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
To elevate user privileges, add them to the suoders file, you will need admin
privileges for this.

| sudo cat /etc/sudoers
| <USER> ALL=(ALL) NOPASSWD: ALL

Relax SELINUX control
=====================
| sudo cat /etc/selinux/config
| SELINUX=permissive

Downgrade kernel
================
DPDK 2.0 currently supports kernel versions up to 3.19. This guide details
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












