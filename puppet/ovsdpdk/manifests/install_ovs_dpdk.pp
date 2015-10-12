# == Class ovsdpdk::install_ovs_dpdk
#
# Installs ovs-dpdk service together with it's configuration file
# it also deploys qemu-kvm wrapper responsible for enabling some vhostforce
# options and setting huge pages into shared mode
#
class ovsdpdk::install_ovs_dpdk (
  $networking_ovs_dpdk_dir          = $::ovsdpdk::networking_ovs_dpdk_dir,
  $plugin_dir                       = $::ovsdpdk::params::plugin_dir,
) inherits ovsdpdk {
  require ovsdpdk::build_ovs_dpdk

  exec {'create_ovs_dpdk':
    command => "cp ${networking_ovs_dpdk_dir}/devstack/ovs-dpdk/ovs-dpdk-init /etc/init.d/ovs-dpdk;chmod +x /etc/init.d/ovs-dpdk",
    creates => '/etc/init.d/ovs-dpdk',
    user    => root,
    path    => ['/usr/bin','/bin'],
  }

  file {'/etc/default/ovs-dpdk': content => template("${plugin_dir}/files/ovs-dpdk-conf.erb"), mode => '0644' }

  exec {'adapt_conf_file':
    command => "${plugin_dir}/files/tune_params.sh",
    user    => root,
    require => File['/etc/default/ovs-dpdk'],
  }

  package {'qemu-kvm': ensure => installed }

  exec {'replace kvm binary':
    command => "cp ${plugin_dir}/files/kvm-wrapper.sh /usr/bin/kvm;chmod +x /usr/bin/kvm",
    path    => ['/usr/bin','/bin'],
    user    => root,
    onlyif  => 'test -f /usr/bin/kvm',
    require => Package['qemu-kvm'],
  }

  exec {'replace qemu-kvm binary':
    command => "cp ${plugin_dir}/files/kvm-wrapper.sh /usr/bin/qemu-kvm;chmod +x /usr/bin/qemu-kvm",
    path    => ['/usr/bin','/bin'],
    user    => root,
    onlyif  => 'test -f /usr/bin/qemu-kvm',
    require => Package['qemu-kvm'],
  }

  exec {'init ovs-dpdk':
    command => '/etc/init.d/ovs-dpdk init',
    user    => root,
    require => [ Exec['create_ovs_dpdk'], File['/etc/default/ovs-dpdk'] ],
  }

  service {'ovs-dpdk':
    ensure    => 'running',
    hasstatus => true,
    require   => Exec['init ovs-dpdk'],
  }

  # install mech driver
  exec {'install mech driver':
    command => 'python setup.py install',
    path    => ['/usr/bin','/bin'],
    cwd     => "${networking_ovs_dpdk_dir}",
    user    => root,
  }
}
