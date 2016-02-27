#!/usr/bin/env bash

set -x

# access openstack cli
source $1

sleep 10
neutron agent-list

# Force update of vswitch agents
for i in `neutron agent-list | grep "Open vSwitch agent" | awk {'print $2'}`; do
  neutron agent-update $i
done

sleep 10
neutron agent-list

# grep id and remove dead agent on all compute nodes
for i in `nova host-list | grep compute | awk {'print $2'}`; do
  dead_agent_id=`neutron agent-list | grep $i | grep xxx | grep "Open vSwitch agent" | awk {'print $2'}`
  neutron agent-delete $dead_agent_id
done

# Kept for operator to configure it afterwards
# modify flavors
#for i in `nova flavor-list | grep m1 | awk {'print $4'}`; do
#  nova flavor-key $i set "hw:mem_page_size=large"
#done

set +x
