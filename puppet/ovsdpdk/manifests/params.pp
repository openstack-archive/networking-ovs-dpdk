#
# This class contains the platform differences for ovsdpdk
# and environment not commonly configured stuff
#
class ovsdpdk::params {

  case $::operatingsystem {
    'Ubuntu': {
      $qemu_kvm = '/usr/bin/kvm'
      # we are not removing packages as of now
      #$remove_packages = [ 'openvswitch-switch', 'openvswitch-datapath-dkms', 'openvswitch-common' ]
      $install_packages = [ 'autoconf', 'libtool', 'screen', 'bc' ]
      $openvswitch_service_name = 'openvswitch-switch'
      $openvswitch_service_file = 'openvswitch-switch.conf'
      $openvswitch_service_path = '/etc/init'
      $openvswitch_agent = 'neutron-plugin-openvswitch-agent'
    }
    'CentOS': {
      $qemu_kvm = '/usr/libexec/qemu-kvm'
      # we are not removing packages as of now
      #$remove_packages = [ 'openvswitch' ]
      $install_packages = [ 'pciutils', 'autoconf', 'libtool', 'screen', 'bc' ]
      $openvswitch_service_name = 'openvswitch'
      $openvswitch_service_file = 'openvswitch.service'
      $openvswitch_service_path = '/usr/lib/systemd/system'
      $openvswitch_agent = 'neutron-openvswitch-agent'
    }
    default: {
      fail("Unsupported os ${::operatingsystem}")
    }
  }

  $ovs_db_conf_dir          = '/etc/openvswitch'
  $ovs_db_socket_dir        = '/var/run/openvswitch'
  $ovs_db_socket            = "${ovs_db_socket_dir}/db.sock"
  $ovs_db_conf              = "${ovs_db_conf_dir}/conf.db"

  # General config
  $plugin_dir               = '/etc/puppet/modules/ovsdpdk'
  $dest                     = '/opt/code'
  $nova_conf_dir            = '/etc/nova'
  $nova_conf                = "${nova_conf_dir}/nova.conf"
  $nova_compute_conf        = "${nova_conf_dir}/nova-compute.conf"
  $ml2_conf                 = '/etc/neutron/plugins/ml2/ml2_conf.ini'
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

}
