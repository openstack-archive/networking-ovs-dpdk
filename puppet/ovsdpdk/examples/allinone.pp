#########################################################
# example of liberty deployment allinone environment    #
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

# Deploy MySQL Server
class { '::mysql::server':
  override_options => {
    mysqld => { bind-address   => '10.237.214.161',
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
  host     => '10.237.214.161'
}

class { '::keystone':
  verbose             => true,
  debug               => true,
  database_connection => 'mysql://keystone:keystone@10.237.214.161/keystone',
  admin_token         => 'admin_token',
  service_name        => 'httpd',
  public_endpoint     => 'http://10.237.214.161:5000/',
  admin_endpoint      => 'http://10.237.214.161:35357/',
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
  public_url     => 'http://10.237.214.161:5000',
  internal_url   => 'http://10.237.214.161:5000',
  admin_url      => 'http://10.237.214.161:35357',
  default_domain => 'admin',
}

# deploy glance

class { '::glance::db::mysql':
  user     => 'glance',
  password => 'glance',
  host     => '10.237.214.161',
}

include ::glance
include ::glance::backend::file
include ::glance::client

class { '::glance::keystone::auth':
  auth_name    => 'glance',
  password     => 'a_big_secret',
  public_url   => 'http://10.237.214.161:9292',
  admin_url    => 'http://10.237.214.161:9292',
  internal_url => 'http://10.237.214.161:9292',
}

class { '::glance::api':
  debug               => true,
  verbose             => true,
  database_connection => 'mysql://glance:glance@10.237.214.161/glance?charset=utf8',
  keystone_password   => 'a_big_secret',
  workers             => 2,
}

class { '::glance::registry':
  debug               => true,
  verbose             => true,
  database_connection => 'mysql://glance:glance@10.237.214.161/glance?charset=utf8',
  keystone_password   => 'a_big_secret',
  workers             => 2,
}

class { '::glance::notify::rabbitmq':
  rabbit_userid       => 'glance',
  rabbit_password     => 'an_even_bigger_secret',
  rabbit_host         => '10.237.214.161',
  notification_driver => 'messagingv2',
}

# deploy nova

class { '::nova::db::mysql':
  user     => 'nova',
  password => 'nova',
  host     => '10.237.214.161',
}

class { '::nova::keystone::auth':
  auth_name        => 'nova',
  password         => 'a_big_secret',
  public_url       => 'http://10.237.214.161:8774/v2/%(tenant_id)s',
  internal_url     => 'http://10.237.214.161:8774/v2/%(tenant_id)s',
  admin_url        => 'http://10.237.214.161:8774/v2/%(tenant_id)s',
  public_url_v3    => 'http://10.237.214.161:8774/v3',
  internal_url_v3  => 'http://10.237.214.161:8774/v3',
  admin_url_v3     => 'http://10.237.214.161:8774/v3',
  ec2_public_url   => 'http://10.237.214.161:8773/services/Cloud',
  ec2_internal_url => 'http://10.237.214.161:8773/services/Cloud',
  ec2_admin_url    => 'http://10.237.214.161:8773/services/Admin',

}

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
  vncserver_proxyclient_address => '10.237.214.161',
  instance_usage_audit          => true,
  instance_usage_audit_period   => 'hour',
}

class { '::nova::compute::libvirt':
  libvirt_virt_type => 'kvm',
  migration_support => true,
  vncserver_listen  => '0.0.0.0',
}

class { '::nova::api':
  admin_password                       => 'a_big_secret',
  auth_uri                             => 'http://10.237.214.161:5000/',
  identity_uri                         => 'http://10.237.214.161:35357/',
  osapi_v3                             => true,
  neutron_metadata_proxy_shared_secret => 'a_big_secret',
  osapi_compute_workers                => 2,
  ec2_workers                          => 2,
  metadata_workers                     => 2,
  default_floating_pool                => 'public',
}

class { '::nova::cert': }

class { '::nova::client': }

class { '::nova::conductor': }

class { '::nova::consoleauth': }

class { '::nova::cron::archive_deleted_rows': }

class { '::nova::scheduler': }

class { '::nova::vncproxy': }

class { '::nova::network::neutron':
  neutron_url            => 'http://10.237.214.161:9696',
  neutron_admin_password => 'a_big_secret',
  neutron_admin_auth_url => 'http://10.237.214.161:35357/v2.0',
}

# deploy neutron

class { '::neutron::db::mysql':
  user     => 'neutron',
  password => 'neutron',
  host     => '10.237.214.161',
}

class { '::neutron::keystone::auth':
  auth_name    => 'neutron',
  password     => 'a_big_secret',
  public_url   => 'http://10.237.214.161:9696',
  admin_url    => 'http://10.237.214.161:9696',
  internal_url => 'http://10.237.214.161:9696',
}

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

class { '::neutron::server':
  database_connection => 'mysql://neutron:neutron@10.237.214.161/neutron?charset=utf8',
  auth_password       => 'a_big_secret',
  identity_uri        => 'http://10.237.214.161:35357/',
  sync_db             => true,
  api_workers         => 4,
}

class { '::neutron::agents::ml2::ovs': }

class { '::neutron::agents::metadata':
  debug            => true,
  auth_password    => 'a_big_secret',
  shared_secret    => 'a_big_secret',
  auth_url         => 'http://10.237.214.161:35357/v2.0',
  metadata_ip      => '10.237.214.161',
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
  nova_url            => 'http://10.237.214.161:8774/v2',
  password            => 'a_big_secret',
  auth_url            => 'http://10.237.214.161:35357',
}

# deploy horizon

class { '::horizon':
  secret_key         => 'big_secret',
  keystone_url       => 'http://10.237.214.161:5000/v2.0',
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

################
# OVSDPDK PART #
################

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
    controller          => 'True',
}
