# == Class ovsdpdk::postinstall_ovs_dpdk
#
# Postinstall configuration of ovs-dpdk service
#
class ovsdpdk::postinstall_ovs_dpdk (
  $plugin_dir               = $::ovsdpdk::params::plugin_dir,
  $nova_conf                = $::ovsdpdk::params::nova_conf,
  $nova_compute_conf        = $::ovsdpdk::params::nova_compute_conf,
  $openvswitch_service_name = $::ovsdpdk::params::openvswitch_service_name,
  $ml2_conf                 = $::ovsdpdk::params::ml2_conf,
  $neutron_l3_conf          = $::ovsdpdk::params::neutron_l3_conf,
  $openvswitch_agent        = $::ovsdpdk::params::openvswitch_agent,
  $ovs_datapath_type        = $::ovsdpdk::ovs_datapath_type,
  $ovs_pmd_core_mask        = $::ovsdpdk::ovs_pmd_core_mask,
  $openrc_file              = $::ovsdpdk::openrc_file,
) inherits ovsdpdk {

  require ovsdpdk::install_ovs_dpdk

  package {'crudini': ensure => installed }

  ###################################################
  # changing of nova specific configuration options #
  ###################################################
  exec {'adapt_nova_conf':
    command => "${plugin_dir}/files/set_vcpu_pin.sh ${nova_conf}",
    path    => ['/usr/bin','/bin'],
    user    => root,
    onlyif  => "test -f ${nova_conf}",
    require => Package['crudini'],
  }

  # Note: nova-compute.conf doesn't exist in all cases
  exec {'set_libvirt_kvm_compute_conf':
    command => "sudo crudini --set ${nova_compute_conf} libvirt virt_type kvm",
    path    => ['/usr/bin','/bin'],
    user    => root,
    onlyif  => "test -f ${nova_compute_conf}",
    require => Package['crudini'],
  }
  exec {'set_libvirt_kvm_nova_conf':
    command => "sudo crudini --set ${nova_conf} libvirt virt_type kvm",
    path    => ['/usr/bin','/bin'],
    user    => root,
    onlyif  => "test -f ${nova_conf}",
    require => [ Package['crudini'], Exec['set_libvirt_kvm_compute_conf'], Exec['adapt_nova_conf'] ],
  }
    
  exec {'append_NUMATopologyFilter':
    command   => "${plugin_dir}/files/numa_filter_append.sh ${nova_conf}",
    path      => ['/usr/bin','/bin'],
    user      => root,
    onlyif    => "test -f ${nova_conf}",
    require   => [ Package['crudini'], Exec['set_libvirt_kvm_nova_conf'] ],
    logoutput => true,
  }

  exec {'adapt_ml2_conf_datapath':
    command => "sudo crudini --set ${ml2_conf} ovs datapath_type ${ovs_datapath_type}",
    path    => ['/usr/bin','/bin'],
    user    => root,
    onlyif  => "test -f ${ml2_conf}",
    require => [ Package['crudini'], Exec['append_NUMATopologyFilter'] ],
  }

  exec {'adapt_ml2_conf_agent_type':
    command => "sudo crudini --set ${ml2_conf} agent agent_type 'DPDK OVS Agent'",
    path    => ['/usr/bin','/bin'],
    user    => root,
    onlyif  => "test -f ${ml2_conf}",
    require => [ Package['crudini'], Exec['adapt_ml2_conf_datapath'] ],
  }

  # deprecated in Mitaka
  #exec {'adapt_ml2_conf_mechanism_driver':
  #  command => "sudo crudini --set ${ml2_conf} ml2 mechanism_drivers ovsdpdk",
  #  path    => ['/usr/bin','/bin'],
  #  user    => root,
  #  onlyif  => "test -f ${ml2_conf}",
  #  require => [ Package['crudini'], Exec['adapt_ml2_conf_agent_type'] ],
  #}

  exec {'adapt_ml2_conf_security_group':
    command => "sudo crudini --set ${ml2_conf} securitygroup firewall_driver neutron.agent.firewall.NoopFirewallDriver",
    path    => ['/usr/bin','/bin'],
    user    => root,
    onlyif  => "test -f ${ml2_conf}",
    require => [ Package['crudini'], Exec['adapt_ml2_conf_agent_type'] ],
  }

  #############################################################
  # propagate those changes by relevant nova services restart #
  #############################################################

  exec {'restart_nova_compute':
    command => '/usr/sbin/service nova-compute restart',
    user    => root,
    require => Exec['adapt_ml2_conf_security_group'],
  }

  exec {'restart_nova_scheduler':
    command => '/usr/sbin/service nova-scheduler restart',
    user    => root,
    require => [ Exec['agents_flavors_update'], Exec['restart_nova_compute'] ],
  }

  #########################
  # neutron specific part #
  #########################

  exec {'adapt_neutron_l3':
    command => "sudo crudini --set ${neutron_l3_conf} DEFAULT external_network_bridge br-ex",
    path    => ['/usr/bin','/bin'],
    user    => root,
    onlyif  => "test -f ${neutron_l3_conf}",
    require => Package['crudini'],
  }

  service {"${openvswitch_service_name}": ensure => 'running' }

  # restart OVS to synchronize ovsdb-server with ovs-vswitchd needed
  # due to several new --no-wait entries
  exec {'restart_ovs':
    command => "/usr/sbin/service ${openvswitch_service_name} restart",
    user    => root,
    require => Service["${openvswitch_service_name}"],
  }

  exec {'configure_bridges':
    command   => "${plugin_dir}/files/configure_bridges.sh ${ovs_datapath_type}",
    user      => root,
    require   => Exec['restart_ovs'],
    logoutput => true,
  }

  service {"${openvswitch_agent}":
    ensure  => 'running',
    require => [ Exec['restart_ovs'], Service["${openvswitch_service_name}"], Exec['adapt_ml2_conf_datapath'], Exec['adapt_ml2_conf_agent_type']  ],
  }

  exec { "ovs-vsctl --no-wait set Open_vSwitch . other_config:pmd-cpu-mask=${ovs_pmd_core_mask}":
    path    => ['/usr/bin','/bin'],
    user    => root,
    require => Service["${openvswitch_agent}"],
  }

  service {'neutron-server': ensure => 'running' }

  # Openstack CLI is used in thio script
  exec { 'agents_flavors_update':
    command   => "${plugin_dir}/files/agents_flavors_update.sh ${openrc_file}",
    logoutput => true,
    timeout   => 0,
    require   => [ Service['neutron-server'], Exec['append_NUMATopologyFilter'] ],
  }

  exec {'restart_neutron_server':
    command => '/usr/sbin/service neutron-server restart',
    user    => root,
    require => Exec['agents_flavors_update'],
  }

}
