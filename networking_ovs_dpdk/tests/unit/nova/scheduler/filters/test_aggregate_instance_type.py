# Copyright (c) 2016, Intel Corporation.
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

import logging

import mock

from nova import objects
from networking_ovs_dpdk.nova.scheduler.filters import (aggregate_instance_type
                                                        as agg_ins_type)
from nova import test
from nova.tests.unit.scheduler import fakes


class TestAggregateExtraSpecsFilter(test.NoDBTestCase):

    def setUp(self):
        super(TestAggregateExtraSpecsFilter, self).setUp()
        self.filt_cls = agg_ins_type.AggregateInstanceTypeFilter()

    def _create_host_state(self,
                           host=None,
                           node=None,
                           capabilities=None,
                           aggr_metadata=None):
        host = 'host1' if host is None else host
        node = 'node1' if node is None else node
        capabilities = {'opt1': 1} if capabilities is None else capabilities
        host_state = fakes.FakeHostState(host, node, capabilities)
        if not isinstance(aggr_metadata, list):
            aggr_metadata = [aggr_metadata]
        for aggr_metadata_item in aggr_metadata:
            aggr = objects.Aggregate(context='test')
            aggr.metadata = aggr_metadata_item
            host_state.aggregates.append(aggr)
        return host_state

    def _do_test_aggr_filter_extra_specs(self, extra_specs, aggr_metadata,
                                         passes):
        spec_obj = objects.RequestSpec(
            context=mock.sentinel.ctx,
            flavor=objects.Flavor(memory_mb=1024, extra_specs=extra_specs))
        capabilities = {'free_ram_mb': 1024}
        host = self._create_host_state(capabilities=capabilities,
                                       aggr_metadata=aggr_metadata)
        assertion = self.assertTrue if passes else self.assertFalse
        assertion(self.filt_cls.host_passes(host, spec_obj))

    @mock.patch('nova.scheduler.filters.utils.aggregate_metadata_get_by_host')
    def test_passes_no_extra_specs(self, agg_mock):
        capabilities = {'opt1': 1, 'opt2': 2}
        spec_obj = objects.RequestSpec(
            context=mock.sentinel.ctx,
            flavor=objects.Flavor(memory_mb=1024))
        host = self._create_host_state(capabilities=capabilities)
        self.assertTrue(self.filt_cls.host_passes(host, spec_obj))
        self.assertTrue(agg_mock.called)

    @mock.patch('nova.scheduler.filters.utils.aggregate_metadata_get_by_host')
    def test_passes_empty_extra_specs(self, agg_mock):
        capabilities = {'opt1': 1, 'opt2': 2}
        spec_obj = objects.RequestSpec(
            context=mock.sentinel.ctx,
            flavor=objects.Flavor(memory_mb=1024, extra_specs={}))
        host = fakes.FakeHostState('host1', 'node1', capabilities)
        self.assertTrue(self.filt_cls.host_passes(host, spec_obj))
        self.assertTrue(agg_mock.called)

    # Sentinel checks.
    @mock.patch.object(logging.LoggerAdapter, 'warning')
    def test_exclamation_exclusive(self, mock_logging):
        aggr_metadata = {
            'opt1': '1',
        }
        extra_specs = {
            'opt1': '<or> ! <or> *',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=False)
        mock_logging.assert_called_with("Sentinel value '!' is exclusive and "
                                        "cannot be joint with other values")

    def test_read_sentinels(self):
        # Sentinels alone.
        self.assertEqual(({'!'}, set()),
            self.filt_cls._read_sentinels('!'))
        self.assertEqual(({'*'}, set()),
            self.filt_cls._read_sentinels('*'))
        self.assertEqual(({'~'}, set()),
            self.filt_cls._read_sentinels('~'))
        # Value strings without sentinels.
        self.assertEqual((set(), {'value'}),
            self.filt_cls._read_sentinels('value'))
        self.assertEqual((set(), set()),
            self.filt_cls._read_sentinels(''))
        self.assertEqual((False, None),
            self.filt_cls._read_sentinels(None))
        # Combination of sentinels.
        self.assertEqual(({'~'}, {'value'}),
            self.filt_cls._read_sentinels('<or> value <or> ~'))
        self.assertEqual(({'~', '*'}, {'value'}),
            self.filt_cls._read_sentinels('<or> value <or> ~ <or> *'))
        self.assertEqual((False, None),
            self.filt_cls._read_sentinels('<or> value <or> ! <or> *'))

    # _split_value checks.
    def test_split_values(self):
        def _check(ref_vals, input_vals):
            self.assertEqual(ref_vals, self.filt_cls._split_values(input_vals))

        # Test string input.
        _check({'val_1'}, 'val_1')
        # Test set input.
        _check({'val_1', 'val_2'}, {'val_1', 'val_2'})
        # Remove blank spaces.
        _check({'val_1'}, 'val_1 ')
        _check({'val_1'}, ' val_1')
        _check({'val_1'}, ' val_1 ')
        _check({'val_1', 'val_2', 'val_3'}, {' val_1', 'val_2 ', ' val_3 '})
        # Test <or> junction inside a string; string must start with <or>.
        _check({'val_1', 'val_2'}, '<or> val_1 <or> val_2')
        _check({'val_1', 'val_2', 'val_3'}, {'val_3', '<or> val_1 <or> val_2'})
        _check({'val_1 <or> val_2'}, 'val_1 <or> val_2')
        _check({'val_1', 'val_2', 'val_3', 'val_4'},
               {'val_1', '<or> val_1 <or> val_2', ' val_3 ',
                '<or> val_3 <or>  val_4 '})

    # No 'force_metadata_check' value in aggregate metadata.
    def test_check_by_instance_no_metadata(self):
        aggr_metadata = {}
        extra_specs = {
            'opt1': '1',
            'aggregate_instance_extra_specs:opt2': '2',
            'trust:trusted_host': 'true',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=False)

    def test_check_by_instance_correct_metadata(self):
        aggr_metadata = {
            'opt1': '1',
            'opt2': '2'
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '2',
            'trust:trusted_host': 'true',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_instance_scoped_key_present(self):
        aggr_metadata = {
            'opt1': '1',
            'opt2': '2'
        }
        extra_specs = {
            'opt1': '1',
            'aggregate_instance_extra_specs:opt2': '2',
            'trust:trusted_host': 'true',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_instance_scoped_no_present(self):
        aggr_metadata = {
            'opt1': '1'
        }
        extra_specs = {
            'opt1': '1',
            'aggregate_instance_extra_specs:opt2': '2',
            'trust:trusted_host': 'true',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=False)

    def test_check_by_instance_no_scoped_key_present(self):
        aggr_metadata = {
            'opt1': '1',
            'opt2': '2',
            'trust:trusted_host': 'true',
        }
        extra_specs = {
            'opt1': '1',
            'aggregate_instance_extra_specs:opt2': '2',
            'trust:trusted_host': 'true',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_instance_no_scoped_key_no_present(self):
        aggr_metadata = {
            'opt1': '1',
            'opt2': '2',
        }
        extra_specs = {
            'opt1': '1',
            'aggregate_instance_extra_specs:opt2': '2',
            'trust:trusted_host': 'true',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_instance_sentinel_asterisk_key_present(self):
        aggr_metadata = {
            'opt1': '1',
            'opt2': '2',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '*',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_instance_sentinel_asterisk_key_not_present(self):
        aggr_metadata = {
            'opt1': '1',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '*',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=False)

    def test_check_by_instance_sentinel_any_key_present(self):
        aggr_metadata = {
            'opt1': '1',
            'opt2': '2',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '~',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_instance_sentinel_any_and_other_value_key_present(self):
        aggr_metadata1 = {
            'opt1': '1',
            'opt2': '2',
        }
        aggr_metadata2 = {
            'opt1': '1',
            'opt2': '20',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '<or> ~ <or> 2',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata1, passes=True)
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata2, passes=False)

    def test_check_by_instance_sentinel_any_key_not_present(self):
        aggr_metadata = {
            'opt1': '1',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '~',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_instance_sentinel_exclamation_key_present(self):
        aggr_metadata = {
            'opt1': '1',
            'opt2': '2',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '!',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=False)

    def test_check_by_instance_sentinel_exclamation_key_not_present(self):
        aggr_metadata = {
            'opt1': '1',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '!',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_instance_multiple_aggregates(self):
        aggr1 = {
            'opt2': '20',
        }
        aggr2 = {
            'opt1': '10',
        }
        extra_specs = {
            'opt1': '10',
            'opt2': '20',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr1, passes=False)
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr2, passes=False)
        self._do_test_aggr_filter_extra_specs(
            extra_specs, [aggr1, aggr2], passes=True)

    # 'force_metadata_check' value in aggregate metadata.
    def test_check_by_aggregate_no_extra_specs(self):
        aggr_metadata = {
            'force_metadata_check': '',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '2',
            'trust:trusted_host': 'true',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_aggregate_correct_extra_specs(self):
        aggr_metadata = {
            'force_metadata_check': '',
            'opt1': '1',
            'opt2': '2',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '2',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_aggregate_scoped_key_present(self):
        aggr_metadata = {
            'force_metadata_check': '',
            'opt1': '1',
            'aggregate_instance_extra_specs:opt2': '2',
            'trust:trusted_host': 'true',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '2',
            'trust:trusted_host': 'true',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_aggregate_scoped_key_not_present(self):
        aggr_metadata = {
            'force_metadata_check': '',
            'opt1': '1',
            'aggregate_instance_extra_specs:opt2': '2',
            'trust:trusted_host': 'true',
        }
        extra_specs = {
            'opt1': '1',
            'trust:trusted_host': 'true',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=False)

    def test_check_by_aggregate_sentinel_asterisk_key_present(self):
        aggr_metadata = {
            'force_metadata_check': '',
            'opt1': '1',
            'opt2': '*',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '2',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_aggregate_sentinel_asterisk_key_not_present(self):
        aggr_metadata = {
            'force_metadata_check': '',
            'opt1': '1',
            'opt2': '*',
        }
        extra_specs = {
            'opt1': '1',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=False)

    def test_check_by_aggregate_sentinel_any_key_present(self):
        aggr_metadata = {
            'force_metadata_check': '',
            'opt1': '1',
            'opt2': '~',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '2',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_aggregate_sentinel_any_key_not_present(self):
        aggr_metadata = {
            'force_metadata_check': '',
            'opt1': '1',
            'opt2': '~',
        }
        extra_specs = {
            'opt1': '1',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_aggregate_sentinel_any_and_other_value_key_present(self):
        aggr_metadata = {
            'force_metadata_check': '',
            'opt1': '1',
            'opt2': '<or> ~ <or> 2',
        }
        extra_specs1 = {
            'opt1': '1',
            'opt2': '2',
        }
        extra_specs2 = {
            'opt1': '1',
            'opt2': '20',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs1, aggr_metadata, passes=True)
        self._do_test_aggr_filter_extra_specs(
            extra_specs2, aggr_metadata, passes=False)

    def test_check_by_aggregate_sentinel_exclamation_key_present(self):
        aggr_metadata = {
            'force_metadata_check': '',
            'opt1': '1',
            'opt2': '!',
        }
        extra_specs = {
            'opt1': '1',
            'opt2': '2',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=False)

    def test_check_by_aggregate_sentinel_exclamation_key_not_present(self):
        aggr_metadata = {
            'force_metadata_check': '',
            'opt1': '1',
            'opt2': '!',
        }
        extra_specs = {
            'opt1': '1',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata, passes=True)

    def test_check_by_aggregate_multiple_aggregates(self):
        aggr_metadata1 = {
            'force_metadata_check': '',
            'opt1': '1',
        }
        aggr_metadata2 = {
            'force_metadata_check': '',
            'opt2': '2',
        }

        extra_specs = {
            'opt1': '1',
            'opt2': '2',
        }
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata1, passes=True)
        self._do_test_aggr_filter_extra_specs(
            extra_specs, aggr_metadata2, passes=True)
        self._do_test_aggr_filter_extra_specs(
            extra_specs, [aggr_metadata1, aggr_metadata2], passes=True)
