===================
networking-ovs-dpdk
===================

A Collection of Agents and Drivers to support managing DPDK accelerated Open
vSwitch with neutron.

* Free software: Apache license
* Source: http://git.openstack.org/cgit/openstack/networking-ovs-dpdk
* Installation:
   http://git.openstack.org/cgit/openstack/networking-ovs-dpdk/tree/doc/source/installation.rst
* All-in-one local.conf example:
   http://git.openstack.org/cgit/openstack/networking-ovs-dpdk/tree/doc/source/_downloads/local.conf.single_node
* Usage: http://git.openstack.org/cgit/openstack/networking-ovs-dpdk/tree/doc/source/usage.rst
* Bugs: http://bugs.launchpad.net/networking-ovs-dpdk
* Code Reviews:
   https://review.openstack.org/#/q/status:open+project:openstack/networking-ovs-dpdk,n,z
* Questions: E-mail the dev mailing list with the [networking-ovs-dpdk] tag
             mailto:openstack-dev@lists.openstack.org?subject=[networking-ovs-dpdk]

The following are links to background information that provide additional
insight into the outlined setup.
* DPDK
  - Official DPDK website.
    http://www.dpdk.org/
  - Information on how OpenStack is accelerated by DPDK.
    https://software.intel.com/en-us/blogs/2015/02/02/openstack-neutron-accelerated-by-dpdk
    https://01.org/openstack/blogs/stephenfin/2016/enabling-ovs-dpdk-openstack
* OpenDayLight(ODL):
  - Background information on the ODL platform.
    http://www.opendaylight.org/
  - Typical use cases for the ODL platform.
    https://www.opendaylight.org/use-cases
* BrightTALK:
  - Describes the ongoing work to bring the benefits of OVS with DPDK to
    OpenStack.
    https://www.brighttalk.com/webcast/12229/202961
  - A webinar on Intel's contributions to ODL, with specific reference to its
    integtration with OpenStack.
    https://www.brighttalk.com/webcast/12229/203981

Features
--------
* A driver is implemented which enforces security groups through Open vSwitch flows
* A devstack plugin which is provided to compile, configure, install and start ovs with dpdk
