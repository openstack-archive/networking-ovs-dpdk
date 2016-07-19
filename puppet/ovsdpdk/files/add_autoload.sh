#!/usr/bin/env bash

function uninstall_dpdk_modules {
    echo "Uninstall dpdk modules"

    if [ -e "/etc/modules-load.d" ]; then
        sudo rm -f /etc/modules-load-d/ovs-dpdk.conf
    elif [ -e "/etc/modules" ]; then
        sudo sed -i '/^# Following row added by ovsdpdk puppet module$/,+1 {d}' /etc/modules
    fi
}

# copying modules
sudo mkdir -p /lib/modules/$(uname -r)/extra/dpdk
for mod in $1/build/kmod/*.ko ; do
    sudo cp -f -v $mod /lib/modules/$(uname -r)/extra/dpdk/
done
sudo depmod -a

# getting proper module name
MODULE=$2
if [[ "$MODULE" == "vfio-pci" ]]; then
    MODULE="vfio_pci"
fi

uninstall_dpdk_modules
if [ -e "/etc/modules-load.d" ]; then
    echo -e "# This files is managed by puppet and can be rewritten when modified\n$MODULE" | sudo tee /etc/modules-load.d/ovs-dpdk.conf
elif [ -e "/etc/modules" ]; then
    echo -e "# Following row added by ovsdpdk puppet module\n$MODULE" | sudo tee -a /etc/modules
else
    echo "WARNING: Unable to detect type of module autoloading"
fi
