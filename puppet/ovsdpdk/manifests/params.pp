#
# This class contains the platform differences for ovsdpdk
# and environment not commonly configured stuff
#
class ovsdpdk::params {

  case $::operatingsystem {
    'Ubuntu': {
      $qemu_kvm = '/usr/bin/kvm'
      $install_packages = [ 'git', 'screen', 'patch', 'autoconf', 'libtool', 'bc',
                            'python-dev', 'python-pip', 'qemu-kvm' ]
      $nova_compute_service_name = 'nova-compute'
      $nova_scheduler_service_name = 'nova-scheduler'

      $openvswitch_service_name = 'openvswitch-switch'
      if (versioncmp($::operatingsystemmajrelease, '16') >=) {
        # xenial and later - systemd handling
        $openvswitch_service_src = 'openvswitch_systemd'
        $openvswitch_service_tgt = '/lib/systemd/system/openvswitch-switch.service'
      } else {
        # trusty or below - upstart handling
        $openvswitch_service_src = 'openvswitch_upstart'
        $openvswitch_service_tgt = '/etc/init/openvswitch-switch.conf'
      }
    }
    'CentOS': {
      $qemu_kvm = '/usr/libexec/qemu-kvm'
      $install_packages = [ 'git', 'screen', 'patch', 'pciutils', 'autoconf', 'libtool', 'bc',
                            'python-devel', 'python-pip', 'qemu-kvm', 'kernel-devel' ]
      $nova_compute_service_name = 'openstack-nova-compute'
      $nova_scheduler_service_name = 'openstack-nova-scheduler'

      # systemd handling only
      $openvswitch_service_name = 'openvswitch'
      $openvswitch_service_src  = 'openvswitch_systemd'
      $openvswitch_service_tgt  = '/usr/lib/systemd/system/openvswitch.service'

    }
    default: {
      fail("Unsupported os ${::operatingsystem}")
    }
  }

  $ovs_db_conf_dir          = '/etc/openvswitch'
  $ovs_db_socket_dir        = '/var/run/openvswitch'
  $ovs_db_socket            = "${ovs_db_socket_dir}/db.sock"
  $ovs_db_conf              = "${ovs_db_conf_dir}/conf.db"

  # General config
  $plugin_dir               = '/etc/puppet/modules/ovsdpdk'
  $dest                     = '/opt/code'
  $nova_conf_dir            = '/etc/nova'
  $nova_conf                = "${nova_conf_dir}/nova.conf"

  # OVS config
  $ovs_install_dir          = '/usr'
  $ovs_git_repo             = 'https://github.com/openvswitch/ovs.git'
  $ovs_git_tag              = 'ace39a6f63d4c28344ca0e2a2c4233ddbc16b07c'
  $ovs_dir                  = "${dest}/ovs"

  # DPDK config
  $ovs_dpdk_git_repo        = 'http://dpdk.org/git/dpdk'
  $ovs_dpdk_git_tag         = 'v16.04'
  $ovs_dpdk_dir             = "${dest}/DPDK-${ovs_dpdk_git_tag}"

  # PLUGIN config
  $networking_ovs_dpdk_dir  = "${dest}/networking-ovs-dpdk"
  $ovs_plugin_git_tag       = 'master'

}
