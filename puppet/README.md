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
As of now we are not providing package distributions, therefore we can't remove vanilla ovs 
mainly due to package dependencies. Current procedure is to replace vanilla ovs binaries with 
dpdk tuned binaries together with ovs service to use our control script.


Installation
------------

#### Installing ovsdpdk puppet module

        Step1) Get freshly installed OS from supported platforms below

        Step2) Openstack installation based on puppet modules
        We are using puppet-openstack-integration for the same, instructions are under following link:
        https://wiki.openstack.org/wiki/Puppet/Deploy

        Original system/kernel based ovs configuration will be replaced during ovs-dpdk init.
        So it's recommended to perform ovsdpdk installation on freshly installed openstack w/o any VM running.

        Step3) Customize ovsdpdk parameters based on your environment
        Parameters for DPDK build are described in ./ovsdpdk/manifests/init.pp
        Environment variables are in ./ovsdpdk/manifests/param.pp and not expected to be changed frequently
        One of installation examples with very low RAM usage intended for small VMs is in ./examples/install_small.pp
        Instructions how to use it are in this file, but you will most likely need to customize it differently.

#### Preconditions

        1. It's usefull to check whether openstack is in good shape before ovsdpdk deployment
        (e.g. via system info in openstack dashboard)

        2. Any OVS settings (e.g each vm will probably own port on br-int bridge) will get lost during deployment
        It's recommended to deploy ovsdpdk on fresh openstack installation.

        3. As part of installation of ovs-dpdk some system services will be upgraded and replaced.
        This may cause some OpenStack services to crash and my require them to be restarted after installation.



Uninstallation
--------------

        Small bash script ./ovsdpdk/files/clean.sh was written for cleaning ovsdpdk installation
        [ToDo - need to rework, by this script we are not installing original package]


Support
-------

Supported platforms: 
(same as for puppet-openstack-integration)
* Centos 7.1+
* Ubuntu 14.04 LTS

