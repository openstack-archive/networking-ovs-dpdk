# == Class: ovsdpdk::uninstall_ovs
#
# Provides uninstallation of openvswitch package (if present) together with removing of kernel module
#
class ovsdpdk::uninstall_ovs (
  $openvswitch_service_name = $::ovsdpdk::params::openvswitch_service_name,
  $openvswitch_agent        = $::ovsdpdk::params::openvswitch_agent,
  $install_packages         = $::ovsdpdk::params::install_packages,
  $openvswitch_agent        = $::ovsdpdk::params::openvswitch_agent,
) inherits ovsdpdk {

  #Due to dependencies to other packages, we won't purge vanilla OVS  
  #package { $remove_packages: ensure => 'purged' }

  exec { "/usr/sbin/service ${openvswitch_service_name} stop":
    user => root,
  }

  exec { "/usr/sbin/service ${openvswitch_agent} stop":
    user => root,
  }

  exec { '/usr/sbin/service neutron-server stop':
    user => root,
  }

  package { $install_packages: ensure => 'installed' }

  exec { '/sbin/modprobe -r openvswitch':
    onlyif  => "/bin/grep -q '^openvswitch' '/proc/modules'",
    user    => root,
    require => Exec["/usr/sbin/service ${openvswitch_agent} stop"],
  }

}

