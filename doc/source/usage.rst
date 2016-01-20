=====
Usage
=====
Follow the `Installation <installation.html>`_ document first.
This document describes how to use OVS-DPDK with devstack as well as configuration settings and values they accept.

To use networking-ovs-dpdk with devstack add the below to local.conf::

    enable_plugin networking-ovs-dpdk https://github.com/openstack/networking-ovs-dpdk master


Note: Virtual Machines using vhost-user need to be backed by hugepages.


Example::

    nova flavor-key m1.tiny set "hw:mem_page_size=large"


local.conf settings
-------------------
See :download:`local.conf_example <_downloads/local.conf_example>`_ for sample usage of the below settings.

Default values for the below settings can be found in `settings` file in devstack directory of the main OVS DPDK repository.

**OVS_SOCKET_MEM**
    (Size in MB/auto) Amount of memory reserved by OVS from each NUMA node.

    Default: 'auto' (2048MB per NUMA node)


    Example:

    OVS_SOCKET_MEM=1024,0

    OVS_SOCKET_MEM=auto

**OVS_MEM_CHANNELS**
    (Number) Number of memory channels into the processor OVS will use.

    Default: 4

**OVS_CORE_MASK**
    CPU core mask in hex format; CPU cores are selected according to this value.
    OVS_CORE_MASK is used for ovs-vswitchd process as -c option.

    Deafult: 2

    Example:
    OVS_CORE_MASK=3 ( i.e. 0000 0011 in binary -> first two cores taken)

**OVS_PMD_CORE_MASK**
    The mask in hex format for the PMD threads of ovs set in the db,
    OVS_PMD_CORE_MASK value is used for other_config:pmd-cpu-mask parameter in ovsdb.

    Default: 4 (4 + siblings if HT is enabled)

**OVS_DPDK_MODE**
    ('compute'|'controller_ovs'|'controller_ovs_dpdk') This parameter determines the installation mode of ovs-dpdk.
    It has no default value and when not set plugin works as usual.
    When set, this parameter alters the defaults for other devstack settings if they are not explicitly set by the user as follows:
    "controller_ovs" mode - OVS_DPDK_INSTALL set to 'False'
                          - OVS_AGENT_TYPE set to '$Q_AGENT'
    "compute" mode or "controller_ovs_dpdk" mode - OVS_DPDK_INSTALL set to 'True'
                                                 - OVS_DATAPATH_TYPE set to 'netdev'
    For both controller* modes the openvswitch mechanism driver is added to Q_ML2_PLUGIN_MECHANISM_DRIVERS, if not declared earlier.

**OVS_LOG_DIR**
    (Filesystem path) Directory containing ovs-db and ovs-vswitchd log files.

    Default: /tmp

**OVS_LOCK_DIR**
    (Filesystem path) Directory containing OVS lock file.

**OVS_DIR**
    (Filesystem path) Destination installation directory for compiled OVS DPDK.

**OVS_DPDK_DIR**
    (Filesystem path) Directory containing DPDK compiled libraries.

**OVS_ALLOCATE_HUGEPAGES**
    (True|False) Indicates whether to allocate hugepages for OVS.
    If 'True' OpenVSwitch/DPDK will allocate hugepages of the default size for currently running Operating System.

    Default: True

**OVS_DPDK_GIT_REPO**
    (url) Location of git repo to clone DPDK from.

    Default: http://dpdk.org/git/dpdk

**OVS_GIT_REPO**
    (url) Location of git repo to clone Open vSwitch from.

    Default: https://github.com/openvswitch/ovs.git

**OVS_DPDK_GIT_TAG**
    (<git tag>|<git branch>|<commitId>) Indicates which tag, branch or commitId of DPDK source to checkout before compiling.

**OVS_GIT_TAG**
    (<git tag>|<git branch>|<commitId>) Indicates which tag, branch or commitId of Open vSwitch source to checkout before compiling.

**OVS_NUM_HUGEPAGES**
    (Number) Amount of hugepages (per NUMA node) to mount if OVS_ALLOCATE_HUGEPAGES is True.

    Default: 2048

**OVS_DPDK_VHOST_USER_DEBUG**
    (True|False) Indicates whether to enable debugging for VHOST USER in DPDK.

    Default: False

**OVS_HUGEPAGE_MOUNT**
    (Filesystem path) Mount point to use for hugepages. It's created and hugepages mounted if doesn't exist on the filesystem.

    Default: /mnt/huge

**OVS_HUGEPAGE_MOUNT_PAGESIZE**
    (2M|1G) Preferred hugepage size. Defaults to Operating System's default if not set. If '1G' value is used hugepages should be allocated before starting ovs (i.e.: at kernel boot command line).

**OVS_BRIDGE_MAPPINGS**
    (network:bridge) List of comma separated pairs of "physical network:bridge name" used by DPDK/OVS.
    Example:
    OVS_BRIDGE_MAPPINGS=default:br-eth1,default1:br-enp9s0f0

**OVS_DPDK_PORT_MAPPINGS**
    (nic:bridge) List of comma separated pairs of "nic:bridge name" used by DPDK/OVS.
    "nic" must be a NIC interface present in the system; "bridge" is the linux virtual bridge created by OVS.
    Example:
    OVS_DPDK_PORT_MAPPINGS=eth1:br-01,eth2:br-01,eth3:br-02

**OVS_INTERFACE_DRIVER**
    (vfio-pci|igb_uio) NIC driver to use for physical network interface(s). Note: drivers names are the ones supported by DPDK, i.e.: not the kernel names.

    Default: igb_uio

**OVS_PATCHES**
    (http/ftp/file location) Space separated cURL-like locations of OVS patches. Patches are downloaded and applied in the same order they are listed here.

**OVS_DPDK_PATCHES**
    (http/ftp/file location) Space separated cURL-like locations of DPDK patches. Patches are downloaded and applied in the same order they are listed here.

**OVS_DATAPATH_TYPE**
    (datapath type) OVS bridges will be set to use this datapath. This parameter should be set to 'netdev' (without '') for userspace OVS.

    Default: netdev

**OVS_DPDK_RTE_LIBRTE_VHOST**
    (True|False) Enable libvhost/vhost-cuse. If ovs commit is before vhost-cuse support was added, this should be set to 'False'.

    Default: 'True'

**OVS_TUNNEL_CIDR_MAPPING**
    (bridge:cidr) When spcifed this option enables automatic assignment of the tunnel endpoint ip to a specific interface.
    This is required to enable vxlan or other tunnelling protocols with ovs-dpdk and dpdk phyical ports.

    e.g. OVS_TUNNEL_CIDR_MAPPING=br-phy:192.168.50.1/24 assigns the ip of 192.168.50.1 with subnetmask 255.255.255.0 to the br-phy local port.

**OVS_BOND_MODE**
    (bond:bond_type) comma separated list of bond to mode mappings. Should be used together with OVS_BOND_PORTS.
    bond_mode is optional, one of active-backup, balance-tcp or balance-slb.
    Defaults to active-backup if unset.

    Example:
    OVS_BOND_MODE=bond0:active-backup,bond1:balance-slb

**OVS_BOND_PORTS**
    (bond:nic) comma separated list of bond to NIC mappings. Specified NIC interfaces will be added as dpdk ports to OVS.
    it's also required that user specify bridge for particular bonds in OVS_DPDK_PORT_MAPPINGS, relevant nic's will be added automatically
    Example:
    OVS_BOND_PORTS=bond0:enp9s0f0,bond0:enp9s0f1
    OVS_DPDK_PORT_MAPPINGS=bond0:br-fast

**RTE_TARGET**
    (directory) Points to the DPDK target environment directory in the OVS_DPDK_DIR.

    Default: x86_64-native-linuxapp-gcc

**OVS_DPDK_MEM_SEGMENTS**
    (number) Defines the maximum number of memory segments that DPDK can use while requesting hugepages.

    Default: 256

**OVS_PCI_MAPPINGS**
    (array) List of port name:PCI address mappings. By default this is unset and the value is determined by OVS_DPDK_PORT_MAPPINGS.

    Example: OVS_PCI_MAPPINGS=0000:02:00.0#ens785f0

**OVS_DPDK_SERVICE_DEBUG_OUTPUT**
    (True|False) Defines if OVS-DPDK service should be executed with debug output.

    Default: False

**OVS_ENABLE_SG_FIREWALL_MULTICAST**
    (ovs:enable_sg_firewall_multicast)(True/False) When enabled, using the OVS Security Group firewall, this option allows multicast traffic to get into the OVS and be delivered to the tenants.
    The traffic, anyway, must match the manual rules defined by the administrator.

    Default: False

**OVS_MULTICAST_SNOOPING_AGING_TIME**
    (number) Defines the maximun time (in seconds) a multicast subscription will be alive in the multicast table os a OVS bridge.
    The count starts when a IGMP subscription packet from a port is read by a bridge. During this time, all multicast packets to this multicast group will be delivered to this port. If the count finish or a leave group packet is sent, the register for this port in the multicast table will be deleted.

    Default: 3600
