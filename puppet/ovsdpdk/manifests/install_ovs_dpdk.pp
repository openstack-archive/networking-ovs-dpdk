# == Class ovsdpdk::install_ovs_dpdk
#
# Installs ovs-dpdk service together with it's configuration file
# it also deploys qemu-kvm wrapper responsible for enabling some vhostforce
# options and setting huge pages into shared mode
#
class ovsdpdk::install_ovs_dpdk (
  $networking_ovs_dpdk_dir = $::ovsdpdk::params::networking_ovs_dpdk_dir,
  $plugin_dir              = $::ovsdpdk::params::plugin_dir,
  $ovs_dir                 = $::ovsdpdk::params::ovs_dir,
  $openvswitch_service_src = $::ovsdpdk::params::openvswitch_service_src,
  $openvswitch_service_tgt = $::ovsdpdk::params::openvswitch_service_tgt,
  $qemu_kvm                = $::ovsdpdk::params::qemu_kvm,
  $compute                 = $::ovsdpdk::compute,

) inherits ovsdpdk {

  if $compute == 'True' {
    exec {'create_ovs_dpdk':
      command => "mv /etc/init.d/openvswitch-switch /tmp/openvswitch-switch.bak;\
                  cp ${networking_ovs_dpdk_dir}/devstack/ovs-dpdk/ovs-dpdk-init /etc/init.d/openvswitch-switch;\
                  chmod +x /etc/init.d/openvswitch-switch;\
                  ln -sf /etc/init.d/openvswitch-switch /etc/init.d/ovs-dpdk;\
                  cp /etc/openvswitch/conf.db /etc/openvswitch/conf.db.pre_dpdk",
    }

    file {'/etc/default/ovs-dpdk': content => template('ovsdpdk/ovs-dpdk-conf.erb'), mode => '0644' }

    exec {'adapt_conf_file':
      command   => "${plugin_dir}/files/tune_params.sh",
      require   => File['/etc/default/ovs-dpdk'],
    }

    exec { 'update ovs service':
      command => "cp ${plugin_dir}/files/${openvswitch_service_src} ${openvswitch_service_tgt}",
      onlyif  => "test -f ${openvswitch_service_tgt}",
    }

    if ($::operatingsystem == 'Ubuntu') and (versioncmp($::operatingsystemmajrelease, '16') <= 0) {
      # trusty or older
    } else {
      # systemd should be in place
      exec { 'systemctl daemon-reload':
        require => Exec['update ovs service'],
      }
    }

    # schema convert required as we are not removing original db
    exec { "ovsdb-tool convert /etc/openvswitch/conf.db ${ovs_dir}/vswitchd/vswitch.ovsschema":
      require   => Exec['create_ovs_dpdk'],
    }

    # backup and patch kvm wrapper for ovs-dpdk specific params
    exec { "cp ${qemu_kvm} ${qemu_kvm}.orig;cp ${plugin_dir}/files/kvm_wrapper ${qemu_kvm};chmod +x ${qemu_kvm}":
      onlyif => "test -f ${qemu_kvm}",
    }
  }
}
