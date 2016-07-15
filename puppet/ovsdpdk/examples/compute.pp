#########################################################
# example of mitaka deployment compute environment      #
# DPDK specific parts are at the bottom of this example #
#########################################################

# Example IP's from test environment
$controller_service_ip = '192.168.51.2'
$compute_service_ip = '192.168.51.3'
$local_tunnel_ip = '192.168.52.3'

Exec { logoutput => 'on_failure' }

# Common resources
case $::operatingsystem {
  'Ubuntu': {
    include ::apt
    class { '::openstack_extras::repo::debian::ubuntu':
      release         => 'mitaka',
      repo            => 'proposed',
      package_require => true,
    }
  }
  'CentOS': {
    class { '::openstack_extras::repo::redhat::redhat':
    release         => 'mitaka',
    }
  }
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
  datapath_type    => 'netdev',
  firewall_driver  => 'neutron.agent.firewall.NoopFirewallDriver',
}

class { '::neutron::plugins::ml2': }

class {'::ovsdpdk':
    ovs_bridge_mappings     => 'default:br-eth1',
    ovs_socket_mem          => 'auto',
    ovs_num_hugepages       => '2048',
    compute                 => 'True',
    ovs_tunnel_cidr_mapping => "br-eth1:${local_tunnel_ip}/24",
}

# deploy nova

class { '::nova':
  database_connection     => "mysql://nova:nova@${controller_service_ip}/nova?charset=utf8",
  api_database_connection => "mysql://nova_api:nova_api@${service_ip}/nova_api?charset=utf8",
  rabbit_host             => "${controller_service_ip}",
  rabbit_userid           => 'nova',
  rabbit_password         => 'an_even_bigger_secret',
  glance_api_servers      => "${controller_service_ip}:9292",
  verbose                 => true,
  debug                   => true,
  notification_driver     => 'messagingv2',
  notify_on_state_change  => 'vm_and_task_state',
}

class { '::nova::compute':
  vncserver_proxyclient_address => "${compute_service_ip}",
  instance_usage_audit          => true,
  instance_usage_audit_period   => 'hour',
}

class { '::nova::network::neutron':
  neutron_url      => "http://${controller_service_ip}:9696",
  neutron_password => 'a_big_secret',
  neutron_auth_url => "http://${controller_service_ip}:35357/v3",
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
