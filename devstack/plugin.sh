local xtrace=$(set +o | grep xtrace)
set +o xtrace
set -x

    # Initial source of lib script
    source $NETWOKING_OVS_DPDK_DIR/devstack/libs/ovs-dpdk

    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        # Set up system services
        echo_summary "Downloading Dependencies"
        clone_ovs_dpdk
    if [ ! -d $DEST/neutron ]; then
        git_clone $NEUTRON_REPO $NEUTRON_DIR $NEUTRON_BRANCH
    fi

    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of ovs dpdk
        echo_summary "Installing OVS DPDK"
        ovs_dpdk_db_cleanup
        install_ovs_dpdk
        local oldDIR=`pwd`
        cd $NETWOKING_OVS_DPDK_DIR
        sudo python setup.py install
        cd $oldDIR

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Start ovs-dpdk before l2 service start
        echo_summary "Starting OVS DPDK"
        start_ovs_dpdk

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # No-op
        :
    fi

    if [[ "$1" == "unstack" ]]; then
        # Shut Down OVS-DPDK
        ovs_dpdk_db_cleanup
        stop_ovs_dpdk
        rm -f $TOP_DIR/lib/neutron_plugins/ovsdpdk_agent
    fi

    if [[ "$1" == "clean" ]]; then
        # Remove state and transient data
        # Remember clean.sh first calls unstack.sh
        ovs_dpdk_clean
    fi

set +x
$xtrace
