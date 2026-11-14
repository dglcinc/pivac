#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
#
# Run on the Pi. Exports every hvac.chiller.chiltrix.* point between two UTC hours, one hour per
# query (a wider query is too heavy for the Pi), as the change-only points InfluxDB holds.
# Usage: sh chiltrix-raw-fetch.sh 2026-11-12T10 2026-11-14T15 [OUTDIR]
# Then copy OUTDIR/raw.csv.gz to the Mac and run scripts/chiltrix-raw-build.py on it.
set -e
A=$1; B=$2; O=${3:-/tmp/cxraw}; mkdir -p "$O"; : > "$O/raw.csv"
python3 - "$A" "$B" > "$O/hours.txt" <<'PY'
import sys
from datetime import datetime, timedelta
t, e = (datetime.strptime(x, "%Y-%m-%dT%H") for x in sys.argv[1:3])
while t < e:
    print(t.strftime("%Y-%m-%dT%H:%M:%SZ"), (t + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")); t += timedelta(hours=1)
PY
while read a b; do
  influx query --raw "from(bucket:\"pivac\") |> range(start: $a, stop: $b) |> filter(fn:(r)=> r._field==\"value\" and r._measurement =~ /^hvac\.chiller\.chiltrix\./) |> keep(columns:[\"_time\",\"_value\",\"_measurement\"])" \
    | grep -v '^#' | grep -v '^$' | grep -v '^,result' >> "$O/raw.csv"
  echo "$a $(wc -l < "$O/raw.csv")"
done < "$O/hours.txt"
gzip -f "$O/raw.csv"; echo DONE
