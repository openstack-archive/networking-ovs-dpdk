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

====================
Version Constraints
====================

This document aims to highlight and aid in the resolution of issues involved
in the implementation of OVS, as well as specific issues on installing
OVS with DPDK. In addition to this, the document includes links to specific
information relating to the installation of OVS with DPDK on specific
Linux platforms.

The information contained in this file is based on the FAQ document for OVS.
 https://github.com/openvswitch/ovs/blob/master/FAQ.md

General Issues
------------------

* Each version of OVS only works with a Linux kernel version within a
  certain range:
  ---------------------------------------
  | Open vSwitch | Linux Kernel Version |
  |--------------|----------------------|
  |    1.4.x     |    2.6.18 to 3.2     |
  |    1.5.x     |    2.6.18 to 3.2     |
  |    1.6.x     |    2.6.18 to 3.2     |
  |    1.7.x     |    2.6.18 to 3.3     |
  |    1.8.x     |    2.6.18 to 3.4     |
  |    1.9.x     |    2.6.18 to 3.8     |
  |    1.10.x    |    2.6.18 to 3.8     |
  |    1.11.x    |    2.6.18 to 3.8     |
  |    2.0.x     |    2.6.32 to 3.10    |
  |    2.1.x     |    2.6.32 to 3.11    |
  |    2.3.x     |    2.6.32 to 3.14    |
  |    2.4.x     |    2.6.32 to 4.0     |
  |    2.5.x     |    2.6.32 to 4.3     |
  |    2.6.x     |    3.10 to 4.7       |
  ---------------------------------------

 https://github.com/openvswitch/ovs/blob/master/FAQ.md#q-what-linux-kernel-versions-does-each-open-vswitch-release-work-with

* Linux Kernel version configuration error:

| configure: error: Linux kernel in <dir> is version <x>, but
| version newer than <y> is not supported (please refer to the
| FAQ for advice)

Solution options:
 * Use the kernel module supplied with the kernel.
 * The Open vSwitch master branch may support the kernel version that you are
   using, consider building kernel verison from master.
   The following link provides instructions on implementing this for a ubuntu
   release:
    https://wiki.ubuntu.com/Kernel/BuildYourOwnKernel

* OVS can currently run on any Linux-based virtulization platform.
  E.g. KVM, VirtualBox, Xen, Xen Cloud Platform, XenServer.

* Open vSwitch userspace should also work with the Linux kernel module built
  into Linux 3.3 and later. It is not sensitive to the Linux kernel version
  and should build against almost any kernel.

* OVS supports different datapaths on different platforms, each with a
  different feature set.

  -------------------------------------------------------------------------------
  |  Feature            | Linux upstream | Linux OVS tree | Userspace | Hyper-V |
  |---------------------|----------------|----------------|-----------|---------|
  | NAT                 |      4.6       |      YES       |    NO     |   NO    |
  | Connection tracking |      4.3       |      YES       |  PARTIAL  | PARTIAL |
  | Tunnel-LISP         |      NO        |      YES       |    NO     |   NO    |
  | Tunnel-STT          |      NO        |      YES       |    NO     |   YES   |
  | Tunnel-GRE          |      3.11      |      YES       |    YES    |   YES   |
  | Tunnel-VXLAN        |      3.12      |      YES       |    YES    |   YES   |
  | Tunnel-Geneve       |      3.18      |      YES       |    YES    |   YES   |
  | Tunnel-GRE-IPv6     |      NO        |      NO        |    YES    |   NO    |
  | Tunnel-VXLAN-IPv6   |      4.3       |      YES       |    YES    |   NO    |
  | Tunnel-Geneve-IPv6  |      4.4       |      YES       |    YES    |   NO    |
  | QoS-Policiing       |      YES       |      YES       |    YES    |   NO    |
  | QoS-Shaping         |      YES       |      YES       |    NO     |   NO    |
  | sFlow               |      YES       |      YES       |    YES    |   NO    |
  | IPFIX               |      3.10      |      YES       |    YES    |   NO    |
  | Set action          |      YES       |      YES       |    YES    | PARTIAL |
  | NIC Bonding         |      YES       |      YES       |    YES    |   NO    |
  | Multiple VTEP's     |      YES       |      YES       |    YES    |   NO    |
  -------------------------------------------------------------------------------

  https://github.com/openvswitch/ovs/blob/master/FAQ.md#q-are-all-features-available-with-all-datapaths

* DPDK versions that successfully build with Open vSwitch.

  ------------------------
  | Open vSwitch | DPDK  |
  |--------------|-------|
  |    2.2.x     |  1.6  |
  |    2.3.x     |  1.6  |
  |    2.4.x     |  2.0  |
  |    2.5.x     |  2.2  |
  |    2.6.x     | 16.07 |
  ------------------------

  https://github.com/openvswitch/ovs/blob/master/FAQ.md#q-what-dpdk-version-does-each-open-vswitch-release-work-with

* If there is a performance drop when OVS is upgraded, this could mean that the
  OVS kernel datapath may have been updated to a newer version. Sometimes new
  versions of the OVS kernel module add functionality that is backwards
  compatible with older userspace components, but may cause a drop in
  performance with them. Updating the OVS userspace components to the latest
  released version should fix the performance degradation issue.

* Open vSwitch only supports certain versions of OpenFlow:

   -----------------------------------------------------------------------------
   |  Open vSwitch     | OF1.0 | OF1.1 | OF1.2 | OF1.3 | OF1.4 | OF1.5 | OF1.6 |
   |-------------------|-------|-------|-------|-------|-------|-------|-------|
   |  1.9 and earlier  |  yes  |  ---  |  ---  |  ---  |  ---  |  ---  |   --- |
   |       1.10        |  yes  |  ---  |  [*]  |  [*]  |  ---  |  ---  |   --- |
   |       1.11        |  yes  |  ---  |  [*]  |  [*]  |  ---  |  ---  |   --- |
   |       2.0         |  yes  |  [*]  |  [*]  |  [*]  |  ---  |  ---  |   --- |
   |       2.1         |  yes  |  [*]  |  [*]  |  [*]  |  ---  |  ---  |   --- |
   |       2.2         |  yes  |  [*]  |  [*]  |  [*]  |  [%]  |  [*]  |   --- |
   |       2.3         |  yes  |  yes  |  yes  |  yes  |  [*]  |  [*]  |   --- |
   |       2.4         |  yes  |  yes  |  yes  |  yes  |  [*]  |  [*]  |   --- |
   |       2.5         |  yes  |  yes  |  yes  |  yes  |  [*]  |  [*]  |   [*] |
   -----------------------------------------------------------------------------

   [*] Supported, with one or more missing features.
   [%] Experimental, unsafe implementation.

 https://github.com/openvswitch/ovs/blob/master/FAQ.md#q-what-versions-of-openflow-does-open-vswitch-support

  In Open vSwitch 1.10 through 2.2, OpenFlow 1.1, 1.2 and 1.3 must be enabled
  manually in ovs-switched.
  OpenFlow 1.4 and 1.5 in Open vSwitch 2.3 and later, as well as OpenFlow 1.6
  in Open vSwitch 2.5 and later are supported but have missing features and so
  are not enabled by default.
  The user can overide any of these defaults:

| ovs-vsctl set bridge br0 protocols=OpenFlow10,OpenFlow11,OpenFlow12,OpenFlow13

| ovs-vsctl set bridge br0 protocols=OpenFlow10,OpenFlow11,OpenFlow12,OpenFlow13,OpenFlow14,OpenFlow15

| ovs-vsctl set bridge br0 protocols=OpenFlow10

  All current versions of ovs-ofctl enable only OpenFlow 1.0 by default.
  Use the -O option to enable support for later versions of OpenFlow in
  ovs-ofctl.

* Difficulty connecting to an OpenFlow controller or OVSDB manager may be due
  to specifying the wrong port numbers. In OVS 2.4, the default ports were
  switched to the IANA-specified port numbers.
  For Openflow: 6633->6653
  For OVSDB: 6632->6640

Specific Platform based Issues with OVS and DPDK
---------------------------------------------------
Certain issues specific to the linux platform being used to install OVS with DPDK
are highlighted in each of the getting started guides below.
* Centos:
   https://github.com/openstack/networking-ovs-dpdk/tree/master/doc/source/getstarted/devstack/centos.rst
* Fedora:
   https://github.com/openstack/networking-ovs-dpdk/tree/master/doc/source/getstarted/devstack/fedora.rst
* Ubuntu:
   https://github.com/openstack/networking-ovs-dpdk/tree/master/doc/source/getstarted/devstack/ubuntu.rst
