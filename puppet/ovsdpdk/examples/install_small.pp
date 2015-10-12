# Declaring OVS-DPDK manifests with some low-level mem requirements
# One can add also other params but OVS_BRIDGE_MAPPINGS is mandatory,
# please fill it in with network:bridge pairs
# e.g.: OVS_BRIDGE_MAPPINGS=default:enp9s0f0
# You can launch it with enabled verbosity as follows:
# puppet apply install_small.pp --certname ovsdpdk-install -d -v

node /ovsdpdk-install/ {

  class { '::ovsdpdk':
    ovs_bridge_mappings => '',
    ovs_socket_mem      => '512',
    ovs_num_hugepages   => '300',
  }

}
