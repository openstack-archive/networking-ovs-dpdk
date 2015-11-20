#!/usr/bin/env bash

# Short script for uninstallation of OVS with DPDK

# enable debugging:
#set -o xtrace

# Stopping service if needed
echo "[debug] stopping ovs-dpdk (if needed)"
sudo service ovs-dpdk status 2>&1 1>/dev/null
res=$?

if [ $res -eq 2 ]; then
    echo "[warning] service ovs-dpdk is already stopped"
else
    echo "[debug] stopping ovs-dpdk service"
    sudo service ovs-dpdk stop 2>&1 1>/dev/null
fi

# Remove  ovs-dpdk service
echo "[debug] removing ovs-dpdk service"
sudo rm -f /etc/default/ovs-dpdk
sudo rm -f /etc/init.d/ovs-dpdk

# kvm wrapper
echo "[debug] replacing kvm wrapper"
if [ -e /usr/bin/kvm ]; then
    KVM_CMD="/usr/bin/kvm"
elif [ -e /usr/bin/qemu-kvm ]; then
    KVM_CMD="/usr/bin/qemu-kvm"
elif [ -e /usr/libexec/qemu-kvm ]; then
    KVM_CMD="/usr/libexec/qemu-kvm"
else
    echo "[warning] package qemu-kvm probably not installed"
fi

cat << 'EOF' | sudo tee  $KVM_CMD
#!/bin/sh

exec /usr/bin/qemu-system-x86_64  "${args[@]}"
EOF


# remove git repos
echo "[warning] git repos were not automatically removed, you can remove it once you're finished with them"
