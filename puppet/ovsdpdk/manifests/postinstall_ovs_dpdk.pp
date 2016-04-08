# == Class ovsdpdk::postinstall_ovs_dpdk
#
# Postinstall configuration of ovs-dpdk service
#
class ovsdpdk::postinstall_ovs_dpdk (
  $plugin_dir               = $::ovsdpdk::params::plugin_dir,
  $nova_conf                = $::ovsdpdk::params::nova_conf,
  $openvswitch_service_name = $::ovsdpdk::params::openvswitch_service_name,
  $openvswitch_agent        = $::ovsdpdk::params::openvswitch_agent,
  $ovs_datapath_type        = $::ovsdpdk::ovs_datapath_type,
  $ovs_pmd_core_mask        = $::ovsdpdk::ovs_pmd_core_mask,
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
    }

    exec {'restart_nova_compute':
      command => '/usr/sbin/service nova-compute restart',
      user    => root,
    }

    exec {'restart_ovs_agent':
      command => "/usr/sbin/service ${openvswitch_agent} restart",
      user    => root,
      require => Exec['restart_ovs'],
    }

    exec { "ovs-vsctl set Open_vSwitch . other_config:pmd-cpu-mask=\
$(cat /etc/default/ovs-dpdk | grep 'OVS_PMD_CORE_MASK' | tr -d 'OVS_PMD_CORE_MASK=')":
      path    => ['/usr/bin','/bin'],
      user    => root,
      require => Exec['restart_ovs'],
    }

    exec {'configure_bridges':
      command   => "${plugin_dir}/files/configure_bridges.sh ${ovs_datapath_type}",
      user      => root,
      require   => Exec['restart_ovs'],
      logoutput => true,
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
      logoutput => true,
    }

    exec {'adjust_vcpu_pinset':
      command   => "${plugin_dir}/files/set_vcpu_pin.sh ${nova_conf}",
      path      => ['/usr/bin','/bin'],
      user      => root,
      onlyif    => "test -f ${nova_conf}",
      require   => Package['crudini'],
      logoutput => true,
    }

    exec {'restart_nova_scheduler':
      command => '/usr/sbin/service nova-scheduler restart',
      user    => root,
      require => [ Exec['append_NUMATopologyFilter'], Exec['adjust_vcpu_pinset'] ],
    }

    # neutron specific part
    exec {'restart_neutron_server':
      command => '/usr/sbin/service neutron-server restart',
      user    => root,
    }
  }
  
  if ($compute != "True") and ($controller != "True") {
    warning('Controller or compute node not specified')
  }
}
