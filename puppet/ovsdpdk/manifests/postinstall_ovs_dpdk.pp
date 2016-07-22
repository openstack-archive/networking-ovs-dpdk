# == Class ovsdpdk::postinstall_ovs_dpdk
#
# Postinstall configuration of ovs-dpdk service
#
class ovsdpdk::postinstall_ovs_dpdk (
  $plugin_dir               = $::ovsdpdk::params::plugin_dir,
  $ovs_dpdk_dir             = $::ovsdpdk::params::ovs_dpdk_dir,
  $nova_conf                = $::ovsdpdk::params::nova_conf,
  $openvswitch_service_name = $::ovsdpdk::params::openvswitch_service_name,
  $ovs_install_dir          = $::ovsdpdk::params::ovs_install_dir,
  $ovs_db_socket_dir        = $::ovsdpdk::params::ovs_db_socket_dir,
  $ovs_db_socket            = $::ovsdpdk::params::ovs_db_socket,
  $ovs_datapath_type        = $::ovsdpdk::ovs_datapath_type,
  $ovs_pmd_core_mask        = $::ovsdpdk::ovs_pmd_core_mask,
  $ovs_interface_driver     = $::ovsdpdk::ovs_interface_driver,
  $compute                  = $::ovsdpdk::compute,
  $controller               = $::ovsdpdk::controller,
) inherits ovsdpdk {

  package {'crudini': ensure => installed }

  #########################
  # compute specific part #
  #########################
  if $compute == 'True' {
    # restart modified services
    exec {'restart_ovs':
      command => "/usr/sbin/service ${openvswitch_service_name} restart",
      user    => root,
      require => Exec['update PMD cpumask'],
    }

    # this value has to be placed in ovsdb-server db, which is done in devstack during
    # init script initialization
    exec {'update PMD cpumask':
      command =>  "sudo ${ovs_install_dir}/sbin/ovsdb-server  --detach --pidfile=${ovs_db_socket_dir}/ovsdb-server.pid\
 --remote=punix:${ovs_db_socket}  --remote=db:Open_vSwitch,Open_vSwitch,manager_options;sleep 10;ovs-vsctl --no-wait set\
 Open_vSwitch . other_config:pmd-cpu-mask=$(cat /etc/default/ovs-dpdk | grep 'OVS_PMD_CORE_MASK' | tr -d 'OVS_PMD_CORE_MASK=');",
      path    => ['/usr/bin','/bin'],
      user    => root,
    }

    exec {'configure_bridges':
      command   => "${plugin_dir}/files/configure_bridges.sh ${ovs_datapath_type}",
      user      => root,
      require   => Exec['restart_ovs'],
      logoutput => true,
    }

    exec {'adjust_vcpu_pinset':
      command   => "${plugin_dir}/files/set_vcpu_pin.sh ${nova_conf}",
      path      => ['/usr/bin','/bin'],
      user      => root,
      onlyif    => "test -f ${nova_conf}",
      require   => Package['crudini'],
      notify    => Service["${nova_compute_service_name}"],
      logoutput => true,
    }

    exec {'add_autoload':
      command   => "${plugin_dir}/files/add_autoload.sh ${ovs_dpdk_dir} ${ovs_interface_driver}",
    }

  }
  ############################
  # controller specific part #
  ############################
  if $controller == 'True' {
    # changing of nova specific configuration options
    exec {'append_NUMATopologyFilter':
      command   => "${plugin_dir}/files/numa_filter_append.sh ${nova_conf}",
      path      => ['/usr/bin','/bin'],
      user      => root,
      onlyif    => "test -f ${nova_conf}",
      require   => Package['crudini'],
      notify    => Service["${nova_scheduler_service_name}"],
      logoutput => true,
    }

  }

  if ($compute != "True") and ($controller != "True") {
    warning('Controller or compute node not specified')
  }
}
