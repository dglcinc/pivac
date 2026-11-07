# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
cd /tmp && mkdir -p mbrpull && cd mbrpull
for m in environment.inside.hvac.ah.mbr.water.supply.temperature environment.inside.hvac.ah.mbr.water.return.temperature environment.inside.hvac.ah.mbr.air.supply.temperature environment.inside.hvac.ah.mbr.air.return.temperature environment.inside.hvac.ah.mbr.y2 environment.inside.thermostat.MASTER_BR.statenum environment.inside.thermostat.MASTER_BR.temperature environment.inside.thermostat.MASTER_BR.heatset environment.inside.thermostat.MASTER_BR.coolset environment.inside.thermostat.MASTER_BR.humidity environment.outside.thermostat.temperature environment.inside.hvac.LOOPA_SUP.temperature environment.inside.hvac.LOOPA_RET.temperature environment.inside.hvac.IN.temperature electrical.ac.switch.utility.HPCALL.statenum electrical.ac.switch.utility.HPHEAT.statenum electrical.ac.switch.utility.HPCOOL.statenum; do
 influx query "from(bucket:\"pivac\") |> range(start:2026-10-20T20:00:00Z) |> filter(fn:(r)=>r._measurement==\"$m\" and r._field==\"value\") |> aggregateWindow(every:1m,fn:mean,createEmpty:false) |> keep(columns:[\"_time\",\"_value\"])" --raw 2>/dev/null | grep -v "^#\|^$\|,result" | cut -d, -f4,5 > $m.csv
 wc -l $m.csv
 sleep 1
done
tar czf - *.csv > /tmp/mbrpull.tgz
