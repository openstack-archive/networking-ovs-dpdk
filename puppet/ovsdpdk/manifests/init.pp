# == Class: ovsdpdk
#
# Configures and installs OVS with DPDK support service
#
# == Parameters:
#
# [*rte_target*]
#   rte_target to compile OVS DPDK
#   Defaults to 'x86_64-native-linuxapp-gcc'
#
# [*ovs_dpdk_mem_segments*]
#   another parameter for OVS DPDK build
#   Defaults to '256'
#
# [*ovs_dpdk_rte_librte_vhost*]
#   another parameter for OVS DPDK build
#   Defaults to 'y'
#
# [*ovs_dpdk_vhost_user_debug*]
#   (True/False) indicates whether to enable debugging for VHOST USER in DPDK
#   Defaults to 'n'
#
# [*ovs_allocate_hugepages*]
#   (True/False) indicates whether to allocate hugepages during ovs-dpdk startup
#   Defaults to 'True'
#
# [*ovs_datapath_type*]
#   OVS bridges will be set to use this datapath, possible values are 'system'
#   for kernel OVS and 'netdev' for userspace OVS
#   Defaults to 'netdev'
#
# [*ovs_tunnel_cidr_mapping*]
#   (bridge:cidr) when specified, this option enables automatic assignment of
#   the tunnel endpoint ip to a specific interface.
#   e.g. OVS_TUNNEL_CIDR_MAPPING=br-phy:192.168.50.1/24 assignes the ip of
#   192.168.50.1 with subnetmask 255.255.255.0 to the br-phy local port.
#   This is required to enabled vxlan or other tunneling protocols with ovs-dpdk
#   and dpdk physical ports.
#
# [*ovs_hugepage_mount*]
#   mount point to use for hugepages. It's created and hugepages mounted if
#   it doesn't exist on the filesystem
#   Defaults to '/mnt/huge'
#
# [*ovs_hugepage_mount_pagesize*]
#   preffered hugepage size (2M/1G)
#   Defaults to OS defaults if not set. If '1G' value is used hugepages
#   should be allocated before starting ovs (e.g. kernel boot command line)
#
# [*ovs_num_hugepages*]
#   amount of hugepages to mount if ovs_allocate_hugepages is True
#
# [*ovs_socket_mem*]
#   amount of memory to allocate on socket, recommended minimum is '512' MB
#
# [*ovs_mem_channels*]
#   number of memory channels into the processor OVS will use
#
# [*ovs_core_mask*]
#   cpu core mask in hexa format, is used for ovs-vswitchd process as -c option
#   Defaults is '2'
#   Example:
#   ovs_core_mask=3 (0x11 binary -> first two cores taken)
#
# [*ovs_pmd_core_mask*]
#   mask in hexa format for PMD threads od OVS set in the db.
#   ovs_pmd_core_mask value is used for other_config:pmd-cpu-mask parameter in
#   ovsdb.
#   Defaults is '4'. In case of HT enabled, it's 4 + sibling
#
# [*ovs_bridge_mappings*]
#   (network:bridge) list of comma separated pairs of "physical network:bridge"
#   used by OVS/DPDK.
#   Example: ovs_bridge_mappings=default:br-eth1,defaul1:br-enp9s0f0
#
# [*ovs_dpdk_port_mappings*]
#   (nic:bridge) list of comma separated pairs of "nic:bridge name" used by
#   OVS/DPDK. "nic" must be a NIC interface present in the system
#   "bridge" is the linux bridge created by OVS
#   Example: ovs_dpdk_port_mappings=eth1:br-01,eth2:br-02
#
# [*ovs_log_dir*]
#   directory where ovs-vswitchd.log will be created
#   Defaults: "/tmp"
#
# [*ovs_lock_dir*]
#   directory containing OVS lock file
#
# [*ovs_interface_driver*]
#   (vfio-pci/igb_uio/uio_pci_generic) NIC driver to use for physical network interfaces.
#   Drivers names are the ones supported by DPDK, i.e: not the kernel names.
#   Defaults: "igb_uio"
#
# [*controller*]
#   if set to True, controller specific changes will be applied
#   Defaults: "False"
#
# [*compute*]
#   if set to True, compute specific changes will be applied
#   Defaults: "False"
#
# [*ovs_bond_mode*]
#   (bond:bond_type) comma separated list of bond to mode mappings. Should be used
#   together with ovs_bond_ports. Bond_mode is optional, one of active-backup,
#   balance-tcp or balance-slb. Defaults to active-backup if unset.
#   Example: ovs_bond_mode=bond0:active-backup,bond1:balance-slb
#
# [*ovs_bond_ports*]
#   (bond:nic) comma separated list of bond to NIC mappings. Specified NIC
#   interfaces will be added as dpdk ports to OVS. It's also required that
#   user specify bridge for particular bonds in ovs_dpdk_port_mappings,
#   relevant nic's will be added automatically.
#   Example:
#   ovs_bond_ports=bond0:enp9s0f0,bond0:enp9s0f1
#   ovs_dpdk_port_mappings=bond0:br-fast
#
# [*ovs_patches*]
#   (http/ftp/file location) Space separated cURL-like locations of OVS patches.
#   Patches are downloaded and applied in the same order they are listed here.
#   Example: ovs_patches='file:///root/ovs1.patch'
#
# [*ovs_dpdk_patches*]
#   (http/ftp/file location) Space separated cURL-like locations of DPDK patches.
#   Patches are downloaded and applied in the same order they are listed here.
#   Example: ovs_dpdk_patches='file:///root/dpdk1.patch file:///root/dpdk2.patch'
#
# [*ovs_enable_sg_firewall_multicast*]
#   *todo
#
# [*ovs_multicast_snooping_aging_time*]
#   *todo
#
# [*ovs_emc_size*]
#    (number) Defines the value which will be replaced in constant EM_FLOW_HASH_SHIFT in ovs lib/dpif-netdev.c.
#    The constant represents count of bits for hash.
#
# [*ovs_init_policy*]
#    This setting controls how ovs with dpdk is enabled.
#    Allowed values: 'cmd', 'db', 'auto'
#    cmd:  setting this value enables the legacy workflow where dpdk paramaters are passed on the ovs-vswitchd commandline.
#    db:   setting this value enables the new workflow where dpdk paramaters are stored in the ovsdb.
#    auto: setting this value instructs the plugin to try and deterim the correct value to use.
#    
#    Default: 'auto'
#
#    Example: ovs_init_policy='db'
#

class ovsdpdk (
  $rte_target                  = 'x86_64-native-linuxapp-gcc',
  $ovs_dpdk_mem_segments       = '256',
  $ovs_dpdk_rte_librte_vhost   = 'y',
  $ovs_dpdk_vhost_user_debug   = 'n',
  $ovs_allocate_hugepages      = 'True',
  $ovs_datapath_type           = 'netdev',
  $ovs_tunnel_cidr_mapping     = '',
  $ovs_hugepage_mount          = '/mnt/huge',
  $ovs_hugepage_mount_pagesize = '2M',
  $ovs_num_hugepages           = '2048',
  $ovs_socket_mem              = 'auto',
  $ovs_mem_channels            = '4',
  $ovs_core_mask               = '2',
  $ovs_pmd_core_mask           = '4',
  $ovs_bridge_mappings         = '',
  $ovs_dpdk_port_mappings      = '',
  $ovs_log_dir                 = '/tmp',
  $ovs_lock_dir                = '',
  $ovs_interface_driver        = 'igb_uio',
  $controller                  = 'False',
  $compute                     = 'False',
  $ovs_bond_mode               = 'active-backup',
  $ovs_bond_ports              = '',
  $ovs_patches                 = '',
  $ovs_dpdk_patches            = '',
  $ovs_emc_size                = '',
  $ovs_init_policy             = 'auto',
) inherits ::ovsdpdk::params {

  anchor { '::ovsdpdk::start': }->
    class { '::ovsdpdk::prepare': }->
    class { '::ovsdpdk::build_ovs_dpdk': }->
    class { '::ovsdpdk::install_ovs_dpdk': }->
    class { '::ovsdpdk::postinstall_ovs_dpdk': }->
  anchor { '::ovsdpdk::end': }

}
