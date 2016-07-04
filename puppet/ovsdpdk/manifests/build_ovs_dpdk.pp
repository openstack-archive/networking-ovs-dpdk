# == Class: ovsdpdk::build_ovs_dpdk
#
# It executes build of OVS with DPDK support from configured shell script
#
class ovsdpdk::build_ovs_dpdk (
  $plugin_dir =  $::ovsdpdk::params::plugin_dir,
  $compute    =  $::ovsdpdk::compute,
) inherits ovsdpdk {

  if $compute == 'True' {
    file {"${plugin_dir}/files/patches.sh":
        content => template('ovsdpdk/patches.erb'),
        mode    => '0775',
    }

    exec {"${plugin_dir}/files/patches.sh":
        require   => File["${plugin_dir}/files/patches.sh"],
        timeout   => 0,
        logoutput => true,
    }

    file {"${plugin_dir}/files/build_ovs_dpdk.sh":
        require => Exec["${plugin_dir}/files/patches.sh"],
        content => template('ovsdpdk/build_ovs_dpdk.erb'),
        mode    => '0775',
    }

    exec {"${plugin_dir}/files/build_ovs_dpdk.sh":
        require   => File["${plugin_dir}/files/build_ovs_dpdk.sh"],
        timeout   => 0,
        logoutput => 'on_failure',
    }
  }
  else {
    info('ovsdpdk build not triggered, compute node not specified')
  }
}

