# == Class ovsdpdk::postinstall_ovs_dpdk
#
# Postinstall configuration of ovs-dpdk service
#
class ovsdpdk::postinstall_ovs_dpdk (
  $plugin_dir       = $::ovsdpdk::params::plugin_dir,
  $nova_conf        = $::ovsdpdk::params::nova_conf,
) inherits ovsdpdk {

  require ovsdpdk::install_ovs_dpdk

  package {'crudini': ensure => installed }

  exec {'adapt_nova_conf_file':
    command => "$plugin_dir/files/set_vcpu_pin.sh $nova_conf",
    path    => ['/usr/bin','/bin'],
    user    => root,
    onlyif  => "test -f $nova_conf",
    require => Package['crudini'],
  }

  # verify ovs-dpdk init.d
  exec {'verify_ovs_dpdk': command => '/etc/init.d/ovs-dpdk status' }
}
