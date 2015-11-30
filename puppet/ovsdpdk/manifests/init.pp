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
#   Defaults to OS defaults if not set. If '1G' value is used hugepages should be
#   allocated before starting ovs (e.g. kernel boot command line)
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
#   Example: ovs_dpdk_port_mappings=eth1:br-01,eth2:br02
#
# [*ovs_log_dir*]
#   directory where ovs-vswitchd.log will be created
#   Defaults: "/tmp"
#
# [*ovs_lock_dir*]
#   directory containing OVS lock file
#
# [*ovs_interface_driver*]
#   (vfio-pci/igb_uio) NIC driver to use for physical network interfaces.
#   Drivers names are the ones supported by DPDK, i.e: not the kernel names.
#   Defaults: "igb_uio"
#
# [*ovs_patches*]
#   *todo*
#
# [*ovs_dpdk_patches*]
#   *todo*
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
  $ovs_num_hugepages           = '1024',
  $ovs_socket_mem              = 'auto',
  $ovs_mem_channels            = '4',
  $ovs_core_mask               = '2',
  $ovs_pmd_core_mask           = '4',
  $ovs_bridge_mappings         = '',
  $ovs_dpdk_port_mappings      = '',
  $ovs_log_dir                 = '/tmp',
  $ovs_lock_dir                = '',
  $ovs_interface_driver        = 'igb_uio',
  $ovs_patches                 = '',
  $ovs_dpdk_patches            = '',
) inherits ::ovsdpdk::params {

  include '::ovsdpdk::clone'
  include '::ovsdpdk::uninstall_ovs'
  include '::ovsdpdk::build_ovs_dpdk'
  include '::ovsdpdk::install_ovs_dpdk'
  include '::ovsdpdk::postinstall_ovs_dpdk'
}
