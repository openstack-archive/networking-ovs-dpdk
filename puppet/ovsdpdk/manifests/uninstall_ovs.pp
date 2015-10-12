# == Class: ovsdpdk::uninstall_ovs
#
# Provides uninstallation of openvswitch package (if present) together with removing of kernel module
#
class ovsdpdk::uninstall_ovs () inherits ovsdpdk {

  case $::operatingsystem {
    'Ubuntu': {
      $remove_packages = [ 'openvswitch-switch', 'openvswitch-datapath-dkms', 'openvswitch-common' ]
      $install_packages = [ 'autoconf', 'libtool', 'libfuse-dev', 'screen' ]
    }
    'Fedora': {
      $remove_packages = [ 'openvswitch' ]
      $install_packages = [ 'pciutils', 'autoconf', 'libtool', 'fuse-devel', 'screen' ]
    }
    default: {
      $remove_packages = [ 'openvswitch' ]
      $install_packages = [ 'pciutils', 'autoconf', 'libtool', 'fuse-devel', 'screen' ]
    }
  }

  package { $remove_packages: ensure => 'purged' }

  package { $install_packages: ensure => 'installed' }

  package { "kernel-devel-${::kernelversion}":
    ensure          => 'installed',
    provider        => 'yum',
    install_options => '--showduplicates',
  }

  exec { '/sbin/modprobe -r openvswitch': onlyif => "/bin/grep -q '^openvswitch' '/proc/modules'" }
}

