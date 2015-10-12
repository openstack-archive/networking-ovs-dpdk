# Declaring OVS-DPDK manifests with some low-level mem requirements
# (suitable for testing on VM)
# puppet apply install_small.pp --certname ovsdpdk-install -d -v 

node /ovsdpdk-install/ {

  class { '::ovsdpdk':
    ovs_socket_mem    => '512',
    ovs_num_hugepages => '300',
  }

}
