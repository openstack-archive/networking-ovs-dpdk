#########################################################
# example of liberty deployment compute environment     #
# DPDK specific parts are at the bottom of this example #
#########################################################

# Example IP's from test environment
$controller_service_ip = '10.237.214.161'
$compute_service_ip = '10.237.214.235'
$local_tunnel_ip = '192.168.52.3'

Exec { logoutput => 'on_failure' }
# Common resources
include ::apt
class { '::openstack_extras::repo::debian::ubuntu':
  release         => 'liberty',
  repo            => 'proposed',
  package_require => true,
}

################
# OVSDPDK PART #
################

class { '::nova::compute::libvirt':
  libvirt_virt_type => 'kvm',
  migration_support => true,
  vncserver_listen  => '0.0.0.0',
}

class { '::neutron::agents::ml2::ovs':
  enable_tunneling => true,
  tunnel_types     => ['vxlan', 'gre'],
  local_ip         => "${local_tunnel_ip}",
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
    ovs_bridge_mappings     => 'default:br-eth1',
    ovs_socket_mem          => 'auto',
    ovs_num_hugepages       => '2048',
    compute                 => 'True',
    ovs_tunnel_cidr_mapping => "br-eth1:${local_tunnel_ip}/24",
}

# deploy nova

class { '::nova':
  database_connection    => "mysql://nova:nova@${controller_service_ip}/nova?charset=utf8",
  rabbit_host            => "${controller_service_ip}",
  rabbit_userid          => 'nova',
  rabbit_password        => 'an_even_bigger_secret',
  glance_api_servers     => "${controller_service_ip}:9292",
  verbose                => true,
  debug                  => true,
  notification_driver    => 'messagingv2',
  notify_on_state_change => 'vm_and_task_state',
}

class { '::nova::compute':
  vncserver_proxyclient_address => "${compute_service_ip}",
  instance_usage_audit          => true,
  instance_usage_audit_period   => 'hour',
}

class { '::nova::network::neutron':
  neutron_url            => "http://${controller_service_ip}:9696",
  neutron_admin_password => 'a_big_secret',
  neutron_admin_auth_url => "http://${controller_service_ip}:35357/v2.0",
}


class { 'nova::vncproxy': }

# deploy neutron

class { '::neutron':
  rabbit_user           => 'neutron',
  rabbit_password       => 'an_even_bigger_secret',
  rabbit_host           => "${controller_service_ip}",
  allow_overlapping_ips => true,
  core_plugin           => 'ml2',
  service_plugins       => ['router', 'metering'],
  debug                 => true,
  verbose               => true,
}

class { '::neutron::client': }
