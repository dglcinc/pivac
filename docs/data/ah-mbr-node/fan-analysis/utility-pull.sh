mkdir -p /tmp/upull && cd /tmp/upull
P=environment.inside.hvac.ah.utility
for m in $P.fan.airflow $P.fan.rpm $P.call.g $P.call.y1 $P.call.y2 $P.call.w1 $P.call.w2 $P.call.e environment.inside.hvac.LOOPB_SUP.temperature environment.inside.hvac.LOOPB_RET.temperature environment.inside.hvac.IN.temperature environment.inside.thermostat.DSTRS_FAM_ROOM.statenum environment.inside.thermostat.DSTRS_FAM_ROOM.temperature environment.inside.thermostat.DSTRS_FAM_ROOM.humidity environment.inside.thermostat.DSTRS_FAM_ROOM.heatset environment.inside.thermostat.DSTRS_FAM_ROOM.coolset environment.inside.thermostat.KITCHEN.statenum environment.inside.thermostat.GREAT_ROOM.statenum environment.outside.thermostat.temperature electrical.ac.switch.utility.HPHEAT.statenum electrical.ac.switch.utility.HPCOOL.statenum electrical.ac.switch.utility.HPCALL.statenum; do
 influx query "from(bucket:\"pivac\") |> range(start:2026-10-24T22:00:00Z) |> filter(fn:(r)=>r._measurement==\"$m\" and r._field==\"value\") |> aggregateWindow(every:1m,fn:mean,createEmpty:false) |> keep(columns:[\"_time\",\"_value\"])" --raw 2>/dev/null | grep -v "^#\|^$\|,result" | cut -d, -f4,5 > $m.csv
 sleep 1
done
for f in $P.fan.stored.*; do :; done
tar czf /tmp/upull.tgz *.csv; wc -l *.csv | tail -1
