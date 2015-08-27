# Copyright (c) 2012 OpenStack Foundation.
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

from oslo_config import cfg
from oslo_utils import importutils

from neutron.tests import base

from neutron.tests.unit.plugins.ml2.drivers.openvswitch.agent \
    import test_ovs_neutron_agent

NOTIFIER = 'neutron.plugins.ml2.rpc.AgentNotifierApi'
OVS_LINUX_KERN_VERS_WITHOUT_VXLAN = "3.12.0"

FAKE_MAC = '00:11:22:33:44:55'
FAKE_IP1 = '10.0.0.1'
FAKE_IP2 = '10.0.0.2'
cfg.CONF.use_stderr = False
OVSDPDK_AGENT_MOD = "networking_ovs_dpdk.agent.ovs_dpdk_neutron_agent"
DVR_MOD = "neutron.plugins.ml2.drivers.openvswitch.agent.ovs_dvr_neutron_agent"
FakeVif = test_ovs_neutron_agent.FakeVif
MockFixedIntervalLoopingCall = \
    test_ovs_neutron_agent.MockFixedIntervalLoopingCall


class OVSDPDKBase(object):
    def setUp(self):
        super(OVSDPDKBase, self).setUp()
        self.mod_agent = importutils.import_module(OVSDPDK_AGENT_MOD)
        self.mod_dvr_agent = importutils.import_module(DVR_MOD)
        self.mod_agent.OVSNeutronAgent = self.mod_agent.OVSDPDKNeutronAgent


class OVSDPDKAgentConfigTestBase(OVSDPDKBase, base.BaseTestCase):
    pass


class OVSDPDKOFCtlTestBase(OVSDPDKAgentConfigTestBase):
    _OFCTL_MOD = (
        'neutron.plugins.ml2.drivers.openvswitch.agent.openflow.'
        'ovs_ofctl')
    _BR_INT_CLASS = _OFCTL_MOD + '.br_int.OVSIntegrationBridge'
    _BR_TUN_CLASS = _OFCTL_MOD + '.br_tun.OVSTunnelBridge'
    _BR_PHYS_CLASS = _OFCTL_MOD + '.br_phys.OVSPhysicalBridge'

    def setUp(self):
        super(OVSDPDKOFCtlTestBase, self).setUp()
        self.br_int_cls = importutils.import_class(self._BR_INT_CLASS)
        self.br_phys_cls = importutils.import_class(self._BR_PHYS_CLASS)
        self.br_tun_cls = importutils.import_class(self._BR_TUN_CLASS)

    def _bridge_classes(self):
        return {
            'br_int': self.br_int_cls,
            'br_phys': self.br_phys_cls,
            'br_tun': self.br_tun_cls,
        }


class CreateAgentConfigMap(OVSDPDKAgentConfigTestBase,
                           test_ovs_neutron_agent.CreateAgentConfigMap):
    pass


class TestOVSDPDKNeutronAgent(test_ovs_neutron_agent.TestOvsNeutronAgent,
                              OVSDPDKBase):
    pass


class TestOVSDPDKNeutronAgentOFCtl(TestOVSDPDKNeutronAgent,
                                   OVSDPDKOFCtlTestBase):
    def test_setup_tunnel_port_invalid_ofport(self):
        self.skip("disabled due to logging error")

    def test_setup_tunnel_port_error_negative_df_disabled(self):
        self.skip("disabled due to loging error")


class AncillaryBridgesTest(test_ovs_neutron_agent.AncillaryBridgesTest,
                           OVSDPDKBase):
    pass


class AncillaryBridgesTestOFCtl(AncillaryBridgesTest,
                                OVSDPDKOFCtlTestBase):
    pass


class TestOVSDPDKDvrNeutronAgent(test_ovs_neutron_agent.TestOvsDvrNeutronAgent,
                                 OVSDPDKBase):
    pass


class TestOVSDPDKDvrNeutronAgentOFCtl(TestOVSDPDKDvrNeutronAgent,
                                      OVSDPDKOFCtlTestBase):
    pass


class TestValidateTunnelLocalIP(
    test_ovs_neutron_agent.TestValidateTunnelLocalIP, OVSDPDKBase):
    pass
