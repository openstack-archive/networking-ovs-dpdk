=====
Usage
=====
Follow the `Installation <installation.html>`_ document first.
This document describes how to use OVS-DPDK with devstack as well as configuration settings and values they accept.

To use networking-ovs-dpdk with devstack add the below to local.conf::

    enable_plugin networking-ovs-dpdk https://github.com/stackforge/networking-ovs-dpdk master


Note: Virtual Machines using vhost-user need to be backed by hugepages.


Example::

    nova flavor-key m1.tiny set "hw:mem_page_size=large"


local.conf settings
-------------------
See :download:`local.conf_example <_downloads/local.conf_example>` for sample usage of the below settings.

Default values for the below settings can be found in `settings` file in devstack directory of the main OVS DPDK repository.

**OVS_INSTALL_DIR**
    (Filesystem path) Directory containing OVS compiled files are installed to.

**OVS_DB_CONF_DIR**
    (Filesystem path) Directory containing OVS configuration and database files.
    Default: /etc/openvswitch/

**OVS_DB_SOCKET_DIR**
    (Filesystem path) Directory to create socket of a running OVS in.

**OVS_DB_CONF**
    (Filesystem path) File path to OVS configuration database.

**OVS_DB_SOCKET**
    (Filesystem path) File path to OVS socket.

**OVS_SOCKET_MEM**
    (Size in MB/auto) Amount of memory reserved by OVS from each Numa node. 'auto' defaults to 2048MB per Numa node.
    Example:
    OVS_SOCKET_MEM=1024,0
    OVS_SOCKET_MEM=auto

**OVS_MEM_CHANNELS**
    (Number) Number of memory channels into the processor OVS will use.

**OVS_CORE_MASK**
    cpu core mask in hexa format, according to it's value CPU cores are selected.
    OVS_CORE_MASK is used for ovs-vswitchd process as -c option, it has default value 2.

    Example:
    OVS_CORE_MASK=3 (0x011 binary -> first two cores taken)

**OVS_PMD_CORE_MASK**
    the mask in hexa format for the PMD threads of ovs set in the db,
    OVS_PMD_CORE_MASK value is used for other_config:pmd-cpu-mask parameter in ovsdb.
    It has default value 4. In case of HT enabled, it's 4 + sibling.

**OVS_LOG_DIR**
    (Filesystem path) Directory containing ovs-db and ovs-vswitchd log files.

**OVS_LOCK_DIR**
    (Filesystem path) Directory containing OVS lock file.

**OVS_SRC_DIR**
    (Filesystem path) Directory containing OVS source code. It's used along with RTE_SDK and RTE_TARGET to compile OVS DPDK.

**OVS_DIR**
    (Filesystem path) Destination installation directory for compiled OVS DPDK.

**OVS_UTILS**
    (Filesystem path) Destination installation directory for compiled OVS DPDK utilities.

**OVS_DB_UTILS**
    (Filesystem path) Directory containing OVS DB and related utilities.

**OVS_DPDK_DIR**
    (Filesystem path) Directory containing DPDK compiled libraries.

**OVS_ALLOCATE_HUGEPAGES**
    (True/False) Indicates whether to allocate hugepages for OVS. If 'True' OpenVSwitch/DPDK will allocate hugepages of the default size for currently running Operating System (i.e.: 2kB).

**OVS_DPDK_GIT_TAG**
    (git tag/branch/commitId) Indicates which tag, branch or commitId of DPDK source to checkout before compiling.

**OVS_NUM_HUGEPAGES**
    (Number) Amount of hugepages to mount if OVS_ALLOCATE_HUGEPAGES is True.

**OVS_DPDK_VHOST_USER_DEBUG**
    (True/False) Indicates whether to enable debugging for VHOST USER in DPDK.

**OVS_HUGEPAGE_MOUNT**
    (Filesystem path) Mount point to use for hugepages. It's created and hugepages mounted if doesn't exist on the filesystem.

**OVS_HUGEPAGE_MOUNT_PAGESIZE**
    (2M/1G) Preferred hugepage size. Defaults to Operating System's default if not set. If '1G' value is used hugepages should be allocated before starting ovs (i.e.: at kernel boot command line).

**OVS_BRIDGE_MAPPINGS**
    (network:bridge) List of comma separated pairs of "physical network:bridge name" used by DPDK/OVS.
    Example:
    OVS_BRIDGE_MAPPINGS=default:br-eth1,default1:br-enp9s0f0

**OVS_INTERFACE_DRIVER**
    (vfio-pci/igb_uio) NIC driver to use for physical network interface(s). Note: drivers names are the ones supported by DPDK, i.e.: not the kernel names.

**OVS_AGENT_TYPE**
    (openvswitch/dpdk/...) Name of the Q_AGENT to use. Defaults to 'ovsdpdk' if not set.

**OVS_PATCHES**
    (http/ftp/file location) Space separated cURL-like locations of OVS patches. Patches are downloaded and applied in the same order they are listed here.

**OVS_DATAPATH_TYPE**
    (datapath type) OVS bridges will be set to use this datapath. This parameter should be set to 'netdev' (without '') for userspace OVS.
