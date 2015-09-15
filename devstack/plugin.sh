xtrace=$(set +o | grep xtrace)
set +o xtrace
set -x

    # Initial source of lib script
    source $NETWOKING_OVS_DPDK_DIR/devstack/libs/ovs-dpdk

    case $1 in
        "stack")
            case $2 in
                "pre-install")
                    # cloning source code
                    echo_summary "Downloading Dependencies for OVS DPDK"
                    clone_ovs_dpdk
                ;;
                "install")
                    # Perform installation of ovs dpdk
                    echo_summary "Configuring, installing and starting OVS DPDK"
                    update_ovs_pmd_core_mask
                    install_ovs_dpdk
                    pushd $NETWOKING_OVS_DPDK_DIR
                    sudo python setup.py install
                    popd
                    start_ovs_dpdk
                ;;
                "post-config")
                    set_vcpu_pin_set
                ;;
                "extra")
                    # no-op
                    :
                ;;
            esac
        ;;
        "unstack")
            # Shut Down OVS-DPDK
            ovs_dpdk_db_cleanup
            stop_ovs_dpdk
            uninstall_libvirt_CentOS
            rm -f $TOP_DIR/lib/neutron_plugins/ovsdpdk_agent
        ;;
        "clean")
            # Remove state and transient data
            # Remember clean.sh first calls unstack.sh
            ovs_dpdk_clean
        ;;
    esac

set +x
$xtrace
