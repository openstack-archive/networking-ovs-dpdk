#!/usr/bin/env  bash

# Small script for calculation of cores not suitable for deployment
# of VM's and adaptation of nova.conf accordingly
# nova.conf path should come as first param
# this should be executed when nova is enabled and already configured

source /etc/default/ovs-dpdk

OVS_CORE_MASK=$(echo $OVS_CORE_MASK | sed 's/^0x//')
OVS_PMD_CORE_MASK=$(echo $OVS_PMD_CORE_MASK | sed 's/^0x//')
BAD_CORES=$((`echo $((16#${OVS_CORE_MASK}))` | `echo $((16#${OVS_PMD_CORE_MASK}))`))
TOTAL_CORES=`nproc`
vcpu_pin_set=""

for cpu in $(seq 0 `expr $TOTAL_CORES - 1`);do
    tmp=`echo 2^$cpu | bc`
    if [ $(($tmp & $BAD_CORES)) -eq 0 ]; then
        vcpu_pin_set+=$cpu","
    fi
done
vcpu_pin_set=${vcpu_pin_set::-1}

crudini --set $1 DEFAULT vcpu_pin_set $vcpu_pin_set
