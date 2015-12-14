#!/usr/bin/env bash

for bridge in `sudo ovs-vsctl list-br`; do
  sudo ovs-vsctl --no-wait set Bridge $bridge datapath_type=$1;
done;
