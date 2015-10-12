# == Class: ovsdpdk::clone
#
# Responsible for downloading all relevant git repos for setting up of OVS+DPDK
#
class ovsdpdk::clone(
  $dest                    = $::ovsdpdk::params::dest,
  $ovs_dir                 = $::ovsdpdk::params::ovs_dir,
  $ovs_dpdk_dir            = $::ovsdpdk::params::ovs_dpdk_dir,
  $networking_ovs_dpdk_dir = $::ovsdpdk::params::networking_ovs_dpdk_dir,
  $ovs_git_tag             = $::ovsdpdk::params::ovs_git_tag,
  $ovs_dpdk_git_tag        = $::ovsdpdk::params::ovs_dpdk_git_tag,
  $ovs_plugin_git_tag      = $::ovsdpdk::params::ovs_plugin_git_tag,
) inherits ovsdpdk {

  file { $dest:
    ensure => directory,
    mode   => '0755',
  }

  package { 'git':
    ensure   => installed,
  }
    
  vcsrepo { $ovs_dir:
    ensure   => present,
    provider => git,
    require  => [ Package['git'] ],
    source   => 'https://github.com/openvswitch/ovs.git',
    revision => $ovs_git_tag,
  }

  vcsrepo { $ovs_dpdk_dir:
    ensure   => present,
    provider => git,
    require  => [ Package['git'] ],
    source   => 'http://dpdk.org/git/dpdk',
    revision => $ovs_dpdk_git_tag,
  }

  vcsrepo { $networking_ovs_dpdk_dir:
    ensure   => present,
    provider => git,
    require  => [ Package['git'] ],
    source   => 'https://github.com/stackforge/networking-ovs-dpdk',
    revision => $ovs_plugin_git_tag,
  }
}
