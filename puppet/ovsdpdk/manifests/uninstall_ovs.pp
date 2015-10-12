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
    default: {
      $remove_packages = [ 'openvswitch' ]
      $install_packages = [ 'pciutils', 'autoconf', 'libtool', 'fuse-devel', 'screen' ]

      package { "kernel-devel-${::kernelversion}":
        ensure          => 'installed',
        provider        => 'yum',
        install_options => '--showduplicates',
      }
    }
  }

  package { $remove_packages: ensure => 'purged' }

  package { $install_packages: ensure => 'installed' }

  exec { '/sbin/modprobe -r openvswitch': onlyif => "/bin/grep -q '^openvswitch' '/proc/modules'" }
}

