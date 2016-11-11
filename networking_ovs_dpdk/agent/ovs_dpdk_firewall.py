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

import collections
import math
import netaddr
import re

from neutron_lib import constants
from oslo_config import cfg
from oslo_log import log as logging

from networking_ovs_dpdk.common._i18n import _, _LW, _LE

from neutron.agent import firewall
from neutron.common import utils as neutron_utils
from neutron.plugins.ml2.drivers.openvswitch.agent.common import (constants
    as ovs_constants)
from neutron.plugins.ml2.drivers.openvswitch.agent import \
    ovs_agent_extension_api


LOG = logging.getLogger(__name__)

# OpenFlow Table IDs
OF_ZERO_TABLE = ovs_constants.LOCAL_SWITCHING
OF_SELECT_TABLE = ovs_constants.OVS_FIREWALL_TABLES[0]
OF_EGRESS_TABLE = ovs_constants.OVS_FIREWALL_TABLES[1]
OF_INGRESS_TABLE = ovs_constants.OVS_FIREWALL_TABLES[2]
OF_INGRESS_EXT_TABLE = ovs_constants.OVS_FIREWALL_TABLES[3]

# Openflow ZERO table priorities
OF_T0_ARP_INT_PRIO = 100
OF_T0_ARP_EXT_PRIO = 90
OF_T0_SELECT_TABLE_IN_PRIO = 50
OF_T0_SELECT_TABLE_EXT_PRIO = 40
OF_T0_BLOCK = 35

# Openflow SELECT table priorities
OF_SEL_SERVICES_INT_IGMP_PRIO = 200
OF_SEL_SERVICES_EXT_IGMP_PRIO = 190
OF_SEL_SERVICES_EXT_MULTICAST_PRIO = 180
OF_SEL_EGRESS_PRIO = 100
OF_SEL_INGRESS_PRIO = 100
OF_DROP_TRAFFIC_PRIO = 50

# Openflow EGRESS table priorities
OF_EGRESS_SERVICES_PRIO = 50
OF_EGRESS_ANTISPOOF_PRIO = 40
OF_EGRESS_PORT_RULE_PRIO = 30
OF_EGRESS_ALLOW_EGRESS_RULE_PRIO = 20

# Openflow INGRESS table priorities
OF_INGRESS_SERVICES_PRIO = 50
OF_INGRESS_ANTISPOOF_PRIO = 40
OF_INGRESS_PORT_RULE_PRIO = 30
OF_INGRESS_OUTBOUND_PRIO = 10

# Openflow INGRESS_EXT table priorities
OF_INGRESS_EXT_BLOCK_INT_MAC_PRIO = 100
OF_INGRESS_EXT_BLOCK_EXT_SOURCE_PRIO = 100
OF_INGRESS_EXT_BLOCK_MULTICAST_PRIO = 100
OF_INGRESS_EXT_ALLOW_EXT_TRAFFIC_PRIO = 50

# Openflow LEARN ACTIONS priorities
OF_LEARNED_HIGH_PRIO = 100
OF_LEARNED_LOW_PRIO = 90

INGRESS_DIRECTION = 'ingress'
EGRESS_DIRECTION = 'egress'
LEARN_IDLE_TIMEOUT = 30  # 30 seconds.
LEARN_HARD_TIMEOUT = 1800  # 30 minutes.

# Ethernet type.
IPv4 = "IPv4"
IPv6 = "IPv6"

# OpenFlow mnemonics.
OF_MNEMONICS = {
    IPv6: {
        "ip_dst": "ipv6_dst",
        "ip_src": "ipv6_src",
        "ip_proto": "ipv6",
    },
    IPv4: {
        "ip_dst": "nw_dst",
        "ip_src": "nw_src",
        "ip_proto": "ip",
    },
}

# Protocols.
IPV4_ROUTER_MESSAGES = [9, 10]
# Router Solicitation (133)
# Router Advertisement (134)
# Neighbor Solicitation (135)
# Neighbor Advertisement (136)
# Redirect (137)
ICMPV6_TYPE_RS = 133
ICMPV6_TYPE_RA = constants.ICMPV6_TYPE_RA or 134
ICMPv6_TYPE_NS = 135
ICMPV6_TYPE_NA = constants.ICMPV6_TYPE_NA or 136
ICMPV6_TYPE_RED = 137
IPV6_ND_MESSAGES = [ICMPV6_TYPE_RS, ICMPV6_TYPE_RA, ICMPv6_TYPE_NS,
                    ICMPV6_TYPE_NA, ICMPV6_TYPE_RED]
# Multicast Listener Query (130)
# Multicast Listener Report (131)
# Multicast Listener Done (132)
ICMPV6_TYPE_MLQ = 130
ICMPV6_TYPE_MLR = 131
ICMPV6_TYPE_MLD = 132
IPV6_MLD_MESSAGES = [ICMPV6_TYPE_MLQ, ICMPV6_TYPE_MLR, ICMPV6_TYPE_MLD]

IPv6_MULTICAST_PREFIX = "ff02::1:ff00:0/104"

DIRECTION_IP_PREFIX = {'ingress': 'source_ip_prefix',
                       'egress': 'dest_ip_prefix'}

ETH_PROTOCOL_TABLE = {IPv4: "0x0800",
                      IPv6: "0x86dd"}

IP_PROTOCOL_TABLE = {
    constants.PROTO_NAME_TCP: constants.PROTO_NUM_TCP,
    constants.PROTO_NAME_ICMP: constants.PROTO_NUM_ICMP,
    constants.PROTO_NAME_IPV6_ICMP: constants.PROTO_NUM_IPV6_ICMP,
    constants.PROTO_NAME_UDP: constants.PROTO_NUM_UDP,
    "igmp": 2}

MULTICAST_MAC = "01:00:5e:00:00:00/01:00:5e:00:00:00"

ovs_opts = [
    cfg.BoolOpt('enable_sg_firewall_multicast', default=False,
               help=_("Allows multicast traffic coming into and going"
                      "outside OVS.")),
]
cfg.CONF.register_opts(ovs_opts, "OVS")


class OVSFirewallDriver(firewall.FirewallDriver):
    """Driver which enforces security groups through
           Open vSwitch flows.
        """

    def __init__(self, integration_bridge):
        self._filtered_ports = {}
        self._int_br = ovs_agent_extension_api.\
            OVSCookieBridge(integration_bridge).deferred(full_ordered=True)
        self._deferred = False
        self._enable_multicast = \
            cfg.CONF.OVS.enable_sg_firewall_multicast

        # List of security group rules for ports residing on this host
        self.sg_rules = {}

        # List of security group member ips for ports residing on this
        # host
        self.sg_members = collections.defaultdict(
            lambda: collections.defaultdict(list))
        self.pre_sg_members = None

        # Known ports managed.
        self._filtered_in_ports = {}

    @property
    def ports(self):
        return self._filtered_ports

    def _vif_port_info(self, port_name):
        """Returns additional vif port info: internal vlan tag,
            interfaces, segmentation id, net id, network type, physical
            network.
            """
        port_info = {'name': port_name}
        other_config = self._int_br.br.db_get_val('Port', port_name,
                                                  'other_config')

        if other_config is None or other_config.get('tag') is None:
            LOG.error(_LE("Port %(port_name)s tag info is not present. SG "
                          "rules can't be applied on this port."),
                      {'port_name': port_name})
            port_info['tag'] = None
        else:
            port_info['tag'] = other_config['tag']
        # Default fields (also other fields could be present):
        #   net_uuid="e00e6a6a-c88a-4724-80a7-6368a94241d9"
        #   network_type=vlan
        #   physical_network=default
        #   segmentation_id="1402"
        port_info.update(other_config)
        port_info['interfaces'] = \
            self._int_br.br.db_get_val('Port', port_name, 'interfaces')
        return port_info

    def update_security_group_rules(self, sg_id, sg_rules):
        LOG.debug("Update rules of security group (%s)", sg_id)
        self.sg_rules[sg_id] = sg_rules

    def update_security_group_members(self, sg_id, sg_members):
        LOG.debug("Update members of security group (%s)", sg_id)
        self.sg_members[sg_id] = collections.defaultdict(list, sg_members)

    def security_group_updated(self, action_type, sec_group_ids,
                               device_ids=[]):
        pass

    def _expand_sg_rule_with_remote_ips(self, rule, port):
        """Expand a remote group rule to rule per remote group IP."""
        remote_group_id = rule.get('remote_group_id')
        if remote_group_id:
            ethertype = rule['ethertype']
            port_ips = port.get('fixed_ips', [])

            for ip in self.sg_members[remote_group_id][ethertype]:
                if ip not in port_ips:
                    ip_rule = rule.copy()
                    direction_ip_prefix = (
                        DIRECTION_IP_PREFIX[rule['direction']])
                    ip_prefix = str(netaddr.IPNetwork(ip).cidr)
                    ip_rule[direction_ip_prefix] = ip_prefix
                    yield ip_rule
        else:
            yield rule

    def _write_proto(self, eth_type, protocol=None):
        if protocol == "arp":
            return "arp"

        proto_str = "eth_type=%s" % ETH_PROTOCOL_TABLE[eth_type]
        if protocol in IP_PROTOCOL_TABLE.keys():
            proto_num = IP_PROTOCOL_TABLE[protocol]
            if protocol == constants.PROTO_NAME_ICMP and \
                    eth_type == IPv6:
                proto_num = constants.PROTO_NUM_IPV6_ICMP
            proto_str += ",ip_proto=%s" % proto_num

        return proto_str

    def apply_port_filter(self, port):
        pass

    def _add_flow(self, **kwargs):
        LOG.debug("OFW add rule: %s", kwargs)
        if self._deferred:
            self._int_br.add_flow(**kwargs)
        else:
            self._int_br.br.add_flow(**kwargs)

    def _del_flows(self, **kwargs):
        LOG.debug("OFW del rule: %s", kwargs)
        if self._deferred:
            self._int_br.delete_flows(**kwargs)
        else:
            self._int_br.br.delete_flows(**kwargs)

    def _add_base_flows(self, port, vif_port):
        """Set base flows for every port."""
        self._add_zero_table(port, vif_port)
        self._add_selection_table(port, vif_port)
        self._add_selection_table_services(port, vif_port)
        self._add_selection_table_port_block(port)
        self._add_egress_antispoof(port, vif_port)
        self._add_egress_services(port, vif_port)
        self._add_ingress_allow_outbound_traffic(port)
        self._add_ingress_services(port, vif_port)

    def _add_zero_table(self, port, vif_port):
        """Set arp flows. The rest of the traffic is sent to
            SELECT_TABLE.
            """
        segmentation_id = port['vinfo']['segmentation_id']
        # ARP and ND traffic to be delivered to an internal port.
        for fixed_ip in port['fixed_ips']:
            # IPv4, ARP.
            if self._ip_version_from_address(fixed_ip) == IPv4:
                self._add_flow(priority=OF_T0_ARP_INT_PRIO,
                    table=OF_ZERO_TABLE,
                    proto=self._write_proto(IPv4, "arp"),
                    dl_vlan=segmentation_id,
                    nw_dst=fixed_ip,
                    actions='strip_vlan,output:%s'
                        % vif_port.ofport)

            # IPv6, NS and NA.
            if self._ip_version_from_address(fixed_ip) == IPv6:
                for icmpv6_type in IPV6_ND_MESSAGES:
                    self._add_flow(priority=OF_T0_ARP_INT_PRIO,
                        table=OF_ZERO_TABLE,
                        proto=self._write_proto(IPv6,
                            constants.PROTO_NAME_IPV6_ICMP),
                        dl_vlan=segmentation_id,
                        icmpv6_type=icmpv6_type,
                        ipv6_dst=fixed_ip,
                        actions='strip_vlan,output:%s'
                            % vif_port.ofport)

        # Internal port ARP messages to be delivered out of br-int.
        self._add_flow(priority=OF_T0_ARP_EXT_PRIO,
            table=OF_ZERO_TABLE,
            proto='arp',
            actions='normal')

        # Internal port NS and NA messages to be delivered out of br-int.
        for icmpv6_type in IPV6_ND_MESSAGES:
            self._add_flow(priority=OF_T0_ARP_EXT_PRIO,
                table=OF_ZERO_TABLE,
                proto=self._write_proto(IPv6,
                                        constants.PROTO_NAME_IPV6_ICMP),
                icmpv6_type=icmpv6_type,
                actions='normal')

        # Select traffic.
        # Incoming internal traffic: check mac, mod vlan.
        self._add_flow(priority=OF_T0_SELECT_TABLE_IN_PRIO,
                       table=OF_ZERO_TABLE,
                       dl_src=port['mac_address'],
                       actions="mod_vlan_vid:%s,"
                               "load:0->NXM_NX_REG0[0..11],"
                               "load:0->NXM_NX_REG1[0..11],"
                               "resubmit(,%s)"
                               % (port['vinfo']['tag'], OF_SELECT_TABLE))

        # Incoming external traffic: check external vlan tag, mod vlan.
        self._add_flow(priority=OF_T0_SELECT_TABLE_EXT_PRIO,
                       table=OF_ZERO_TABLE,
                       dl_vlan=segmentation_id,
                       actions="mod_vlan_vid:%s,"
                               "load:%s->NXM_NX_REG0[0..11],"
                               "load:0->NXM_NX_REG1[0..11],"
                               "resubmit(,%s)"
                               % (port['vinfo']['tag'],
                                  port['vinfo']['tag'],
                                  OF_SELECT_TABLE))

        # Block rest of traffic.
        self._add_flow(priority=OF_T0_BLOCK,
                       table=OF_ZERO_TABLE,
                       actions="drop")

    def _add_selection_table(self, port, vif_port):
        """Set traffic selection basic rules.
            Allows all internal traffic matching mac/ip to egress table.
            Allows all extenal traffic matching dst mac to ingress table.
        """
        for fixed_ip in port['fixed_ips']:
            if self._ip_version_from_address(fixed_ip) == IPv4:
                self._add_flow(priority=OF_SEL_EGRESS_PRIO,
                    table=OF_SELECT_TABLE,
                    in_port=vif_port.ofport,
                    proto=self._write_proto(IPv4),
                    dl_vlan=port['vinfo']['tag'],
                    dl_src=port['mac_address'],
                    nw_src=fixed_ip,
                    actions='resubmit(,%s)' %
                        (OF_EGRESS_TABLE))

            if self._ip_version_from_address(fixed_ip) == IPv6:
                self._add_flow(priority=OF_SEL_EGRESS_PRIO,
                    table=OF_SELECT_TABLE,
                    in_port=vif_port.ofport,
                    proto=self._write_proto(IPv6),
                    dl_vlan=port['vinfo']['tag'],
                    dl_src=port['mac_address'],
                    ipv6_src=fixed_ip,
                    actions='resubmit(,%s)' %
                        (OF_EGRESS_TABLE))

        # External traffic to ingress processing table
        self._add_flow(
            priority=OF_SEL_INGRESS_PRIO,
            table=OF_SELECT_TABLE,
            dl_vlan=port['vinfo']['tag'],
            dl_dst=port['mac_address'],
            actions='resubmit(,%d)'
                    % (OF_INGRESS_TABLE))

    def _add_selection_table_services(self, port, vif_port):
        """Selection table services:
           Allows DHCP traffic to request an IP address
           IGMP snooping/MLD traffic and multicast traffic.
        """
        # Allow DHCP requests from invalid address
        self._add_flow(priority=OF_SEL_EGRESS_PRIO,
                       table=OF_SELECT_TABLE,
                       in_port=vif_port.ofport,
                       proto=self._write_proto(IPv4),
                       dl_vlan=port['vinfo']['tag'],
                       dl_src=port['mac_address'],
                       nw_src='0.0.0.0',
                       actions="resubmit(,%s)"
                               % (OF_EGRESS_TABLE))

        if self._enable_multicast:
            for fixed_ip in port['fixed_ips']:
                if self._ip_version_from_address(fixed_ip) == IPv4:
                    # Add internal IGMP snooping traffic support. This traffic
                    # is sent to the bridge using the 'normal' action.
                    self._add_flow(priority=OF_SEL_SERVICES_INT_IGMP_PRIO,
                        table=OF_SELECT_TABLE,
                        in_port=vif_port.ofport,
                        proto=self._write_proto(IPv4, "igmp"),
                        dl_vlan=port['vinfo']['tag'],
                        dl_src=port['mac_address'],
                        dl_dst=MULTICAST_MAC,
                        nw_src=fixed_ip,
                        nw_dst=str(netaddr.ip.IPV4_MULTICAST.cidr),
                        actions='strip_vlan,normal')

                if self._ip_version_from_address(fixed_ip) == IPv6:
                    # Add internal MLD snooping traffic support.
                    self._add_flow(priority=OF_SEL_SERVICES_INT_IGMP_PRIO,
                        table=OF_SELECT_TABLE,
                        in_port=vif_port.ofport,
                        proto=self._write_proto(IPv6,
                            constants.PROTO_NAME_IPV6_ICMP),
                        dl_vlan=port['vinfo']['tag'],
                        dl_src=port['mac_address'],
                        dl_dst=MULTICAST_MAC,
                        ipv6_src=fixed_ip,
                        ipv6_dst=str(netaddr.ip.IPV6_MULTICAST.cidr),
                        actions='strip_vlan,normal')

            # Add external IGMP snooping traffic support.
            self._add_flow(priority=OF_SEL_SERVICES_EXT_IGMP_PRIO,
                table=OF_SELECT_TABLE,
                proto=self._write_proto(IPv4, "igmp"),
                dl_vlan=port['vinfo']['tag'],
                dl_dst=MULTICAST_MAC,
                nw_dst=str(netaddr.ip.IPV4_MULTICAST.cidr),
                actions='normal')

            # Add external MLD snooping traffic support.
            self._add_flow(priority=OF_SEL_SERVICES_EXT_IGMP_PRIO,
                table=OF_SELECT_TABLE,
                proto=self._write_proto(IPv6,
                                        constants.PROTO_NAME_IPV6_ICMP),
                dl_vlan=port['vinfo']['tag'],
                dl_dst=MULTICAST_MAC,
                ipv6_dst=str(netaddr.ip.IPV6_MULTICAST.cidr),
                actions='normal')

            # Allow external multicast traffic to skip the internal MAC filter.
            # This traffic is sent to the ingress table. Only TCP and UDP.
            # REG0 in external traffic must match the internal VLAN tag.
            for proto in [constants.PROTO_NAME_TCP,
                          constants.PROTO_NAME_UDP]:
                self._add_flow(priority=OF_SEL_SERVICES_EXT_MULTICAST_PRIO,
                    table=OF_SELECT_TABLE,
                    reg0="%s" % port['vinfo']['tag'],
                    proto=self._write_proto(IPv4, proto),
                    dl_vlan=port['vinfo']['tag'],
                    dl_dst=MULTICAST_MAC,
                    nw_dst=str(netaddr.ip.IPV4_MULTICAST.cidr),
                    actions='load:1->NXM_NX_REG1[0..11],'
                            'resubmit(,%s)' % OF_INGRESS_TABLE)
                self._add_flow(priority=OF_SEL_SERVICES_EXT_MULTICAST_PRIO,
                    table=OF_SELECT_TABLE,
                    reg0="%s" % port['vinfo']['tag'],
                    proto=self._write_proto(IPv6, proto),
                    dl_vlan=port['vinfo']['tag'],
                    dl_dst=MULTICAST_MAC,
                    ipv6_dst=str(netaddr.ip.IPV6_MULTICAST.cidr),
                    actions='load:1->NXM_NX_REG1[0..11],'
                            'resubmit(,%s)' % OF_INGRESS_TABLE)

    def _add_selection_table_port_block(self, port):
        """Block rest of the traffic.
            Drop all traffic not generated by or to a VM.
            """
        for eth_type in ETH_PROTOCOL_TABLE.keys():
            self._add_flow(
                priority=OF_DROP_TRAFFIC_PRIO,
                table=OF_SELECT_TABLE,
                proto=self._write_proto(eth_type),
                dl_vlan=port['vinfo']['tag'],
                actions='drop')

    def _add_egress_antispoof(self, port, vif_port):
        """Set antispoof rules.
            Antispoof rules take precedence to any rules set by
            the tenant in the security group.
            """
        # No DHCPv4 server out from port.
        self._add_flow(priority=OF_EGRESS_ANTISPOOF_PRIO,
                       table=OF_EGRESS_TABLE,
                       in_port=vif_port.ofport,
                       proto=self._write_proto(IPv4,
                                               constants.PROTO_NAME_UDP),
                       dl_vlan=port['vinfo']['tag'],
                       udp_src=67,
                       udp_dst=68,
                       actions='drop')

        # No DHCPv6 server out from port.
        self._add_flow(priority=OF_EGRESS_ANTISPOOF_PRIO,
                       table=OF_EGRESS_TABLE,
                       in_port=vif_port.ofport,
                       proto=self._write_proto(IPv6,
                                               constants.PROTO_NAME_UDP),
                       dl_vlan=port['vinfo']['tag'],
                       udp_src=547,
                       udp_dst=546,
                       actions='drop')

    def _add_egress_services(self, port, vif_port):
        """Add service rules.
            Allows traffic to DHCPv4/v6 servers.
            Allows icmp traffic.
            """
        # DHCP & DHCPv6.
        for eth_type, udp_src, udp_dst in [(IPv4, 68, 67), (IPv6, 546, 547)]:
            self._add_flow(
                table=OF_EGRESS_TABLE,
                priority=OF_EGRESS_SERVICES_PRIO,
                dl_vlan=port['vinfo']['tag'],
                dl_src=port['mac_address'],
                in_port=vif_port.ofport,
                proto=self._write_proto(eth_type, constants.PROTO_NAME_UDP),
                udp_src=udp_src,
                udp_dst=udp_dst,
                actions='resubmit(,%s)' % OF_INGRESS_TABLE)

        # Allows ICMP router advertisement / router selection.
        for type in IPV4_ROUTER_MESSAGES:
            self._add_flow(
                table=OF_EGRESS_TABLE,
                priority=OF_EGRESS_SERVICES_PRIO,
                dl_vlan=port['vinfo']['tag'],
                dl_src=port['mac_address'],
                proto=self._write_proto(IPv4,
                                        constants.PROTO_NAME_ICMP),
                icmp_type=type,
                actions='resubmit(,%s)' % OF_INGRESS_TABLE)

        # Allows IPv6 MLD messages.
        for icmpv6_type in IPV6_MLD_MESSAGES:
            self._add_flow(
                table=OF_EGRESS_TABLE,
                priority=OF_EGRESS_SERVICES_PRIO,
                dl_vlan=port['vinfo']['tag'],
                dl_src=port['mac_address'],
                in_port=vif_port.ofport,
                proto=self._write_proto(IPv6,
                                        constants.PROTO_NAME_IPV6_ICMP),
                icmpv6_type=icmpv6_type,
                actions='resubmit(,%s)' % OF_INGRESS_TABLE)

    def _add_ingress_allow_outbound_traffic(self, port):
        """Allows ingress outbound traffic.
            By default, all ingress traffic not matching any internal port
            in the bridge is sent to the external ports.
            """
        # If the traffic do not match any mac address inside the bridge,
        # send the traffic to the INGRESS_EXT table.
        self._add_flow(
            table=OF_INGRESS_TABLE,
            priority=OF_INGRESS_OUTBOUND_PRIO,
            dl_vlan=port['vinfo']['tag'],
            actions='resubmit(,%s)' % OF_INGRESS_EXT_TABLE)

        # Blocks all traffic in this table if it's for an internal
        # port (mac address).
        self._add_flow(
            table=OF_INGRESS_EXT_TABLE,
            priority=OF_INGRESS_EXT_BLOCK_INT_MAC_PRIO,
            dl_vlan=port['vinfo']['tag'],
            dl_dst=port['mac_address'],
            actions='drop')

        # Blocks all traffic in this table if was sent by an external
        # source. Prevents from sending back the traffic.
        self._add_flow(
            table=OF_INGRESS_EXT_TABLE,
            priority=OF_INGRESS_EXT_BLOCK_EXT_SOURCE_PRIO,
            dl_vlan=port['vinfo']['tag'],
            reg0="%s" % port['vinfo']['tag'],
            actions='drop')

        # Use normal action to send the traffic outside the integration
        # bridge.
        self._add_flow(
            table=OF_INGRESS_EXT_TABLE,
            priority=OF_INGRESS_EXT_ALLOW_EXT_TRAFFIC_PRIO,
            dl_vlan=port['vinfo']['tag'],
            actions='strip_vlan,normal')

    def _add_ingress_services(self, port, vif_port):
        """Add service rules.dl_vlan=port['vinfo']['tag'],
            Allows traffic to DHCPv4/v6 servers
            Allows specific icmp traffic (RA messages).
            """
        # DHCP & DHCPv6.
        for eth_type, udp_src, udp_dst in [(IPv4, 67, 68), (IPv6, 547, 546)]:
            self._add_flow(
                table=OF_INGRESS_TABLE,
                priority=OF_INGRESS_SERVICES_PRIO,
                proto=self._write_proto(eth_type, constants.PROTO_NAME_UDP),
                dl_vlan=port['vinfo']['tag'],
                dl_dst=port['mac_address'],
                udp_src=udp_src,
                udp_dst=udp_dst,
                actions=self._get_ingress_actions(vif_port))

        # ICMP RA messages.
        for type in [9, 10]:
            self._add_flow(
                table=OF_INGRESS_TABLE,
                priority=OF_INGRESS_SERVICES_PRIO,
                proto=self._write_proto(IPv4,
                                        constants.PROTO_NAME_ICMP),
                dl_vlan=port['vinfo']['tag'],
                dl_dst=port['mac_address'],
                icmp_type=type,
                actions=self._get_ingress_actions(vif_port))

        # ICMP6 MLD messages.
        for icmpv6_type in IPV6_MLD_MESSAGES:
            self._add_flow(
                table=OF_INGRESS_TABLE,
                priority=OF_INGRESS_SERVICES_PRIO,
                proto=self._write_proto(IPv6,
                                        constants.PROTO_NAME_IPV6_ICMP),
                dl_vlan=port['vinfo']['tag'],
                dl_dst=port['mac_address'],
                icmpv6_type=icmpv6_type,
                actions=self._get_ingress_actions(vif_port))

        if self._enable_multicast:
            # Block the multicast traffic in the external ingress table.
            self._add_flow(
                table=OF_INGRESS_EXT_TABLE,
                priority=OF_INGRESS_EXT_BLOCK_MULTICAST_PRIO,
                dl_vlan=port['vinfo']['tag'],
                reg1="1",
                actions='drop')

    def _get_ingress_actions(self, vif_port):
        return 'strip_vlan,output:%(oport)s' % \
               {'oport': vif_port.ofport}

    def _remove_flows(self, port):
        # Remove manual and "learn action" rules.
        self._del_flows(dl_src=port["mac_address"])
        self._del_flows(dl_dst=port["mac_address"])
        # Remove antispoof rules.
        if self._filtered_in_ports.get(port['device']):
            self._del_flows(in_port=self._filtered_in_ports.get(
                port['device']))
        # Remove ARP rules.
        for ipv4 in [ip for ip in port['fixed_ips'] if
                     self._ip_version_from_address(ip) == IPv4]:
            self._del_flows(table=OF_ZERO_TABLE, nw_dst=ipv4,
                            proto=self._write_proto(IPv4, "arp"))
        # Remove ND rules.
        for ipv6 in [ip for ip in port['fixed_ips'] if
                     self._ip_version_from_address(ip) == IPv6]:
            self._del_flows(table=OF_ZERO_TABLE, ipv6_dst=ipv6,
                proto=self._write_proto(IPv6, constants.PROTO_NAME_IPV6_ICMP))

    def _write_multicast_flow(self, flow, direction, port, port_match,
                              priority, ip_version):
        """Write a flow for the manual rule, allowing multicast traffic.
            """
        # Multicast ingress traffic.
        # Check the traffic protocol: only tcp or udp. Also check the
        # multicast destination MAC and IP.
        if self._enable_multicast \
                and direction == INGRESS_DIRECTION \
                and flow['proto'] in [constants.PROTO_NAME_TCP,
                                      constants.PROTO_NAME_UDP]:
            hp_flow = dict.copy(flow)
            ip_dst = str(netaddr.ip.IPV6_MULTICAST.cidr) \
                if ip_version == IPv6 \
                else str(netaddr.ip.IPV4_MULTICAST.cidr)
            hp_flow[OF_MNEMONICS[ip_version]['ip_dst']] = ip_dst
            hp_flow['dl_vlan'] = port['vinfo']['tag']
            hp_flow['priority'] = priority
            hp_flow['dl_dst'] = MULTICAST_MAC
            hp_flow['table'] = OF_INGRESS_TABLE
            hp_flow['actions'] = \
                "move:NXM_NX_REG0[0..11]->NXM_OF_VLAN_TCI[0..11],normal"
            self._write_flows_per_port_match(hp_flow, port_match)

    def _get_learn_action_rule(self, direction, priority,
                               port_range_min, port_range_max,
                               eth_type, ip_proto, vif_port):
        # Write protocol string.
        proto_str = self._write_proto(eth_type, ip_proto)
        port_dst_str = ""
        port_src_str = ""
        if ip_proto in [constants.PROTO_NAME_TCP,
                        constants.PROTO_NAME_UDP]:
            # Known L4 protocols with configurable ports.
            port_dst_str = \
                "NXM_OF_%(ip_proto)s_DST[]=NXM_OF_%(ip_proto)s_SRC[]," \
                % {'ip_proto': ip_proto.upper()}
            port_src_str = \
                "NXM_OF_%(ip_proto)s_SRC[]=NXM_OF_%(ip_proto)s_DST[]," \
                % {'ip_proto': ip_proto.upper()}

        # Setup ICMPv4/v6 type and code.
        icmp_type = ""
        icmp_code = ""
        if ip_proto == constants.PROTO_NAME_ICMP:
            if port_range_min == 8:
                icmp_type = "icmp_type=%s," % 0
            elif port_range_min == 13:
                icmp_type = "icmp_type=%s," % 14
            elif port_range_min == 15:
                icmp_type = "icmp_type=%s," % 16
            elif port_range_min == 17:
                icmp_type = "icmp_type=%s," % 18
            elif port_range_min:
                icmp_type = "icmp_type=%s," % port_range_min

            if port_range_max:
                icmp_code = "icmp_code=%s," % port_range_max
        elif ip_proto == constants.PROTO_NAME_IPV6_ICMP:
            if port_range_min:
                icmp_type = "icmpv6_type=%s," % port_range_min
            if port_range_max:
                icmp_code = "icmpv6_code=%s," % port_range_max

        # Source and destination IPs.
        if eth_type == IPv4:
            ip_dst = "NXM_OF_IP_DST[]=NXM_OF_IP_SRC[],"
            ip_src = "NXM_OF_IP_SRC[]=NXM_OF_IP_DST[],"
        else:
            ip_dst = "NXM_NX_IPV6_DST[]=NXM_NX_IPV6_SRC[],"
            ip_src = "NXM_NX_IPV6_SRC[]=NXM_NX_IPV6_DST[],"

        # Learn action store table:
        if direction == INGRESS_DIRECTION:
            learn_action_table = OF_EGRESS_TABLE
        elif direction == EGRESS_DIRECTION:
            learn_action_table = OF_INGRESS_TABLE

        learn_actions = "learn(table=%(table)s," \
                        "priority=%(priority)s," \
                        "idle_timeout=%(idle_timeout)s," \
                        "hard_timeout=%(hard_timeout)s," \
                        "%(proto)s," \
                        "NXM_OF_ETH_SRC[]=NXM_OF_ETH_DST[]," \
                        "NXM_OF_ETH_DST[]=NXM_OF_ETH_SRC[]," \
                        "%(ip_src)s" \
                        "%(ip_dst)s" \
                        "%(port_dst)s" \
                        "%(port_src)s" \
                        "%(icmp_type)s" \
                        "%(icmp_code)s" \
                        "NXM_OF_VLAN_TCI[0..11]," \
                        "load:NXM_NX_REG0[0..11]->NXM_OF_VLAN_TCI[0..11]," \
                        "output:NXM_OF_IN_PORT[])" % \
                        {'table': learn_action_table,
                         'priority': priority,
                         'idle_timeout': LEARN_IDLE_TIMEOUT,
                         'hard_timeout': LEARN_HARD_TIMEOUT,
                         'proto': proto_str,
                         'ip_src': ip_src,
                         'ip_dst': ip_dst,
                         'port_dst': port_dst_str,
                         'port_src': port_src_str,
                         'icmp_type': icmp_type,
                         'icmp_code': icmp_code}

        if direction == EGRESS_DIRECTION:
            return "%(learn_actions)s," \
                   "resubmit(,%(table)s)" % \
                   {'learn_actions': learn_actions,
                    'table': OF_INGRESS_TABLE}
        elif direction == INGRESS_DIRECTION:
            return "%(learn_actions)s," \
                   "strip_vlan,output:%(ofport)s" % \
                   {'learn_actions': learn_actions,
                    'ofport': vif_port.ofport}

    def _select_sg_rules_for_port(self, port):
        """Select rules from the security groups the port is member of."""
        port_sg_ids = port.get('security_groups', [])
        port_rules = []

        for sg_id in port_sg_ids:
            for rule in self.sg_rules.get(sg_id, []):
                port_rules.extend(
                    self._expand_sg_rule_with_remote_ips(rule, port))
        return port_rules

    def _write_flows_per_port_match(self, flow, port_match):
        if port_match == "" or isinstance(flow[port_match], int):
            self._add_flow(**flow)
        elif isinstance(flow[port_match], list):
            for portm in flow[port_match]:
                hp_flow = dict.copy(flow)
                hp_flow[port_match] = portm
                self._add_flow(**hp_flow)

    def _write_flows_per_ip(self, flow, rule, port, port_match, ip_proto):
        """Write the needed flows per each IP in the port."""
        vif_port = self._int_br.br.get_vif_port_by_id(port['device'])
        if not vif_port:
            LOG.warning(_LW("Port %(port_id)s not present in bridge. Skip "
                            "applying rules for this port"),
                        {'port_id': port})
            return

        # Write a rule(s) per ip.
        for fixed_ip in port['fixed_ips']:
            # Check if the rule and the IP address have the same version.
            if rule['ethertype'] != \
                    self._ip_version_from_address(fixed_ip):
                continue

            if rule['direction'] == EGRESS_DIRECTION:
                flow[OF_MNEMONICS[rule['ethertype']]['ip_src']] = fixed_ip
            elif rule['direction'] == INGRESS_DIRECTION:
                flow[OF_MNEMONICS[rule['ethertype']]['ip_dst']] = fixed_ip

            # Write learn actions.
            # Default protocol: "ip". Create high priority rules
            # for TCP and UDP protocols.
            if not ip_proto:
                for proto in [constants.PROTO_NAME_TCP,
                              constants.PROTO_NAME_UDP]:
                    hp_flow = dict.copy(flow)
                    hp_flow['proto'] = self._write_proto(rule['ethertype'],
                                                         proto)
                    hp_flow['actions'] = self._get_learn_action_rule(
                        rule['direction'],
                        OF_LEARNED_HIGH_PRIO,
                        "",
                        "",
                        rule['ethertype'],
                        proto,
                        vif_port)
                    self._write_flows_per_port_match(hp_flow, port_match)

            # Write normal "learn action" for every flow.
            flow['actions'] = self._get_learn_action_rule(
                rule['direction'],
                OF_LEARNED_LOW_PRIO,
                rule.get('port_range_min'),
                rule.get('port_range_max'),
                rule['ethertype'],
                rule.get('protocol'),
                vif_port)
            self._write_flows_per_port_match(flow, port_match)

        # Write multicast rule.
        self._write_multicast_flow(flow, rule['direction'], port,
                                   port_match, OF_LEARNED_LOW_PRIO,
                                   rule['ethertype'])

    def _add_rules_flows(self, port):
        rules = self._select_sg_rules_for_port(port)
        for rule in rules:
            ethertype = rule['ethertype']
            direction = rule['direction']
            protocol = rule.get('protocol')
            port_range_min = rule.get('port_range_min')
            port_range_max = rule.get('port_range_max')
            source_ip_prefix = rule.get('source_ip_prefix')
            dest_ip_prefix = rule.get('dest_ip_prefix')

            flow = {}
            # Direcction.
            if direction == EGRESS_DIRECTION:
                flow['priority'] = OF_EGRESS_PORT_RULE_PRIO
                flow['table'] = OF_EGRESS_TABLE
                flow["dl_src"] = port["mac_address"]

            elif direction == INGRESS_DIRECTION:
                flow['priority'] = OF_INGRESS_PORT_RULE_PRIO
                flow['table'] = OF_INGRESS_TABLE
                flow["dl_dst"] = port["mac_address"]

            # Protocol.
            flow['proto'] = self._write_proto(ethertype, protocol)

            # Port range.
            port_match = ""
            if (port_range_min and port_range_max and
                    protocol in [constants.PROTO_NAME_TCP,
                                 constants.PROTO_NAME_UDP]):
                port_match = "%s_dst" % protocol
                if port_range_max > port_range_min:
                    flow[port_match] = neutron_utils.port_rule_masking(
                        port_range_min,
                        port_range_max)
                else:
                    flow[port_match] = int(port_range_min)

            # Destination and source address.
            if dest_ip_prefix and dest_ip_prefix != "0.0.0.0/0":
                flow[OF_MNEMONICS[ethertype]["ip_dst"]] = dest_ip_prefix

            if source_ip_prefix and source_ip_prefix != "0.0.0.0/0":
                flow[OF_MNEMONICS[ethertype]["ip_src"]] = source_ip_prefix

            # Write flow.
            self._write_flows_per_ip(flow, rule, port, port_match, protocol)

    def _apply_flows(self):
        self._int_br.apply_flows()

    def prepare_port_filter(self, port):
        LOG.debug("OFW Preparing device (%s) filter: %s", port['device'],
                  port)
        vif_port = self._int_br.br.get_vif_port_by_id(port['device'])
        if not vif_port:
            LOG.warning(_LW("Port %(port_id)s not present in bridge. Skip"
                            "applying rules for this port"),
                        {'port_id': port})
            return
        port['vinfo'] = self._vif_port_info(vif_port.port_name)
        self._remove_flows(port)
        self._filtered_ports[port['device']] = port
        self._filtered_in_ports[port['device']] = vif_port.ofport
        self._add_base_flows(port, vif_port)
        self._add_rules_flows(port)

    def update_port_filter(self, port):
        LOG.debug("OFW Updating device (%s) filter: %s", port['device'],
                  port)
        if port['device'] not in self._filtered_ports:
            LOG.info(_('Attempted to update port filter which is not '
                       'filtered %s'), port['device'])
            return

        old_port = self._filtered_ports.get(port['device'])
        vif_port = self._int_br.br.get_vif_port_by_id(port['device'])
        if not vif_port:
            LOG.warning(_LW("Port %(port_id)s not present in bridge. Skip"
                            "applying rules for this port"),
                        {'port_id': port})
            return
        port['vinfo'] = self._vif_port_info(vif_port.port_name)
        self._remove_flows(old_port)
        self._filtered_ports[port['device']] = port
        self._filtered_in_ports[port['device']] = vif_port.ofport
        self._add_base_flows(port, vif_port)
        self._add_rules_flows(port)

    def remove_port_filter(self, port):
        LOG.debug("OFW Removing device (%s) filter: %s", port['device'],
                  port)
        if not self._filtered_ports.get(port['device']):
            LOG.info(_('Attempted to remove port filter which is not '
                       'filtered %r'), port)
            return
        self._remove_flows(port)
        self._filtered_ports.pop(port['device'])
        self._filtered_in_ports.pop(port['device'])

    def filter_defer_apply_on(self):
        LOG.debug("OFW defer_apply_on")
        self._deferred = True

    def filter_defer_apply_off(self):
        LOG.debug("OFW defer_apply_off")
        if self._deferred:
            self._apply_flows()
            self._deferred = False

    @staticmethod
    def _ip_version_from_address(ip_string):
        ipv4_pattern = \
            "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}" \
            "(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        ipv6_pattern = "^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"
        ipv6_pattern_hexcompressed = \
            "^((?:[0-9A-Fa-f]{1,4}(?::[0-9A-Fa-f]" \
            "{1,4})*)?)::((?:[0-9A-Fa-f]{1,4}(?::[0-9A-Fa-f]{1,4})*)?)$"
        ipv6_pattern_hex4dec = \
            "^((?:[0-9A-Fa-f]{1,4}:){6,6})(25[0-5]|2[0-4]" \
            "\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\z"
        ipv6_pattern_hex4deccompressed = \
            "^((?:[0-9A-Fa-f]{1,4}(?::[0-9A-Fa-f]" \
            "{1,4})*)?) ::((?:[0-9A-Fa-f]{1,4}:)*)(25[0-5]|2[0-4]" \
            "\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}$"
        if re.search(ipv4_pattern, ip_string):
            return IPv4
        if re.search(ipv6_pattern, ip_string) or \
                re.search(ipv6_pattern_hexcompressed, ip_string) or \
                re.search(ipv6_pattern_hex4dec, ip_string) or \
                re.search(ipv6_pattern_hex4deccompressed, ip_string):
            return IPv6
        raise ValueError(_('Illegal IP string address'))

