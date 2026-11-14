#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
#
# Run on the Pi. Exports per-minute series for scripts/chiltrix-heat-by-outdoor.py, one measurement
# at a time (a wide pivot over weeks of data is too heavy for the Pi). Usage:
#   sh chiltrix-heat-fetch.sh [START] [OUTDIR]   e.g. 2026-10-29T18:00:00Z /tmp/cop
# then copy OUTDIR to the Mac and run the analysis on it.
OUT=${2:-/tmp/cop}; mkdir -p $OUT
START=${1:-2026-10-29T18:00:00Z}
for m in hvac.chiller.chiltrix.inletTemp hvac.chiller.chiltrix.outletTemp hvac.chiller.chiltrix.waterFlow \
         hvac.chiller.chiltrix.compressorHz hvac.chiller.chiltrix.inputCurrent electrical.emporia.house.chiltrix \
         environment.outside.thermostat.temperature electrical.ac.switch.utility.HPCALL.statenum \
         electrical.ac.switch.utility.BLR.statenum electrical.ac.switch.utility.DHWX.statenum \
         electrical.ac.switch.utility.HPHEAT.statenum hvac.boiler.sentry.gasInputValue \
         environment.inside.thermostat.KIDS_ROOM.temperature environment.inside.thermostat.KIDS_ROOM.heatset \
         environment.inside.thermostat.MASTER_BR.temperature environment.inside.thermostat.MASTER_BR.heatset \
         environment.inside.thermostat.GREAT_ROOM.temperature environment.inside.thermostat.GREAT_ROOM.heatset \
         environment.inside.thermostat.KITCHEN.temperature environment.inside.thermostat.KITCHEN.heatset \
         environment.inside.thermostat.DSTRS_FAM_ROOM.temperature environment.inside.thermostat.DSTRS_FAM_ROOM.heatset ; do
  influx query --raw "from(bucket:\"pivac\") |> range(start: $START) |> filter(fn:(r)=> r._measurement==\"$m\" and r._field==\"value\") |> aggregateWindow(every: 1m, fn: mean, createEmpty: true) |> fill(usePrevious: true) |> keep(columns:[\"_time\",\"_value\"])" > $OUT/$m.csv 2>$OUT/$m.err
  echo "$m $(wc -l < $OUT/$m.csv)"
done
echo DONE
