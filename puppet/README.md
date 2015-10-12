ovsdpdk
==========================================

1.0.0 - 2015.2 - Liberty

#### Table of Contents

1. [Overview - what is networking-ovs-dpdk module ?](#overview)
2. [Installation - how to install ovs with dpdk ?](#installation)
3. [Uninstallation - how to uninstall ovs with dpdk ?](#uninstallation)
4. [Support - what platforms are supported ?](#support)


Overview
--------

The ovsdpdk module is responsible for installation of openvswitch with DPDK support.
It removes the original OVS firsts and subsequently it builds a new one with DPDK.


Installation
------------

#### Installing networking-ovs-dpdk

        Parameters for DPDK build are described in ./ovsdpdk/manifests/init.pp
        Environment settings is possible via ./ovsdpdk/manifests/param.pp
        One of installation examples with very low RAM usage intended for small VMs is below:
        puppet apply /etc/puppet/modules/ovsdpdk/examples/install_small.pp --certname ovs-dpdk-install

        You're supposed to declare ovsdpdk class with your settings similarly to example file.
        Configurable params are described in manifests/init.pp.
        Environment related params are declared in manifests/params.pp


#### Preconditions

	1. vcsrepo puppet module - required for manipulating with git repos.
	it can be installed it via following command if it's missing:
	sudo puppet module install puppetlabs-vcsrepo

	2. virtualization packages - qemu-kvm, libvirt (libvirt-bin in ubuntu)
        "Usually come with OpenStack, but can be checked before installation"



Uninstallation
--------------

        Small bash script ./ovsdpdk/files/clean.sh was written for cleaning ovsdpdk installation



Support
-------

Supported platforms:
* Fedora 21 (fully tested)

plugin should work also on Ubuntu 14.04 but some minor changes in networking-ovs-dpdk project are required
implementation of changes is tracked in:
https://bugs.launchpad.net/networking-ovs-dpdk/+bug/1486697
