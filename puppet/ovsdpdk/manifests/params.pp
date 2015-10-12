#
# This class contains the platform differences for ovsdpdk
# and environment not commonly configured stuff
#
class ovsdpdk::params {

  case $::osfamily {
    'Redhat': {
      $ovs_db_conf_dir = '/etc/openvswitch'
      $ovs_db_socket_dir = '/var/run/openvswitch'
    }
    'Debian': {
      $ovs_db_conf_dir = '/usr/etc/openvswitch'
      $ovs_db_socket_dir = '/usr/var/run/openvswitch'
    }
    default: {
      $ovs_db_conf_dir = '/etc/openvswitch'
      $ovs_db_socket_dir = '/var/run/openvswitch'
    }
  }

  $ovs_db_socket            = "${ovs_db_socket_dir}/db.sock"
  $ovs_db_conf              = "${ovs_db_conf_dir}/conf.db"

  # General config
  $plugin_dir               = '/etc/puppet/modules/ovsdpdk'
  $dest                     = '/opt/code'
  $nova_conf_dir            = '/etc/nova'
  $nova_conf                = "${nova_conf_dir}/nova.conf"

  # OVS config
  $ovs_git_repo             = 'https://github.com/openvswitch/ovs.git'
  $ovs_dir                  = "${dest}/ovs"
  $ovs_git_tag              = '7d1ced01772de541d6692c7d5604210e274bcd37'

  # DPDK config
  $ovs_dpdk_git_repo        = 'http://dpdk.org/git/dpdk'
  $ovs_dpdk_git_tag         = 'v2.0.0'
  $ovs_dpdk_dir             = "${dest}/DPDK-${ovs_dpdk_git_tag}"

  # PLUGIN config
  $networking_ovs_dpdk_dir  = "${dest}/networking-ovs-dpdk"
  $ovs_plugin_git_tag       = '7dd1da1c172769bf1e05b13ee713171f591b3462'
}

