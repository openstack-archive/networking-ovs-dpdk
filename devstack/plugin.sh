local xtrace=$(set +o | grep xtrace)
set +o xtrace
set -x

    # Initial source of lib script
    source $NETWOKING_OVS_DPDK_DIR/devstack/libs/ovs-dpdk

    case $1 in
        "stack")
            case $2 in
                "pre-install")
                    # Set up system services
                    echo_summary "Downloading Dependencies"
                    clone_ovs_dpdk
                ;;
                "install")
                    # Perform installation of ovs dpdk
                    echo_summary "Installing OVS DPDK"
                    ovs_dpdk_db_cleanup
                    install_ovs_dpdk
                    pushd $NETWOKING_OVS_DPDK_DIR
                    sudo python setup.py install
                    popd
                ;;
                "post-config")
                    # Start ovs-dpdk before l2 service start
                    echo_summary "Starting OVS DPDK"
                    start_ovs_dpdk
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
