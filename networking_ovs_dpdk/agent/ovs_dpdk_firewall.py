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

from oslo_config import cfg
from oslo_log import log as logging

from neutron.agent.common import ovs_lib
from neutron.agent import firewall
from neutron.common import constants

LOG = logging.getLogger(__name__)

# OpenFlow Table IDs
OF_ZERO_TABLE = 0
OF_EGRESS_STRIP_VLAN_TABLE = 1
OF_EGRESS_TABLE = 11
OF_INGRESS_STRIP_VLAN_TABLE = 2
OF_INGRESS_TABLE = 12

# Openflow Table 0 priorities
OF_T0_EGRESS_PRIO = 100
OF_T0_EGRESS_ARP_PRIO = 90
OF_T0_EGRESS_NO_MATCH_PRIO = 80
OF_T0_INGRESS_ARP_PRIO = 60
OF_T0_INGRESS_PRIO = 50
OF_DROP_TRAFFIC_PRIO = 40

# Openflow EGRESS table priorities
OF_EGRESS_STRIP_VLAN = 100
OF_EGRESS_STRIP_VLAN_OUT = 90
OF_EGRESS_SERVICES_PRIO = 50
OF_EGRESS_ANTISPOOF_PRIO = 40
OF_EGRESS_PORT_RULE_PRIO = 30
OF_EGRESS_ALLOW_EGRESS_RULE_PRIO = 20

# Openflow INGRESS table priorities
OF_INGRESS_STRIP_VLAN = 100
OF_INGRESS_STRIP_VLAN_OUT = 90
OF_INGRESS_SERVICES_PRIO = 45
OF_INGRESS_ANTISPOOF_PRIO = 40
OF_INGRESS_PORT_RULE_PRIO = 30
OF_INGRESS_OUTBOUND_PRIO = 10

# Openflow LEARN ACTIONS priorities
OF_LEARNED_HIGH_PRIO = 70
OF_LEARNED_LOW_PRIO = 60


INGRESS_DIRECTION = 'ingress'
EGRESS_DIRECTION = 'egress'

ICMPv6 = 'ipv6,nw_proto=58'
OUTBOUND_PORT_TYPE = 'patch'
LEARN_IDLE_TIMEOUT = 30     # 30 seconds.
LEARN_HARD_TIMEOUT = 1800   # 30 minutes.

DIRECTION_IP_PREFIX = {'ingress': 'source_ip_prefix',
                       'egress': 'dest_ip_prefix'}

ETH_PROTOCOL_TABLE = {constants.IPv4: "0x0800",
                      constants.IPv6: "0x86dd"}

IP_PROTOCOL_TABLE = {constants.PROTO_NAME_TCP: constants.PROTO_NUM_TCP,
    constants.PROTO_NAME_ICMP: constants.PROTO_NUM_ICMP,
    constants.PROTO_NAME_ICMP_V6: constants.PROTO_NUM_ICMP_V6,
    constants.PROTO_NAME_UDP: constants.PROTO_NUM_UDP}


class OVSFirewallDriver(firewall.FirewallDriver):
        """Driver which enforces security groups through
           Open vSwitch flows.
        """

        def __init__(self):
            self._filtered_ports = {}
            self._filtered_ports_modified = {}
            self._int_br = ovs_lib.OVSBridge(cfg.CONF.OVS.integration_bridge)
            self._int_br_not_deferred = self._int_br
            self._deferred = False

            # List of security group rules for ports residing on this host
            self.sg_rules = {}

            # List of security group member ips for ports residing on this host
            self.sg_members = collections.defaultdict(
                lambda: collections.defaultdict(list))
            self.pre_sg_members = None

            # Known ports managed.
            self.known_in_port_for_device = {}

        @property
        def ports(self):
            return self._filtered_ports

        def _outbound_port(self):
            """Go over all ports in bridge and returns the patch port
            in the bridge, if exists.
            """
            # Loop all ports looking for type='patch'.
            for port_name in self._int_br_not_deferred.get_port_tag_dict():
                port_type = self._int_br_not_deferred.db_get_val('Interface',
                                                                 port_name,
                                                                 'type')
                if port_type == OUTBOUND_PORT_TYPE:
                    return self._int_br_not_deferred.db_get_val('Interface',
                                                                port_name,
                                                                'ofport')

            return None

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
            """Expand a remote group rule to rule per remote group IP.
            """
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

        def apply_port_filter(self, port):
            pass

        def _get_port_vlan(self, vif_port):
            # optimize calls to this out to avoid re-fetching same port across
            # runs, will be used to map CT connections in zones per vlan tag
            vlan = self._int_br_not_deferred.db_get_val('Port',
                                                        vif_port.port_name,
                                                        'Interface')
            LOG.debug("vlan: %s", vlan)

            # Use external_ids
            if type(vlan) != int:
                vlan = 1
                LOG.warning("vlan for vif_port %s not assigned, using zone 1",
                            vif_port.port_name)
            return vlan

        def _add_flow(self, *args, **kwargs):
            self._int_br.add_flow(*args, **kwargs)

        def _add_base_flows(self, port, vif_port):
            """Set base flows for every port.
            """
            self._add_port_egress(port, vif_port)
            self._add_port_egress_antispoof(port, vif_port)
            self._add_port_egress_services(port, vif_port)
            self._add_port_block_traffic_default()
            self._add_port_ingress_and_arp(port, vif_port)
            self._add_port_ingress_services(port, vif_port)
            self._add_port_ingress_allow_outbound_traffic(port)
            self._add_port_strip_vlan_tag(port)

        def _add_port_egress(self, port, vif_port):
            """Set egress basic rules.
            Allow DHCP traffic to request an IP address, send all
            traffic matching mac/ip to egress table and allow arp.
            """
            # Allow DHCP requests from invalid address
            self._add_flow(priority=OF_T0_EGRESS_PRIO,
                           in_port=vif_port.ofport,
                           proto='ip',
                           nw_src='0.0.0.0',
                           dl_src=port['mac_address'],
                           actions="goto_table:%d"
                                   % (OF_EGRESS_STRIP_VLAN_TABLE))

            for fixed_ip in port['fixed_ips']:
                # IPv6 address not supported yet.
                if self._ip_version_from_address(fixed_ip) == constants.IPv6:
                    continue

                # Jump to egress table per port+ip pair on know mac
                self._add_flow(priority=OF_T0_EGRESS_PRIO,
                               in_port=vif_port.ofport,
                               proto='ip',
                               nw_src=fixed_ip,
                               dl_src=port['mac_address'],
                               actions='mod_vlan_vid:%s,goto_table:%d' %
                               (port['zone_id'], OF_EGRESS_STRIP_VLAN_TABLE))

            self.known_in_port_for_device[port['device']] = vif_port.ofport

        def _add_port_egress_antispoof(self, port, vif_port):
            """Set antispoof rules.
            Antispoof rules take precedence to any rules set by
            the tenant in the security group.
            """
            # No DHCPv4 server out from port.
            self._add_flow(priority=OF_EGRESS_ANTISPOOF_PRIO,
                           table=OF_EGRESS_TABLE,
                           in_port=vif_port.ofport,
                           proto='udp',
                           udp_src=67,
                           udp_dst=68,
                           actions='drop')

            # No DHCPv6 server out from port.
            self._add_flow(priority=OF_EGRESS_ANTISPOOF_PRIO,
                           table=OF_EGRESS_TABLE,
                           in_port=vif_port.ofport,
                           proto='udp',
                           udp_src=547,
                           udp_dst=546,
                           actions='drop')

        def _add_port_egress_services(self, port, vif_port):
            """Add service rules.
            Allows traffic to DHCPv4/v6 servers; allows icmp traffic.
            """
            # DHCP & DHCPv6.
            for udp_src, udp_dst in [(68, 67), (546, 547)]:
                self._add_flow(
                    table=OF_EGRESS_TABLE,
                    priority=OF_EGRESS_SERVICES_PRIO,
                    dl_src=port['mac_address'],
                    in_port=vif_port.ofport,
                    proto='udp',
                    udp_src=udp_src,
                    udp_dst=udp_dst,
                    actions='normal')

            # Allow ICMP router solicitation/etc.
            self._add_flow(
                table=OF_EGRESS_TABLE,
                priority=OF_EGRESS_SERVICES_PRIO,
                dl_src=port['mac_address'],
                in_port=vif_port.ofport,
                proto='icmp',
                actions='normal')

            # Allow ICMPv6 router solicitation/etc.
            self._add_flow(
                table=OF_EGRESS_TABLE,
                priority=OF_EGRESS_SERVICES_PRIO,
                dl_src=port['mac_address'],
                in_port=vif_port.ofport,
                proto=ICMPv6,
                actions='normal')

        def _add_port_ingress_allow_outbound_traffic(self, port):
            """Allow ingress outbound traffic.
            By default, all egress traffic not matching any internal port
            in the bridge is sent to the patch port.
            """
            # If the traffic do not match any mac address inside the bridge,
            # send the traffic through the outbound port (patch port).
            outbound_port = self._outbound_port()
            if outbound_port is not None:
                self._add_flow(
                    table=OF_INGRESS_TABLE,
                    priority=OF_INGRESS_OUTBOUND_PRIO,
                    proto='ip',
                    actions='mod_vlan_vid:%(vlan)s,output:%(oport)s' %
                            {'vlan': port['zone_id'],
                             'oport': outbound_port})

        def _add_port_ingress_and_arp(self, port, vif_port):
            """Set ingress basic rules.
            Allows arp traffic; sends all incoming traffic matching the
            destination port to the ingress table.
            """
            # In port arp responses
            self._add_flow(
                priority=OF_T0_INGRESS_ARP_PRIO,
                dl_dst=port['mac_address'],
                proto='arp',
                actions="strip_vlan,output:%s" % vif_port.ofport)

            # Go to ingress processing table
            self._add_flow(
                priority=OF_T0_INGRESS_PRIO,
                dl_dst=port['mac_address'],
                actions='resubmit(0,%d)'
                        % (OF_INGRESS_STRIP_VLAN_TABLE))

        def _add_port_ingress_services(self, port, vif_port):
            """Add service rules.
            Allows traffic to DHCPv4/v6 servers; allows icmp traffic.
            """
            # DHCP & DHCPv6.
            for udp_src, udp_dst in [(67, 68), (547, 546)]:
                self._add_flow(
                    table=OF_INGRESS_TABLE,
                    priority=OF_INGRESS_SERVICES_PRIO,
                    dl_dst=port['mac_address'],
                    proto='udp',
                    udp_src=udp_src,
                    udp_dst=udp_dst,
                    actions=self._get_ingress_actions(vif_port))

            # ICMP RA messages.
            for icmpv6_type in constants.ICMPV6_ALLOWED_TYPES:
                self._add_flow(
                    table=OF_INGRESS_TABLE,
                    priority=OF_INGRESS_SERVICES_PRIO,
                    dl_dst=port['mac_address'],
                    proto=ICMPv6,
                    icmp_type=icmpv6_type,
                    actions=self._get_ingress_actions(vif_port))

        def _add_port_block_traffic_default(self):
            """Block rest of the traffic.
            Drop all traffic not generated by or to a Vm.
            """
            self._add_flow(
                priority=OF_DROP_TRAFFIC_PRIO,
                proto='ip',
                actions='drop')

        def _add_port_strip_vlan_tag(self, port):
            """Strip VLAN tag in EGRESS and INGRESS tables before matching
            learn action rules, only for traffic going into VM ports.
            """
            self._add_flow(
                table=OF_INGRESS_STRIP_VLAN_TABLE,
                priority=OF_INGRESS_STRIP_VLAN,
                dl_dst=port['mac_address'],
                actions='strip_vlan,resubmit(,%s)' % OF_INGRESS_TABLE)
            self._add_flow(
                table=OF_INGRESS_STRIP_VLAN_TABLE,
                priority=OF_INGRESS_STRIP_VLAN_OUT,
                actions='resubmit(,%s)' % OF_INGRESS_TABLE)
            self._add_flow(
                table=OF_EGRESS_STRIP_VLAN_TABLE,
                priority=OF_EGRESS_STRIP_VLAN,
                dl_dst=port['mac_address'],
                actions='strip_vlan,resubmit(,%s)' % OF_EGRESS_TABLE)
            self._add_flow(
                table=OF_EGRESS_STRIP_VLAN_TABLE,
                priority=OF_EGRESS_STRIP_VLAN_OUT,
                actions='resubmit(,%s)' % OF_EGRESS_TABLE)

        def _remove_flows(self, port, vif_port):
            self._int_br.delete_flows(dl_src=port["mac_address"])
            self._int_br.delete_flows(dl_dst=port["mac_address"])
            if vif_port:
                self._int_br.delete_flows(in_port=vif_port.ofport)
            else:
                self._int_br.delete_flows(
                    in_port=self.known_in_port_for_device.pop(port['device']))

        def _get_ingress_actions(self, vif_port):
            return 'strip_vlan,output:%(oport)s' % \
                   {'oport': vif_port.ofport}

        def _get_learn_action_rule(self, direction, priority,
                                port_range_min, port_range_max,
                                eth_type, ip_proto, vif_port):
            # Ethernet type.
            eth_type_num = ETH_PROTOCOL_TABLE.get(eth_type)

            # IP type.
            ip_proto_num = IP_PROTOCOL_TABLE.get(ip_proto)
            port_dst_str = ""
            port_src_str = ""
            if ip_proto in [constants.PROTO_NAME_TCP,
                            constants.PROTO_NAME_UDP]:
                # Known L4 protocols with configurable ports.
                ip_proto_str = "ip_proto=%d," % ip_proto_num
                port_dst_str = \
                    "NXM_OF_%(ip_proto)s_DST[]=NXM_OF_%(ip_proto)s_SRC[]," \
                    % {'ip_proto': ip_proto.upper()}
                port_src_str = \
                    "NXM_OF_%(ip_proto)s_SRC[]=NXM_OF_%(ip_proto)s_DST[]," \
                    % {'ip_proto': ip_proto.upper()}
            elif ip_proto_num:
                # Rest of known L4 protocols without configurable ports.
                ip_proto_str = "ip_proto=%d," % ip_proto_num
            else:
                # No L4 protocol configured.
                ip_proto_str = ""

            # Setup ICMPv4/v6 type and code.
            if ip_proto == constants.PROTO_NAME_ICMP:
                icmp_type = "icmp_type=%s," % port_range_min
                icmp_code = "icmp_code=%s," % port_range_max
            elif ip_proto == constants.PROTO_NAME_ICMP_V6:
                icmp_type = "icmpv6_type=%s," % port_range_min
                icmp_code = "icmpv6_code=%s," % port_range_max
            else:
                icmp_type = ""
                icmp_code = ""

            # Source and destination IPs.
            if eth_type == constants.IPv4:
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
                            "eth_type=%(eth_type)s," \
                            "%(ip_proto)s" \
                            "NXM_OF_ETH_SRC[]=NXM_OF_ETH_DST[]," \
                            "NXM_OF_ETH_DST[]=NXM_OF_ETH_SRC[]," \
                            "%(ip_src)s" \
                            "%(ip_dst)s" \
                            "%(port_dst)s" \
                            "%(port_src)s" \
                            "%(icmp_type)s" \
                            "%(icmp_code)s" \
                            "output:NXM_OF_IN_PORT[])" % \
                            {'table': learn_action_table,
                             'priority': priority,
                             'idle_timeout': LEARN_IDLE_TIMEOUT,
                             'hard_timeout': LEARN_HARD_TIMEOUT,
                             'eth_type': eth_type_num,
                             'ip_proto': ip_proto_str,
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
                        'table': OF_INGRESS_STRIP_VLAN_TABLE}
            elif direction == INGRESS_DIRECTION:
                return "%(learn_actions)s," \
                       "strip_vlan,output:%(ofport)s" % \
                       {'learn_actions': learn_actions,
                        'ofport': vif_port.ofport}

        def _select_sg_rules_for_port(self, port):
            """Select rules from the security groups the port is member of.
            """
            port_sg_ids = port.get('security_groups', [])
            port_rules = []

            for sg_id in port_sg_ids:
                for rule in self.sg_rules.get(sg_id, []):
                    port_rules.extend(
                        self._expand_sg_rule_with_remote_ips(rule, port))
            return port_rules

        def _write_flows_per_port_match(self, flow, port_match):
            if port_match == "" or isinstance(flow[port_match], int):
                self._int_br.add_flow(**flow)
            elif isinstance(flow[port_match], list):
                for portm in flow[port_match]:
                    hp_flow = dict.copy(flow)
                    hp_flow[port_match] = portm
                    self._int_br.add_flow(**hp_flow)

        def _write_flows_per_ip(self, flow, rule, port, port_match):
            """Write the needed flows per each IP in the port.
            """
            vif_port = self._int_br_not_deferred.get_vif_port_by_id(
                port['device'])

            for fixed_ip in port['fixed_ips']:
                # IPv6 addresses not supported yet.
                if self._ip_version_from_address(fixed_ip) == constants.IPv6:
                    continue

                if rule['direction'] == EGRESS_DIRECTION:
                    flow['nw_src'] = fixed_ip
                elif rule['direction'] == INGRESS_DIRECTION:
                    flow['nw_dst'] = fixed_ip

                # Write learn actions.
                # Default protocol: "ip". Create high priority rules
                # for TCP and UDP protocols.
                if flow['proto'] == 'ip':
                    for proto in [constants.PROTO_NAME_TCP,
                                  constants.PROTO_NAME_UDP]:
                        hp_flow = dict.copy(flow)
                        hp_flow['proto'] = proto
                        hp_flow['actions'] = self._get_learn_action_rule(
                            rule['direction'],
                            OF_LEARNED_HIGH_PRIO,
                            "",
                            "",
                            rule['ethertype'],
                            proto,
                            vif_port)
                        LOG.debug("OFW rule %s flow %s", rule, hp_flow)
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
                LOG.debug("OFW rule %s flow %s", rule, flow)
                self._write_flows_per_port_match(flow, port_match)

        def _add_rules_flows(self, port):
            rules = self._select_sg_rules_for_port(port)
            for rule in rules:
                ethertype = rule['ethertype']
                # IPv6 not supported yet.
                if ethertype == constants.IPv6:
                    continue
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
                if protocol:
                    if protocol == constants.PROTO_NAME_ICMP and \
                                    ethertype == constants.IPv6:
                        flow["proto"] = ICMPv6
                    else:
                        flow["proto"] = protocol
                else:
                    # Default protocol: 'ip'
                    flow['proto'] = 'ip'

                # Port range.
                port_match = ""
                if (port_range_min and port_range_max and
                    protocol in [constants.PROTO_NAME_TCP,
                                 constants.PROTO_NAME_UDP]):
                    port_match = "%s_dst" % protocol
                    if port_range_max > port_range_min:
                        flow[port_match] = self._port_rule_masking(
                            port_range_min,
                            port_range_max)
                    else:
                        flow[port_match] = int(port_range_min)

                # Destination and source address.
                if dest_ip_prefix and dest_ip_prefix != "0.0.0.0/0":
                    flow["nw_dst"] = dest_ip_prefix

                if source_ip_prefix and source_ip_prefix != "0.0.0.0/0":
                    flow["nw_src"] = source_ip_prefix

                # Write flow.
                self._write_flows_per_ip(flow, rule, port, port_match)

        def _apply_flows(self):
            self._int_br.apply_flows()

        def prepare_port_filter(self, port):
            LOG.debug("OFW Preparing device (%s) filter: %s", port['device'],
                      port)
            vif_port = self._int_br_not_deferred.get_vif_port_by_id(
                port['device'])
            self._remove_flows(port, vif_port)
            self._add_base_flows(port, vif_port)
            self._filtered_ports[port['device']] = port

        def update_port_filter(self, port):
            LOG.debug("OFW Updating device (%s) filter: %s", port['device'],
                      port)
            if port['device'] not in self._filtered_ports:
                LOG.info(_('Attempted to update port filter which is not '
                           'filtered %s'), port['device'])
                return

            old_port = self._filtered_ports[port['device']]
            vif_port = self._int_br_not_deferred.get_vif_port_by_id(
                port['device'])
            self._remove_flows(old_port, vif_port)
            self._add_base_flows(port, vif_port)
            self._filtered_ports[port['device']] = port

        def remove_port_filter(self, port):
            LOG.debug("OFW Removing device (%s) filter: %s", port['device'],
                      port)
            if not self._filtered_ports.get(port['device']):
                LOG.info(_('Attempted to remove port filter which is not '
                           'filtered %r'), port)
                return
            vif_port = self._int_br_not_deferred.get_vif_port_by_id(
                port['device'])
            self._remove_flows(port, vif_port)
            self._filtered_ports.pop(port['device'])

        def filter_defer_apply_on(self):
            LOG.debug("OFW defer_apply_on")
            if not self._deferred:
                self._int_br = ovs_lib.DeferredOVSBridge(
                    self._int_br_not_deferred, full_ordered=True)
                self._deferred = True

        def filter_defer_apply_off(self):
            LOG.debug("OFW defer_apply_off")
            if self._deferred:
                self._int_br_not_deferred.dump_flows_for_table(
                    OF_ZERO_TABLE)
                self._int_br_not_deferred.dump_flows_for_table(
                    OF_EGRESS_TABLE)
                self._int_br_not_deferred.dump_flows_for_table(
                    OF_INGRESS_TABLE)
                for port in self.ports.values():
                    self._add_rules_flows(port)
                self._apply_flows()
                self._deferred = False

        def _ip_version_from_address(self, ip_string):
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
                return constants.IPv4
            if re.search(ipv6_pattern, ip_string) or \
                    re.search(ipv6_pattern_hexcompressed, ip_string) or \
                    re.search(ipv6_pattern_hex4dec, ip_string) or \
                    re.search(ipv6_pattern_hex4deccompressed, ip_string):
                return constants.IPv6
            raise ValueError(_('Illegal IP string address'))

        def _port_rule_masking(self, port_min, port_max):
            # Unsigned 16 bit MAX.
            MAX_UINT16 = 0xffff

            def create_mask(lsb_mask):
                return (MAX_UINT16 << int(math.floor(math.log(lsb_mask, 2)))) \
                       & MAX_UINT16

            def reduce_mask(mask, step=1):
                mask <<= step
                return mask & MAX_UINT16

            def increase_mask(mask, step=1):
                for index in range(0, step):
                    mask >>= 1
                    mask |= 0x8000
                return mask

            def hex_format(number):
                return format(number, '#06x')

            # Check port_max >= port_min.
            if port_max < port_min:
                raise ValueError(_("'port_max' is smaller than 'port_min'"))

            # Rules to be added to OVS.
            rules = []

            # Loop from the lower part. Increment port_min.
            bit_right = 1
            mask = MAX_UINT16
            t_port_min = port_min
            while True:
                # Obtain last significative bit.
                bit_min = port_min & bit_right
                # Take care of first bit.
                if bit_right == 1:
                    if bit_min > 0:
                        rules.append("%s" % (hex_format(t_port_min)))
                    else:
                        mask = create_mask(2)
                        rules.append("%s/%s" % (hex_format(t_port_min & mask),
                                                hex_format(mask)))
                elif bit_min == 0:
                    mask = create_mask(bit_right)
                    t_port_min += bit_right
                    # If the temporal variable we are using exceeds the
                    # port_max value, exit the loop.
                    if t_port_min > port_max:
                        break
                    rules.append("%s/%s" % (hex_format(t_port_min & mask),
                                            hex_format(mask)))

                # If the temporal variable we are using exceeds the
                # port_max value, exit the loop.
                if t_port_min > port_max:
                    break
                bit_right <<= 1

            # Loop from the higher part.
            bit_position = int(round(math.log(port_max, 2)))
            bit_left = 1 << bit_position
            mask = MAX_UINT16
            mask = reduce_mask(mask, bit_position)
            # Find the most significative bit of port_max, higher
            # than the most significative bit of port_min.
            while mask < MAX_UINT16:
                bit_max = port_max & bit_left
                bit_min = port_min & bit_left
                if bit_max > bit_min:
                    # Difference found.
                    break
                # Rotate bit_left to the right and increase mask.
                bit_left >>= 1
                mask = increase_mask(mask)

            while bit_left > 1:
                # Obtain next most significative bit.
                bit_left >>= 1
                bit_max = port_max & bit_left
                if bit_left == 1:
                    if bit_max == 0:
                        rules.append("%s" % (hex_format(port_max)))
                    else:
                        mask = create_mask(2)
                        rules.append("%s/%s" % (hex_format(port_max & mask),
                                                hex_format(mask)))
                elif bit_max > 0:
                    t_port_max = port_max - bit_max
                    mask = create_mask(bit_left)
                    rules.append("%s/%s" % (hex_format(t_port_max),
                                            hex_format(mask)))

            return rules
