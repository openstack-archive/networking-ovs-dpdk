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

from oslo_log import log as logging
import six

from nova.i18n import _LW
from nova.scheduler import filters
from nova.scheduler.filters import extra_specs_ops as ops
from nova.scheduler.filters import utils


LOG = logging.getLogger(__name__)

_SCOPE = 'aggregate_instance_extra_specs'
FORCE_METADATA_CHECK = 'force_metadata_check'

ASTERISK = '*'
TILDE = '~'
EXCLAMATION = '!'
SENTINELS = [ASTERISK, TILDE, EXCLAMATION]

OR = '<or>'


class AggregateInstanceTypeFilter(filters.BaseHostFilter):
    """AggregateInstanceTypeFilter works with InstanceType records."""

    # Aggregate data and instance type does not change within a request
    run_filter_once_per_request = True

    @staticmethod
    def _read_sentinels(value):
        """Read sentinel values.

        :param value: value or set of values contained in a dictionary entry of
                      host aggregate metadata or instance extra specs.
        :type value: set or string, no other types will be allowed.

        Flavor extra specs values can contain also the following sentinel
        values:

        * (asterisk): may be used to specify that any value is valid, can be
                      used alone or inside a <or> junction.
        ~ (tilde): may be used to specify that a key may optionally be omitted,
                   can be used alone or inside a <or> junction.
        ! (exclamation): may be used to specify that the key must not be
                         present, it's exclusive.
        """

        if not isinstance(value, (set, basestring)):
            LOG.warning(_LW("Value passed to '_read_sentinels' is not valid: "
                            "%(value)s"), {'value': value})
            return False, None

        if not isinstance(value, set):
            value = {value}

        sentinels = set()
        other_values = set()
        for val in [val for val in value if val]:
            words = val.split(' ')
            op = words.pop(0)
            if op == '<or>':
                sentinels |= set([word for word in words
                                  if word in SENTINELS])
                other_values |= set([word for word in words if
                                    word not in SENTINELS + [OR]])
                if EXCLAMATION in sentinels and len(sentinels) > 1:
                    LOG.warning(_LW("Sentinel value '!' is exclusive and "
                                    "cannot be joint with other values"))
                    return False, None
            elif op in SENTINELS:
                sentinels.add(op)
            else:
                other_values.add(op)

        return sentinels, other_values

    def _execute_sentinel_actions(self, check_val, req_val):
        """Execute the filter actions depending on the possible sentinel
        values.

        :param check_val: set of values for a key stored in aggregate metadata
                          or flavor extra specs
        :type check_val: set
        :param req_val: string value of a key, stored in aggregate metadata or
                        in flavor extra specs, containing sentinel values
        :type req_val: str
        """
        sentinels, other_values = self._read_sentinels(req_val)
        if sentinels is False:
            return False

        if EXCLAMATION in sentinels:
            if check_val is None:
                return True
            else:
                return False
        if TILDE in sentinels and (not req_val or
                                   (req_val and not other_values)):
            return True
        if ASTERISK in sentinels:
            if check_val is not None and len(check_val) > 0:
                return True
            else:
                return False

        return None

    @staticmethod
    def _split_values(value):
        ret_value = set()
        if not value:
            return None

        if isinstance(value, basestring):
            value = {value}

        for element in value:
            words = element.split()
            if words and words[0] == OR:
                ret_value |= set([v.strip()
                                  for v in element.split(OR) if v])
            else:
                ret_value.add(element.strip())

        return ret_value

    def _check_by_instance_type(self, host_state, spec_obj, metadata):
        """Checks if the image extra_specs are satisfied in the host aggregate
        metadata.

        :param host_state: host information
        :type host_state: class nova.scheduler.host_manager.HostState
        :param spec_obj: filter_properties
        :type spec_obj: class nova.objects.request_spec.RequestSpec
        :param metadata: aggregate metadata
        :type metadata: dict of sets
        :return: True if the aggregate metadata fulfills the conditions defined
                 in the flavor extra specs.
        """

        instance_type = spec_obj.flavor
        if (not instance_type.obj_attr_is_set('extra_specs')
                or not instance_type.extra_specs):
            return True

        for key, especs_vals in six.iteritems(instance_type.extra_specs):
            scope = key.split(':', 1)
            scoped = False
            if len(scope) > 1:
                if scope[0] == _SCOPE:
                    key = scope[1]
                else:
                    scoped = True

            aggregate_vals = self._split_values(metadata.get(key))
            ret = self._execute_sentinel_actions(aggregate_vals, especs_vals)
            if ret is True:
                continue
            elif ret is False:
                return ret

            if not aggregate_vals and not scoped:
                LOG.debug("%(host_state)s fails instance type extra specs "
                          "requirements. Extra spec %(key)s is not in "
                          "aggregate metadata.",
                          {'host_state': host_state, 'key': key})
                return False
            elif not aggregate_vals and scoped:
                LOG.debug("Not mandatory extra_spec %(key)s is not in "
                          "aggregate metadata.", {'key': key})
                continue

            if not aggregate_vals:
                LOG.debug("%(host_state)s fails instance type extra specs "
                          "requirements. Extra spec %(key)s is not in "
                          "aggregate.", {'host_state': host_state, 'key': key})
                return False

            for aggregate_value in aggregate_vals:
                if ops.match(aggregate_value, especs_vals):
                    break
            else:
                LOG.debug("%(host_state)s fails instance type extra specs "
                          "requirements. '%(aggregate_vals)s' do not "
                          "match '%(req)s'",
                          {'host_state': host_state, 'req': especs_vals,
                           'aggregate_vals': aggregate_vals})
                return False
        return True

    def _check_by_aggregate(self, host_state, spec_obj, metadata):
        """Checks if the image extra_specs are satisfied in the host aggregate
        metadata.

        :param host_state: host information
        :type host_state: class nova.scheduler.host_manager.HostState
        :param spec_obj: filter_properties
        :type spec_obj: class nova.objects.request_spec.RequestSpec
        :param metadata: aggregate metadata
        :type metadata: dict of sets
        :return: True if the flavor extra specs fulfills the conditions defined
                 in the aggregate metadata.
        """

        if not metadata:
            return True
        instance_type = spec_obj.flavor
        extra_specs = instance_type.extra_specs if \
            instance_type.obj_attr_is_set('extra_specs') else {}

        for key, aggregate_vals in six.iteritems(metadata):
            scope = key.split(':', 1)
            scoped = False
            if len(scope) > 1:
                if scope[0] == _SCOPE:
                    key = scope[1]
                else:
                    scoped = True

            especs_vals = self._split_values(extra_specs.get(key))
            ret = self._execute_sentinel_actions(especs_vals, aggregate_vals)
            if ret is True:
                continue
            elif ret is False:
                return ret

            if not especs_vals and not scoped:
                LOG.debug("%(host_state)s fails instance type extra specs "
                          "requirements. Aggregate metadata key %(key)s is "
                          "not in extra specs",
                          {'host_state': host_state, 'key': key})
                return False
            elif not especs_vals and scoped:
                LOG.debug("Not mandatory aggregate metadata key %(key)s is "
                          "not in instance type extra specs", {'key': key})
                continue

            if not especs_vals:
                LOG.debug("%(host_state)s fails instance type extra_specs "
                          "requirements. Aggregate metadata key %(key)s is "
                          "not in instance type extra specs.",
                          {'host_state': host_state, 'key': key})
                return False

            for aggregate_value in aggregate_vals:
                for specs_value in especs_vals:
                    if ops.match(specs_value, aggregate_value):
                        break
                else:
                    break
            else:
                continue

            LOG.debug("%(host_state)s fails instance type extra specs "
                      "requirements. '%(aggregate_vals)s' do not "
                      "match '%(req)s'",
                      {'host_state': host_state, 'req': especs_vals,
                       'aggregate_vals': aggregate_vals})
            return False
        return True

    def host_passes(self, host_state, spec_obj):
        """Checks a host in an aggregate that metadata key/value match
           with image properties.

        """

        metadata = utils.aggregate_metadata_get_by_host(host_state)
        if FORCE_METADATA_CHECK in six.iterkeys(metadata):
            metadata.pop(FORCE_METADATA_CHECK)
            return self._check_by_aggregate(host_state, spec_obj, metadata)
        else:
            return self._check_by_instance_type(host_state, spec_obj, metadata)
