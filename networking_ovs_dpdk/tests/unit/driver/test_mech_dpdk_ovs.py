# Copyright (c) 2013 OpenStack Foundation
# All Rights Reserved.
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

from networking_ovs_dpdk.common import constants
from networking_ovs_dpdk.driver import mech_ovs_dpdk
from neutron.extensions import portbindings
from neutron.tests.unit.ml2 import _test_mech_agent as base


class OVSDPDKMechanismBaseTestCase(base.AgentMechanismBaseTestCase):
    VIF_TYPE = constants.VIF_TYPE_VHOST_USER
    VIF_DETAILS = {portbindings.CAP_PORT_FILTER: False,
                   constants.VHOST_USER_MODE:
                       constants.VHOST_USER_MODE_CLIENT,
                   constants.VHOST_USER_OVS_PLUG: True,
                   constants.VHOST_USER_DIR: "/tmp/"}

    AGENT_TYPE = constants.AGENT_TYPE_OVS_DPDK

    GOOD_MAPPINGS = {'fake_physical_network': 'fake_bridge'}
    GOOD_TUNNEL_TYPES = []
    GOOD_CONFIGS = {'bridge_mappings': GOOD_MAPPINGS,
                    'tunnel_types': GOOD_TUNNEL_TYPES}

    BAD_MAPPINGS = {'wrong_physical_network': 'wrong_bridge'}
    BAD_TUNNEL_TYPES = ['bad_tunnel_type']
    BAD_CONFIGS = {'bridge_mappings': BAD_MAPPINGS,
                   'tunnel_types': BAD_TUNNEL_TYPES}

    AGENTS = [{'alive': True,
               'configurations': GOOD_CONFIGS,
               'host': 'host'}]
    AGENTS_DEAD = [{'alive': False,
                    'configurations': GOOD_CONFIGS,
                    'host': 'dead_host'}]
    AGENTS_BAD = [{'alive': False,
                   'configurations': GOOD_CONFIGS,
                   'host': 'bad_host_1'},
                  {'alive': True,
                   'configurations': BAD_CONFIGS,
                   'host': 'bad_host_2'}]

    def setUp(self):
        super(OVSDPDKMechanismBaseTestCase, self).setUp()
        self.driver = mech_ovs_dpdk.OVSDPDKMechanismDriver()
        self.driver.initialize()


class OVSDPDKMechanismGenericTestCase(OVSDPDKMechanismBaseTestCase,
                                      base.AgentMechanismGenericTestCase):
    pass


class OVSDPDKMechanismLocalTestCase(OVSDPDKMechanismBaseTestCase,
                                    base.AgentMechanismLocalTestCase):
    pass


class OVSDPDKMechanismFlatTestCase(OVSDPDKMechanismBaseTestCase,
                                   base.AgentMechanismFlatTestCase):
    pass


class OVSDPDKMechanismVlanTestCase(OVSDPDKMechanismBaseTestCase,
                                   base.AgentMechanismVlanTestCase):
    pass
