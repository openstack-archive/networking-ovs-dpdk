local xtrace=$(set +o | grep xtrace)
local error_on_clone=${ERROR_ON_CLONE}
if [ "$VERBOSE" == 'True' ]; then
    # enabling verbosity on whole plugin - default behavior
    set -o xtrace
fi

# disabling ERROR_NO_CLONE to allow this plugin work with devstack-gate
ERROR_ON_CLONE=False

    # Initial source of lib script
    source $NETWORKING_OVS_DPDK_DIR/devstack/libs/ovs-dpdk

    case $1 in
        "stack")
            case $2 in
                "pre-install")
                    # cloning source code
                    if [ $OVS_DPDK_INSTALL == 'True' ]; then
                        echo_summary "Downloading Dependencies for OVS DPDK"
                        clone_ovs_dpdk
                    else
                        echo_summary "Cloning of src files for ovs-dpdk not required"
                    fi
                ;;
                "install")
                    # Perform installation of ovs dpdk
                    if [ $OVS_DPDK_INSTALL == 'True' ]; then
                        echo_summary "Configuring, installing and starting OVS DPDK"
                        update_ovs_pmd_core_mask
                        install_ovs_dpdk
                        pushd $NETWORKING_OVS_DPDK_DIR
                        sudo python setup.py install
                        popd
                        start_ovs_dpdk
                    else
                        echo_summary "OVS_DPDK_INSTALL configured for not to install OVS DPDK"
                        echo_summary "Agent & ovsdpdk mechanism driver has to be built anyway"
                        pushd $NETWORKING_OVS_DPDK_DIR
                        sudo python setup.py install
                        popd
                    fi
                ;;
                "post-config")
                    set_vcpu_pin_set
                    if [ $OVS_DPDK_INSTALL == 'True' ]; then
                        iniset /$Q_PLUGIN_CONF_FILE ovs vhostuser_socket_dir $OVS_DB_SOCKET_DIR
                    fi
                    ovs_dpdk_configure_firewall_driver
                ;;
                "extra")
                    # no-op
                    # Multicast support.
                    configure_multicast
                    :
                ;;
            esac
        ;;
        "unstack")
            # Shut Down OVS-DPDK
            ovs_dpdk_db_cleanup
            stop_ovs_dpdk
            uninstall_libvirt_CentOS
        ;;
        "clean")
            # Remove state and transient data
            # Remember clean.sh first calls unstack.sh
            ovs_dpdk_clean
        ;;
    esac

ERROR_ON_CLONE=$error_on_clone
$xtrace
