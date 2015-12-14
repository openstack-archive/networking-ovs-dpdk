#
# This class contains the platform differences for ovsdpdk
# and environment not commonly configured stuff
#
class ovsdpdk::params {

  $ovs_db_conf_dir          = '/etc/openvswitch'
  $ovs_db_socket_dir        = '/var/run/openvswitch'
  $ovs_db_socket            = "${ovs_db_socket_dir}/db.sock"
  $ovs_db_conf              = "${ovs_db_conf_dir}/conf.db"

  # General config
  $plugin_dir               = '/etc/puppet/modules/ovsdpdk'
  $dest                     = '/opt/code'
  $nova_conf_dir            = '/etc/nova'
  $nova_conf                = "${nova_conf_dir}/nova.conf"
  $ml2_ovs_conf             = '/etc/neutron/plugins/ml2/openvswitch_agent.ini'
  $neutron_l3_conf          = '/etc/neutron/l3_agent.ini'

  # OVS config
  $ovs_install_dir          = '/usr'
  $ovs_git_repo             = 'https://github.com/openvswitch/ovs.git'
  $ovs_dir                  = "${dest}/ovs"
  $ovs_git_tag              = '88058f19ed9aadb1b22d26d93e46b3fd5eb1ad32'

  # DPDK config
  $ovs_dpdk_git_repo        = 'http://dpdk.org/git/dpdk'
  $ovs_dpdk_git_tag         = 'v2.1.0'
  $ovs_dpdk_dir             = "${dest}/DPDK-${ovs_dpdk_git_tag}"

  # PLUGIN config
  $networking_ovs_dpdk_dir  = "${dest}/networking-ovs-dpdk"
  $ovs_plugin_git_tag       = 'master'

  case $::operatingsystem {
    'Ubuntu': {
      $qemu_kvm = '/usr/bin/kvm'
    }
    'CentOS': {
      $qemu_kvm = '/usr/libexec/qemu-kvm'
    }
    default: {
      $qemu_kvm = '/usr/bin/qemu-kvm'
    }
  }

}

