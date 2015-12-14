# Declaring OVS-DPDK manifests with minimal config changes

# Please don't forget to insert following mandatory params before execution:
# ovs_bridge_mappings - script is taking nic's for dpdk driver from it
#                       please fill it in with network:bridge pairs
# e.g. ovs_bridge_mappings => 'default:br-eth2',
#
# openrc_file         - path to openc file required for openstack cli commands
# e.g. openrc_file         => '/root/openrc'

# You can launch it with enabled verbosity as follows:
# sudo puppet apply install_small.pp --certname ovsdpdk-install -d -v

node /ovsdpdk-install/ {

  class { '::ovsdpdk':
    ovs_bridge_mappings => 'default:br-eth2',
    openrc_file         => '/root/openrc',
    ovs_socket_mem      => '2048',
    ovs_num_hugepages   => '2048',
  }
}
