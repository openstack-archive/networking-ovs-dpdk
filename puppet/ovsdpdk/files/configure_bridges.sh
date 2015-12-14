#!/usr/bin/env bash

# Configure integration bridge with specified datapath
sudo ovs-vsctl --no-wait -- --may-exist add-br br-int
if [ "$1" != "" ]; then
    sudo ovs-vsctl --no-wait set Bridge br-int datapath_type=$1
fi
sudo ovs-vsctl --no-wait br-set-external-id br-int bridge-id br-int

# Configure external bridge with specified datapath
sudo ovs-vsctl --no-wait -- --may-exist add-br br-ex
if [ "$1" != "" ]; then
    sudo ovs-vsctl --no-wait set Bridge br-ex datapath_type=$1
fi
sudo ovs-vsctl --no-wait br-set-external-id br-ex bridge-id br-ex

# Configure br-tun bridge with specified datapath
sudo ovs-vsctl --no-wait -- --may-exist add-br br-tun
if [ "$1" != "" ]; then
    sudo ovs-vsctl --no-wait set Bridge br-tun datapath_type=$1
fi
sudo ovs-vsctl --no-wait br-set-external-id br-tun bridge-id br-tun

