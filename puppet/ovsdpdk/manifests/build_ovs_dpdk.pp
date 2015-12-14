# == Class: ovsdpdk::build_ovs_dpdk
#
# It executes build of OVS with DPDK support from configured shell script
#
class ovsdpdk::build_ovs_dpdk (
  $plugin_dir =  $::ovsdpdk::params::plugin_dir,
) inherits ovsdpdk {
  require ovsdpdk::uninstall_ovs

  file {"${plugin_dir}/files/build_ovs_dpdk.sh":
      content => template("${plugin_dir}/files/build_ovs_dpdk.erb"),
      mode    => '0775',
  }

  exec {"${plugin_dir}/files/build_ovs_dpdk.sh":
      require => File["${plugin_dir}/files/build_ovs_dpdk.sh"],
      timeout => 0,
  }
}

