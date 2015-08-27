# Copyright 2011 VMware, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import sys

from oslo_config import cfg
from oslo_log import log as logging

from networking_ovs_dpdk.common import constants
from neutron.common import constants as n_const
from neutron.i18n import _LE
from neutron.plugins.ml2.drivers.openvswitch.agent import ovs_neutron_agent

LOG = logging.getLogger(__name__)
cfg.CONF.import_group('AGENT', 'neutron.plugins.ml2.drivers.openvswitch.'
                      'agent.common.config')
cfg.CONF.import_group('OVS', 'neutron.plugins.ml2.drivers.openvswitch.agent.'
                      'common.config')

# passthrough module classes and constants.
DEAD_VLAN_TAG = ovs_neutron_agent.DEAD_VLAN_TAG
UINT64_BITMASK = ovs_neutron_agent.UINT64_BITMASK
DeviceListRetrievalError = ovs_neutron_agent.DeviceListRetrievalError
LocalVLANMapping = ovs_neutron_agent.LocalVLANMapping
OVSPluginApi = ovs_neutron_agent.OVSPluginApi
create_agent_config_map = ovs_neutron_agent.create_agent_config_map
validate_local_ip = ovs_neutron_agent.validate_local_ip
prepare_xen_compute = ovs_neutron_agent.prepare_xen_compute


class OVSDPDKNeutronAgent(ovs_neutron_agent.OVSNeutronAgent):
    '''Implements OVS-based tunneling, VLANs and flat networks.

    Two local bridges are created: an integration bridge (defaults to
    'br-int') and a tunneling bridge (defaults to 'br-tun'). An
    additional bridge is created for each physical network interface
    used for VLANs and/or flat networks.

    All VM VIFs are plugged into the integration bridge. VM VIFs on a
    given virtual network share a common "local" VLAN (i.e. not
    propagated externally). The VLAN id of this local VLAN is mapped
    to the physical networking details realizing that virtual network.

    For virtual networks realized as GRE tunnels, a Logical Switch
    (LS) identifier is used to differentiate tenant traffic on
    inter-HV tunnels. A mesh of tunnels is created to other
    Hypervisors in the cloud. These tunnels originate and terminate on
    the tunneling bridge of each hypervisor. Port patching is done to
    connect local VLANs on the integration bridge to inter-hypervisor
    tunnels on the tunnel bridge.

    For each virtual network realized as a VLAN or flat network, a
    veth or a pair of patch ports is used to connect the local VLAN on
    the integration bridge with the physical network bridge, with flow
    rules adding, modifying, or stripping VLAN tags as necessary.
    '''

    def __init__(self, bridge_classes, integ_br, tun_br, local_ip,
                 bridge_mappings, polling_interval, tunnel_types=None,
                 veth_mtu=None, l2_population=False,
                 enable_distributed_routing=False,
                 minimize_polling=False,
                 ovsdb_monitor_respawn_interval=(
                     constants.DEFAULT_OVSDBMON_RESPAWN),
                 arp_responder=False,
                 prevent_arp_spoofing=True,
                 use_veth_interconnection=False,
                 quitting_rpc_timeout=None,
                 conf=None):
        '''Constructor.
        :param bridge_classes: a dict for bridge classes.
        :param integ_br: name of the integration bridge.
        :param tun_br: name of the tunnel bridge.
        :param local_ip: local IP address of this hypervisor.
        :param bridge_mappings: mappings from physical network name to bridge.
        :param polling_interval: interval (secs) to poll DB.
        :param tunnel_types: A list of tunnel types to enable support for in
               the agent. If set, will automatically set enable_tunneling to
               True.
        :param veth_mtu: MTU size for veth interfaces.
        :param l2_population: Optional, whether L2 population is turned on
        :param minimize_polling: Optional, whether to minimize polling by
               monitoring ovsdb for interface changes.
        :param ovsdb_monitor_respawn_interval: Optional, when using polling
               minimization, the number of seconds to wait before respawning
               the ovsdb monitor.
        :param arp_responder: Optional, enable local ARP responder if it is
               supported.
        :param prevent_arp_spoofing: Optional, enable suppression of any ARP
               responses from ports that don't match an IP address that belongs
               to the ports. Spoofing rules will not be added to ports that
               have port security disabled.
        :param use_veth_interconnection: use veths instead of patch ports to
               interconnect the integration bridge to physical bridges.
        :param quitting_rpc_timeout: timeout in seconds for rpc calls after
               SIGTERM is received
        :param conf: an instance of ConfigOpts
        '''
        super(OVSDPDKNeutronAgent, self).__init__(
            bridge_classes, integ_br, tun_br, local_ip,
            bridge_mappings, polling_interval,
            tunnel_types=tunnel_types,
            veth_mtu=veth_mtu, l2_population=l2_population,
            enable_distributed_routing=enable_distributed_routing,
            minimize_polling=minimize_polling,
            ovsdb_monitor_respawn_interval=(
                ovsdb_monitor_respawn_interval),
            arp_responder=arp_responder,
            prevent_arp_spoofing=prevent_arp_spoofing,
            use_veth_interconnection=use_veth_interconnection,
            quitting_rpc_timeout=quitting_rpc_timeout,
            conf=conf)
        self.agent_state = {
            'binary': 'networking-ovs-dpdk-agent',
            'host': self.conf.host,
            'topic': n_const.L2_AGENT_TOPIC,
            'configurations': {'bridge_mappings': bridge_mappings,
                               'tunnel_types': self.tunnel_types,
                               'tunneling_ip': local_ip,
                               'l2_population': self.l2_pop,
                               'arp_responder_enabled':
                               self.arp_responder_enabled,
                               'enable_distributed_routing':
                               self.enable_distributed_routing,
                               'log_agent_heartbeats':
                               self.conf.AGENT.log_agent_heartbeats},
            'agent_type': constants.AGENT_TYPE_OVS_DPDK,
            'start_flag': True}


def main(bridge_classes):
    try:
        agent_config = create_agent_config_map(cfg.CONF)
    except ValueError:
        LOG.exception(_LE("Agent failed to create agent config map"))
        raise SystemExit(1)
    prepare_xen_compute()
    try:
        agent = OVSDPDKNeutronAgent(bridge_classes, **agent_config)
    except RuntimeError as e:
        LOG.error(_LE("%s Agent terminated!"), e)
        sys.exit(1)
    agent.daemon_loop()
