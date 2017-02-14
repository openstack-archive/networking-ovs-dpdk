#!/bin/bash

echo networking-ovs-dpdk pre-test-hook executed.

if type apt-get 2>&1 >/dev/null ; then
    sudo apt-get install -y libvirt-bin apparmor-utils
    sudo aa-disable /usr/sbin/libvirtd
fi


cat <<EOF | sudo tee /opt/stack/new/devstack/local.sh
# creating an nfv flavor used in tempest
nova flavor-create nfv-64-0-2 420 64 0 2
nova flavor-create nfv-128-0-2 840 128 0 2
nova flavor-key 420 set "hw:mem_page_size=large"
nova flavor-key 840 set "hw:mem_page_size=large"
# TODO(sean-k-mooney): remove as numa cannot be tested upstream
# nova flavor-key 420 set "hw:numa_nodes=2"
# nova flavor-key 840 set "hw:numa_nodes=2"

# TODO(sean-k-mooney): enable to test cpu pinning later
#nova flavor-key 420 set "hw:cpu_policy=dedicated"
#nova flavor-key 840 set "hw:cpu_policy=dedicated"

# setting tempest to use newly created flavors
source /opt/stack/new/devstack/functions
iniset /opt/stack/new/tempest/etc/tempest.conf compute flavor_ref 420
iniset /opt/stack/new/tempest/etc/tempest.conf compute flavor_ref_alt 840

# TODO(sean-k-mooney) investigate why this is needed as it works manually.
echo "Setting interface_attach = False in tempest config as it's not supported in ovs-dpdk"
echo "This skips relevant tempest tests"
iniset /opt/stack/new/tempest/etc/tempest.conf compute-feature-enabled interface_attach False
EOF

sudo chmod +x /opt/stack/new/devstack/local.sh

# add PciPassthroughFilter,NUMATopologyFilter to default set of filters
source /opt/stack/new/devstack/lib/nova
cat <<EOF | sudo tee /opt/stack/new/devstack/local.conf
[[post-config|\$NOVA_CONF]]
[DEFAULT]
firewall_driver=nova.virt.firewall.NoopFirewallDriver
scheduler_default_filters=$FILTERS,PciPassthroughFilter,NUMATopologyFilter
}}

