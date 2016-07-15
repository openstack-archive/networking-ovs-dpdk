# == Class: ovsdpdk::prepare
#
# Responsible for downloading all relevant git repos for setting up of OVS+DPDK
#
class ovsdpdk::prepare(
  $dest                     = $::ovsdpdk::params::dest,
  $ovs_dir                  = $::ovsdpdk::params::ovs_dir,
  $ovs_dpdk_dir             = $::ovsdpdk::params::ovs_dpdk_dir,
  $networking_ovs_dpdk_dir  = $::ovsdpdk::params::networking_ovs_dpdk_dir,
  $ovs_git_tag              = $::ovsdpdk::params::ovs_git_tag,
  $ovs_dpdk_git_tag         = $::ovsdpdk::params::ovs_dpdk_git_tag,
  $ovs_plugin_git_tag       = $::ovsdpdk::params::ovs_plugin_git_tag,
  $openvswitch_service_name = $::ovsdpdk::params::openvswitch_service_name,
  #$openvswitch_agent        = $::ovsdpdk::params::openvswitch_agent,
  $install_packages         = $::ovsdpdk::params::install_packages,
  $compute                  = $::ovsdpdk::compute,
  $controller               = $::ovsdpdk::controller,
) inherits ovsdpdk {

  # vswtich::ovs is taking care for installation of vanilla ovs
  # we are builing our code on top of it and need to ensure
  # that it's not rewritten afterwards
  #require ::vswitch::ovs
  require ::neutron::agents::ml2::ovs


  file { $dest:
    ensure => directory,
    mode   => '0755',
  }

  package { $install_packages:  ensure   => installed  }

  if $compute == 'True' {
    vcsrepo { $networking_ovs_dpdk_dir:
      ensure   => present,
      provider => git,
      require  => Package[$install_packages],
      source   => 'https://github.com/openstack/networking-ovs-dpdk',
      revision => $ovs_plugin_git_tag,
    }

    vcsrepo { $ovs_dir:
      ensure   => present,
      provider => git,
      require  => Package[$install_packages],
      source   => 'https://github.com/openvswitch/ovs.git',
      revision => $ovs_git_tag,
    }

    vcsrepo { $ovs_dpdk_dir:
      ensure   => present,
      provider => git,
      require  => Package[$install_packages],
      source   => 'http://dpdk.org/git/dpdk',
      revision => $ovs_dpdk_git_tag,
    }

    #exec { "/usr/sbin/service ${openvswitch_agent} stop": }
    exec { "/usr/sbin/service ${openvswitch_service_name} stop": } 
  }

  if $controller == 'True' {
    exec { '/usr/sbin/service neutron-server stop': }
  }

  if ($compute != "True") and ($controller != "True") {
    warning('Not running on controller or compute !?')
  }
}
