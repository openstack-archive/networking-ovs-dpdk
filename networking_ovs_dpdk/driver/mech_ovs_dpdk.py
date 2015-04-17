# Copyright (c) 2014 Intel Corporation
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

import copy
import os

from oslo_log import log

from networking_ovs_dpdk.common import constants
from neutron.extensions import portbindings
from neutron.plugins.common import constants as npcc
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2.drivers import mech_agent

LOG = log.getLogger(__name__)


class OVSDPDKMechanismDriver(mech_agent.SimpleAgentMechanismDriverBase):
    """Attach to networks using OVS DPDK L2 agent.

    The OVSDPDKMechanismDriver integrates DPDK Accelerated OVS via the ml2
    plugin with the OVS DPDK L2 agent. Port binding with this driver
    requires the OVS DPDK agent to be running on the port's host,
    and that agent to have connectivity to at least one segment of the port's
    network.

    This driver support the qemu vhost-user interface
    with dpdk accelerated openvswitch datapaths.
    """

    def __init__(self):
        vif_details = {portbindings.CAP_PORT_FILTER: False,
                       constants.VHOST_USER_MODE:
                       constants.VHOST_USER_MODE_CLIENT,
                       constants.VHOST_USER_OVS_PLUG: True}

        super(OVSDPDKMechanismDriver, self).__init__(
            constants.AGENT_TYPE_OVS_DPDK,
            constants.VIF_TYPE_VHOST_USER,
            vif_details)

    def get_allowed_network_types(self, agent):
        return (agent['configurations'].get('tunnel_types', []) +
                [npcc.TYPE_LOCAL, npcc.TYPE_FLAT,
                npcc.TYPE_VLAN])

    def get_mappings(self, agent):
        return agent['configurations'].get('bridge_mappings', {})

    def try_to_bind_segment_for_agent(self, context, segment, agent):
        if self.check_segment_for_agent(segment, agent):
            sock_name = (constants.PORT_PREFIX + context.current['id'])[:14]
            vif_details = copy.copy(self.vif_details)
            vif_details[constants.VHOST_USER_SOCKET] = os.path.join(
                                        constants.VHOSTUSER_SOCKET_DIR,
                                        sock_name)
            context.set_binding(segment[api.ID],
                                self.vif_type,
                                vif_details)
            return True
        else:
            return False
