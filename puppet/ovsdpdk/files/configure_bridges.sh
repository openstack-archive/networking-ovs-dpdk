#!/usr/bin/env bash

# Configure integration bridge with proper datapath
sudo ovs-vsctl --no-wait -- --may-exist add-br br-int
if [ "$1" != "" ]; then
    sudo ovs-vsctl --no-wait set Bridge $bridge datapath_type=$1
fi
sudo ovs-vsctl --no-wait br-set-external-id br-int bridge-id br-int

# Configure external bridge with proper datapath
sudo ovs-vsctl --no-wait -- --may-exist add-br br-ex
if [ "$1" != "" ]; then
    sudo ovs-vsctl --no-wait set Bridge br-ex datapath_type=$1
fi
sudo ovs-vsctl --no-wait br-set-external-id br-ex bridge-id br-ex

