#########################################################
# example of mitaka deployment controller environment   #
# DPDK specific parts are at the bottom of this example #
#########################################################

# Example IP's from test environment
$controller_service_ip = '192.168.51.2'
$local_tunnel_ip = '192.168.52.2'
# public network below with CIDR 172.24.5.0/24

Exec { logoutput => 'on_failure' }
# Common resources
include ::apt
class { '::openstack_extras::repo::debian::ubuntu':
  release         => 'mitaka',
  repo            => 'proposed',
  package_require => true,
}

################
# OVSDPDK PART #
################
class { '::neutron::agents::ml2::ovs':
  enable_tunneling => true,
  tunnel_types     => ['vxlan', 'gre'],
  local_ip         => "${local_tunnel_ip}",
  firewall_driver  => 'neutron.agent.firewall.NoopFirewallDriver',
}

class { '::neutron::plugins::ml2':
  mechanism_drivers    => ['openvswitch'],
}

class {'::ovsdpdk':
  controller   => 'True',
}

####################
# ENV GENERAL PART #
####################

# Deploy MySQL Server
class { '::mysql::server':
  override_options => {
    mysqld => { bind-address   => "${controller_service_ip}",
    max_connections            => '1024',
    }
  },
  restart => true,
}

# Deploy RabbitMQ
class { '::rabbitmq':
  delete_guest_user => true,
  package_provider  => $package_provider,
}
rabbitmq_vhost { '/':
  provider => 'rabbitmqctl',
  require  => Class['rabbitmq'],
}
rabbitmq_user { ['keystone', 'neutron', 'nova', 'glance']:
  admin    => true,
  password => 'an_even_bigger_secret',
  provider => 'rabbitmqctl',
  require  => Class['rabbitmq'],
}
rabbitmq_user_permissions { ['keystone@/', 'neutron@/', 'nova@/', 'glance@/']:
  configure_permission => '.*',
  write_permission     => '.*',
  read_permission      => '.*',
  provider             => 'rabbitmqctl',
  require              => Class['rabbitmq'],
}

# deploy keystone

class { '::keystone::client': }

class { '::keystone::cron::token_flush': }

class { '::keystone::db::mysql':
  user     => 'keystone',
  password => 'keystone',
  host     => "${controller_service_ip}",
}

class { '::keystone':
  verbose             => true,
  debug               => true,
  database_connection => "mysql://keystone:keystone@${controller_service_ip}/keystone",
  admin_token         => 'admin_token',
  service_name        => 'httpd',
  public_endpoint     => "http://${controller_service_ip}:5000/",
  admin_endpoint      => "http://${controller_service_ip}:35357/",
  rabbit_userid       => 'keystone',
  rabbit_password     => 'an_even_bigger_secret',
}

include ::apache
class { '::keystone::wsgi::apache':
  ssl     => false,
  workers => 2,
}

class { '::keystone::roles::admin':
  email    => 'test@example.tld',
  password => 'a_big_secret',
}

class { '::keystone::endpoint':
  public_url     => "http://${controller_service_ip}:5000",
  internal_url   => "http://${controller_service_ip}:5000",
  admin_url      => "http://${controller_service_ip}:35357",
  default_domain => 'admin',
}

# deploy glance

class { '::glance::db::mysql':
  user     => 'glance',
  password => 'glance',
  host     => "${controller_service_ip}",
}

include ::glance
include ::glance::backend::file
include ::glance::client

class { '::glance::keystone::auth':
  auth_name    => 'glance',
  password     => 'a_big_secret',
  public_url   => "http://${controller_service_ip}:9292",
  admin_url    => "http://${controller_service_ip}:9292",
  internal_url => "http://${controller_service_ip}:9292",
}

class { '::glance::api':
  debug               => true,
  verbose             => true,
  database_connection => "mysql://glance:glance@${controller_service_ip}/glance?charset=utf8",
  keystone_password   => 'a_big_secret',
  workers             => 2,
}

class { '::glance::registry':
  debug               => true,
  verbose             => true,
  database_connection => "mysql://glance:glance@${controller_service_ip}/glance?charset=utf8",
  keystone_password   => 'a_big_secret',
  workers             => 2,
}

class { '::glance::notify::rabbitmq':
  rabbit_userid       => 'glance',
  rabbit_password     => 'an_even_bigger_secret',
  rabbit_host         => "${controller_service_ip}",
  notification_driver => 'messagingv2',
}

# deploy nova

class { '::nova::db::mysql':
  user     => 'nova',
  password => 'nova',
  host     => "${controller_service_ip}",
}

class { '::nova::db::mysql_api':
  user     => 'nova_api',
  password => 'nova_api',
  host     => "${controller_service_ip}",
}

class { '::nova::keystone::auth':
  auth_name        => 'nova',
  password         => 'a_big_secret',
  public_url       => "http://${controller_service_ip}:8774/v2/%(tenant_id)s",
  internal_url     => "http://${controller_service_ip}:8774/v2/%(tenant_id)s",
  admin_url        => "http://${controller_service_ip}:8774/v2/%(tenant_id)s",
  public_url_v3    => "http://${controller_service_ip}:8774/v3",
  internal_url_v3  => "http://${controller_service_ip}:8774/v3",
  admin_url_v3     => "http://${controller_service_ip}:8774/v3",
  ec2_public_url   => "http://${controller_service_ip}:8773/services/Cloud",
  ec2_internal_url => "http://${controller_service_ip}:8773/services/Cloud",
  ec2_admin_url    => "http://${controller_service_ip}:8773/services/Admin",

}

class { '::nova':
  database_connection     => "mysql://nova:nova@${controller_service_ip}/nova?charset=utf8",
  api_database_connection => "mysql://nova_api:nova_api@${controller_service_ip}/nova_api?charset=utf8",
  rabbit_host             => "${controller_service_ip}",
  rabbit_userid           => 'nova',
  rabbit_password         => 'an_even_bigger_secret',
  glance_api_servers      => "${controller_service_ip}:9292",
  verbose                 => true,
  debug                   => true,
  notification_driver     => 'messagingv2',
  notify_on_state_change  => 'vm_and_task_state',
}

class { '::nova::api':
  admin_password                       => 'a_big_secret',
  auth_uri                             => "http://${controller_service_ip}:5000/",
  identity_uri                         => "http://${controller_service_ip}:35357/",
  osapi_v3                             => true,
  neutron_metadata_proxy_shared_secret => 'a_big_secret',
  osapi_compute_workers                => 2,
  ec2_workers                          => 2,
  metadata_workers                     => 2,
  default_floating_pool                => 'public',
  sync_db_api                          => true,
}

class { '::nova::cert': }

class { '::nova::client': }

class { '::nova::conductor': }

class { '::nova::consoleauth': }

class { '::nova::cron::archive_deleted_rows': }

class { '::nova::scheduler': }

class { '::nova::vncproxy': }

class { '::nova::network::neutron':
  neutron_url            => "http://${controller_service_ip}:9696",
  neutron_admin_password => 'a_big_secret',
  neutron_admin_auth_url => "http://${controller_service_ip}:35357/v3",
}

# deploy neutron

class { '::neutron::db::mysql':
  user     => 'neutron',
  password => 'neutron',
  host     => "${controller_service_ip}",
}

class { '::neutron::keystone::auth':
  auth_name    => 'neutron',
  password     => 'a_big_secret',
  public_url   => "http://${controller_service_ip}:9696",
  admin_url    => "http://${controller_service_ip}:9696",
  internal_url => "http://${controller_service_ip}:9696",
}

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

class { '::neutron::server':
  database_connection => "mysql://neutron:neutron@${controller_service_ip}/neutron?charset=utf8",
  auth_password       => 'a_big_secret',
  identity_uri        => "http://${controller_service_ip}:35357/",
  sync_db             => true,
  api_workers         => 4,
}

class { '::neutron::agents::metadata':
  debug            => true,
  auth_password    => 'a_big_secret',
  shared_secret    => 'a_big_secret',
  auth_url         => "http://${controller_service_ip}:35357/v2.0",
  metadata_ip      => "${controller_service_ip}",
  metadata_workers => 2,
}

class { '::neutron::agents::lbaas':
  debug => true,
}

class { '::neutron::agents::l3':
  debug => true,
}

class { '::neutron::agents::dhcp':
  debug => true,
}

class { '::neutron::agents::metering':
  debug => true,
}

class { '::neutron::server::notifications':
  nova_url            => "http://${controller_service_ip}:8774/v2.0",
  password            => 'a_big_secret',
  auth_url            => "http://${controller_service_ip}:35357",
}

# deploy horizon

class { '::horizon':
  secret_key         => 'big_secret',
  keystone_url       => "http://${controller_service_ip}:5000/v2.0",
  servername         => $::hostname,
  allowed_hosts      => $::hostname,
  # need to disable offline compression due to
  # https://bugs.launchpad.net/ubuntu/+source/horizon/+bug/1424042
  compress_offline   => false,
}

neutron_network { 'public':
  tenant_name     => 'openstack',
  router_external => true,
}
Keystone_user_role['admin@openstack'] -> Neutron_network<||>

neutron_subnet { 'public-subnet':
  cidr             => '172.24.5.0/24',
  ip_version       => '4',
  allocation_pools => ['start=172.24.5.10,end=172.24.5.200'],
  gateway_ip       => '172.24.5.1',
  enable_dhcp      => false,
  network_name     => 'public',
  tenant_name      => 'openstack',
}

vs_bridge { 'br-ex':
  ensure => present,
  notify => Exec['create_br-ex_vif'],
}

# creates br-ex virtual interface to reach floating-ip network
exec { 'create_br-ex_vif':
  path        => '/usr/bin:/bin:/usr/sbin:/sbin',
  provider    => shell,
  command     => 'ip addr add 172.24.5.1/24 dev br-ex; ip link set br-ex up',
  refreshonly => true,
}
