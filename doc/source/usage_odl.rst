**Use with OpenDaylight**

To use this plugin with OpenDaylight you need Neutron and Networking-ODL plugin:

  https://github.com/openstack/networking-odl

In your local.conf you should enable following lines::

  enable_plugin networking-odl http://git.openstack.org/openstack/networking-odl master
  disable_service q-agt

Networking-OVS-DPDK plugin installs for you OVS-DPDK. As Networking-ODL plugin could
try to install legacy OVS one you should instruct him to skip that operation as following::
  SKIP_OVS_INSTALL=True

The ML2 driver to be used by Neutron has to be the one provided by Networking-ODL::
  Q_ML2_PLUGIN_MECHANISM_DRIVERS=opendaylight

To increase performances (processed packets per seconds) of tenents network interface
Networking-ODL will try to use 'vhostuser' VIF type when it is supported. To detect
if 'vhostuser' is supported Networking-ODL (running on control node) must be able
to translate the host name of compute nodes to their IP addresses on the management
network (the one used by OVS to connect to OpenDaylight).

To archive that you could edit file /etc/hosts on control node where neutron is running
adding all compute nodes where you want to use 'vhostuser', or configure to use
a DNS server you have configured to solve such address resolution.

