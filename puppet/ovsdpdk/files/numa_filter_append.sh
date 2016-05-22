#!/usr/bin/env bash

# This script will just check if in nova.conf taken from first argument
# NUMATopologyFilter is in place and append if needed

ORIG_FILTERS=`grep "#scheduler_default_filters" $1 | sed -e 's/\(.*\)=//'`

if [ -z "$ORIG_FILTERS" ]; then
  SEPARATOR=""
else
  SEPARATOR=","
fi

if [[ ! "$ORIG_FILTERS" =~ "NUMATopologyFilter" ]]; then
  sudo crudini --set $1 DEFAULT scheduler_default_filters "${ORIG_FILTERS}${SEPARATOR}NUMATopologyFilter"
fi
