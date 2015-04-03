============
Installation
============

**Install required patches**

There's a set of patches needed for vhost user in OpenVSwitch to work correctly. Here's how you get and install them.

1. Download the below patches to $DEST/patches. Note: $DEST is usually /opt/stack
    http://openvswitch.org/pipermail/dev/2015-March/052061.html

    http://openvswitch.org/pipermail/dev/2015-March/052680.html

    http://openvswitch.org/pipermail/dev/2015-March/052022.html


2. Specify the filenames of the patches in OVS_PATCHES setting in local.conf so they can be automatically applied during stacking.
    See :download:`local.conf_example <_downloads/local.conf_example>` for an example.


**Install required packages**

Fedora:
    yum install -y kernel-headers kernel-core kernel-modules kernel kernel-devel kernel-modules-extra

Ubuntu:
    tbd
