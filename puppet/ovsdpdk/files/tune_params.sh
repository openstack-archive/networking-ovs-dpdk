#!/usr/bin/env  bash

# It adapts /etc/default/ovs-dpdk file
# generated mainly from devstack/libs/ovs-dpdk
# it will modify / tune variables, which are not configured directly

source /etc/default/ovs-dpdk

if [ $OVS_SOCKET_MEM == "auto" ] ; then
    for d in /sys/devices/system/node/node? ; do
        if [ $OVS_SOCKET_MEM == "auto" ]; then
                OVS_SOCKET_MEM=2048
        else
                OVS_SOCKET_MEM=$OVS_SOCKET_MEM,2048
        fi
    done
fi

sudo sed "s#OVS_SOCKET_MEM=.*#OVS_SOCKET_MEM=$OVS_SOCKET_MEM#" -i /etc/default/ovs-dpdk

# Creates an array of pci addres to interface names delimeted by # e.g. <pci_address>#<interface name>
PAIRS=( `ls -al /sys/class/net/* | grep pci | rev | awk '{print $1;}' | cut -d '/' -f 1,3 | rev |  sed s'/\//#/'` )
# Populates OVS_BRIDGE_MAPPINGS if $PHYSICAL_NETWORK and $OVS_PHYSICAL_BRIDGE are used instead.
if [[ "$OVS_DATAPATH_TYPE" != "" ]] && [[ "$OVS_BRIDGE_MAPPINGS" = "" ]] && [[ "$PHYSICAL_NETWORK" != "" ]] && [[ "$OVS_PHYSICAL_BRIDGE" != "" ]]; then
    OVS_BRIDGE_MAPPINGS=$PHYSICAL_NETWORK:$OVS_PHYSICAL_BRIDGE
fi

if [[ -z "$OVS_DPDK_PORT_MAPPINGS" ]]; then
    OVS_BRIDGES=${OVS_BRIDGE_MAPPINGS//,/ }
    ARRAY=( $OVS_BRIDGES )
    for net in "${ARRAY[@]}"; do
        bridge="${net##*:}"
        nic=${bridge/br-/}
        if [[ -z "$OVS_DPDK_PORT_MAPPINGS" ]]; then
            OVS_DPDK_PORT_MAPPINGS=$nic:$bridge
        else
            OVS_DPDK_PORT_MAPPINGS=$OVS_DPDK_PORT_MAPPINGS,$nic:$bridge
        fi
    done
fi

MAPPINGS=${OVS_DPDK_PORT_MAPPINGS//,/ }

ARRAY=( $MAPPINGS )
NICS=""
for net in "${ARRAY[@]}"; do
    nic="${net%%:*}"
    bridge="${net##*:}"
    printf "%s in %s\n" "$KEY" "$VALUE"
    for pair in "${PAIRS[@]}"; do
        if [[ $nic == `echo $pair | cut -f 2 -d "#"` ]]; then
            if [[ $NICS == "" ]]; then
                NICS=$pair
            else
                NICS=$NICS,$pair
            fi
        fi
    done
done
sudo sed "s/OVS_PCI_MAPPINGS=.*/OVS_PCI_MAPPINGS=$NICS/" -i /etc/default/ovs-dpdk
sudo sed "s/OVS_BRIDGE_MAPPINGS=.*/OVS_BRIDGE_MAPPINGS=$OVS_BRIDGE_MAPPINGS/" -i /etc/default/ovs-dpdk
sudo sed "s/OVS_DPDK_PORT_MAPPINGS=.*/OVS_DPDK_PORT_MAPPINGS=$OVS_DPDK_PORT_MAPPINGS/" -i /etc/default/ovs-dpdk

OVS_PMD_CORE_MASK=$(echo $OVS_PMD_CORE_MASK | sed 's/^0x//')

if [ $OVS_PMD_CORE_MASK -eq 4 ]; then
    #default value, check for siblings in case of hyperthreading enabled
    SIBLINGS=""
    RESULT=0
    FILE="/sys/devices/system/cpu/cpu3/topology/thread_siblings_list"
    if [ -e $FILE ]; then
        SIBLINGS=`cat $FILE`
    else
        echo "warning: don't know how to check siblings"
        SIBLINGS=3
    fi

    for SIBLING in $(echo $SIBLINGS | sed -n 1'p' | tr ',' '\n'); do
        SIBLING_CORE=`echo "obase=10;$((1<<($SIBLING-1)))" | bc`
        RESULT=$(($RESULT | $SIBLING_CORE))
    done

    OVS_PMD_CORE_MASK=`printf "%x" $RESULT`
fi

sudo sed "s#OVS_PMD_CORE_MASK=.*#OVS_PMD_CORE_MASK=$OVS_PMD_CORE_MASK#" -i /etc/default/ovs-dpdk
