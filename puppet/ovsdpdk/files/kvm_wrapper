#!/usr/bin/env bash
VIRTIO_OPTIONS="csum=off,gso=off,guest_tso4=off,guest_tso6=off,guest_ecn=off"
VHOST_FORCE="vhostforce"
SHARE="share=on"
add_mem=False
i=0
while [ $# -gt 0 ]; do
     case "$1" in

     -device)
        args[i]="$1"
        (( i++ ))
        shift
        if [[ $1 =~ "vhost-user" ]]
        then
                args[i]=${1},${VHOST_FORCE}
                (( i++))
                shift

        fi
        ;;
    -object)
        args[i]="$1"
        (( i++ ))
        shift
        if [[ $1 =~ "memory-backend-file" ]]
        then
                args[i]=${1},${SHARE}
                (( i++))
                shift

        fi
        ;;

     *)
         args[i]="$1"
         (( i++ ))
         shift ;;
     esac
done
echo "qemu ${args[@]}"  > /tmp/qemu.orig
if [ -e /usr/bin/qemu-system-x86_64 ]; then
    exec /usr/bin/qemu-system-x86_64  "${args[@]}"
elif [ -e /usr/libexec/qemu-kvm.orig ]; then
    exec /usr/libexec/qemu-kvm.orig  "${args[@]}"
fi
