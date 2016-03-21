#########################################################
# example of liberty deployment compute environment     #
# DPDK specific parts are at the bottom of this example #
#########################################################

Exec { logoutput => 'on_failure' }

# Common resources
include ::apt
class { '::openstack_extras::repo::debian::ubuntu':
  release         => 'liberty',
  repo            => 'proposed',
  package_require => true,
}

# deploy nova

class { '::nova':
  database_connection    => 'mysql://nova:nova@10.237.214.161/nova?charset=utf8',
  rabbit_host            => '10.237.214.161',
  rabbit_userid          => 'nova',
  rabbit_password        => 'an_even_bigger_secret',
  glance_api_servers     => '10.237.214.161:9292',
  verbose                => true,
  debug                  => true,
  notification_driver    => 'messagingv2',
  notify_on_state_change => 'vm_and_task_state',
}

class { '::nova::compute':
  vncserver_proxyclient_address => '10.237.214.235',
  instance_usage_audit          => true,
  instance_usage_audit_period   => 'hour',
}

class { '::nova::network::neutron':
  neutron_url            => 'http://10.237.214.161:9696',
  neutron_admin_password => 'a_big_secret',
  neutron_admin_auth_url => 'http://10.237.214.161:35357/v2.0',
}


class { 'nova::vncproxy': }

# deploy neutron

class { '::neutron':
  rabbit_user           => 'neutron',
  rabbit_password       => 'an_even_bigger_secret',
  rabbit_host           => '10.237.214.161',
  allow_overlapping_ips => true,
  core_plugin           => 'ml2',
  service_plugins       => ['router', 'metering'],
  debug                 => true,
  verbose               => true,
}

class { '::neutron::client': }

class { '::neutron::agents::ml2::ovs':
  enable_tunneling => true,
  tunnel_types     => ['vxlan', 'gre'],
  local_ip         => '192.168.52.3',
}

################
# OVSDPDK PART #
################

class { '::nova::compute::libvirt':
  libvirt_virt_type => 'kvm',
  migration_support => true,
  vncserver_listen  => '0.0.0.0',
}

class { '::neutron::plugins::ml2':
  mechanism_drivers    => ['ovsdpdk'],
}

class { '::neutron::config':
  plugin_ml2_config =>
    { 'ovs/datapath_type'             => { value => 'netdev'},
      'agent/agent_type'              => { value => 'DPDK OVS Agent'},
      'securitygroup/firewall_driver' => { value => 'neutron.agent.firewall.NoopFirewallDriver' },
    }
}

class {'::ovsdpdk':
    ovs_bridge_mappings => 'default:br-eth1',
    ovs_socket_mem      => '2048',
    ovs_num_hugepages   => '2048',
    compute             => 'True',
}

