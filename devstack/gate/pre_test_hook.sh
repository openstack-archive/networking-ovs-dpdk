#!/bin/bash

echo networking-ovs-dpdk pre-test-hook executed.

if type apt-get 2>&1 >/dev/null ; then
    sudo -EH apt-get update
    sudo -EH apt-get install -y libvirt-bin apparmor-utils automake
    sudo -EH aa-disable /usr/sbin/libvirtd
fi


cat <<EOF | sudo tee /opt/stack/new/devstack/local.sh
# creating an nfv flavor used in tempest
openstack flavor create --id 420 --ram 64 --disk 0 --vcpus 2 nfv-64-0-2
openstack flavor create --id 840 --ram 128 --disk 0 --vcpus 2 nfv-128-0-2
openstack flavor set --property hw:mem_page_size=large 420
openstack flavor set --property hw:mem_page_size=large 840

# TODO(sean-k-mooney): remove as numa cannot be tested upstream
# nova flavor-key 420 set "hw:numa_nodes=2"
# nova flavor-key 840 set "hw:numa_nodes=2"

# TODO(sean-k-mooney): enable to test cpu pinning later
# openstack flavor set --property hw:cpu_policy=dedicated 420
# openstack flavor set --property hw:cpu_policy=dedicated 840

EOF

sudo chmod +x /opt/stack/new/devstack/local.sh

# add PciPassthroughFilter,NUMATopologyFilter to default set of filters
source /opt/stack/new/devstack/lib/nova
cat << "EOF" | sudo tee /opt/stack/new/devstack/local.conf
[[post-config|\$NOVA_CONF]]
[DEFAULT]
firewall_driver=nova.virt.firewall.NoopFirewallDriver
scheduler_default_filters=$FILTERS,PciPassthroughFilter,NUMATopologyFilter
}}

[[test-config|/opt/stack/new/tempest/etc/tempest.conf]]
[compute]
flavor_ref=420
flavor_ref_alt=840

[compute-feature-enabled]
interface_attach=False

EOF
