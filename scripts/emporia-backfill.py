#!/usr/bin/env python3
"""Backfill electrical.emporia.* in InfluxDB from Emporia's cloud after an outage.

Emporia's cloud keeps minute data even when its API refuses pivac's polls, so a
gap in InfluxDB can be filled after the fact. This script rebuilds each minute
through the same code path pivac.Emporia uses live (get_device_list_usage with a
historical `instant`, paired CTs summed by circuit name, names sanitized), so
the measurements, tags and rounding match what signalk-to-influxdb2 writes.

A point stamped at HH:MM:55 carries the minute HH:MM-1, which is the same lag
the live poller has (checked against the chart series on 2026-09-16: 0.7 W
mean difference at a one-minute shift).

Run on the Pi in the venv. Dry run by default: writes line protocol to --out and
prints per-measurement counts and a main-vs-sum check. --write then feeds the
file to `influx write` using the CLI's active config.

    ~/pivac-venv/bin/python scripts/emporia-backfill.py \
        --start 2026-09-16T17:10:55Z --end 2026-09-16T19:51:55Z
    ~/pivac-venv/bin/python scripts/emporia-backfill.py ... --write

Choose --start as the first minute after the last live point and --end as the
last minute before the first live point (query the measurement's timestamps
around the gap first), so nothing is written on top of live data.
"""
import argparse
import datetime
import os
import subprocess
import sys
import time

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pivac.Emporia as E  # noqa: E402

CONTEXT = "vessels.urn:mrn:signalk:uuid:19a9eec1-e7f1-4768-81ff-81a22cf03027"
SOURCE = "ws.admin.XX"


def parse_ts(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=os.environ.get("PIVAC_CFG", "/etc/pivac/config.yml"))
    ap.add_argument("--start", required=True, help="first instant, UTC, e.g. 2026-09-16T17:10:55Z")
    ap.add_argument("--end", required=True, help="last instant, UTC")
    ap.add_argument("--out", default="/tmp/emporia-backfill.lp")
    ap.add_argument("--bucket", default="pivac")
    ap.add_argument("--context", default=CONTEXT)
    ap.add_argument("--source", default=SOURCE)
    ap.add_argument("--write", action="store_true", help="feed the file to influx write")
    args = ap.parse_args()

    from pyemvue.enums import Scale, Unit

    cfg = dict(yaml.safe_load(open(args.config))["pivac.Emporia"])
    cfg["token_file"] = "/tmp/emporia-backfill-tokens.json"   # never the service's token file
    vue = E._get_vue(cfg)
    cache = E._get_device_cache(vue, cfg)
    gids = list(cache.keys())

    t, end = parse_ts(args.start), parse_ts(args.end)
    lines, per, worst = [], {}, 0.0
    while t <= end:
        du = None
        for _ in range(3):
            try:
                du = vue.get_device_list_usage(deviceGids=gids, instant=t,
                                               scale=Scale.MINUTE.value, unit=Unit.KWH.value)
                break
            except Exception as e:
                print("retry", t, e)
                time.sleep(2)
        if du is None:
            print("FAILED", t)
            t += datetime.timedelta(minutes=1)
            continue
        for gid, ud in du.items():
            if ud is None or gid not in cache:
                print("no data", gid, t)
                continue
            panel, names = cache[gid]["name"], cache[gid]["channel_names"]
            watts = {}
            for cn, ch in ud.channels.items():
                if ch is None or ch.usage is None:
                    continue
                raw = names.get(cn) or getattr(ch, "name", None) or "channel_%s" % cn
                cname = E._sanitize(raw)
                watts[cname] = watts.get(cname, 0.0) + ch.usage * 60 * 1000
            # Emporia's balance is main minus every CT, so main = sum + balance.
            if "main" in watts:
                worst = max(worst, abs(watts["main"] - sum(watts.values()) + watts["main"]))
            for cname, w in watts.items():
                m = "electrical.emporia.%s.%s" % (panel, cname)
                lines.append("%s,context=%s,self=true,source=%s value=%s %d"
                             % (m, args.context, args.source, round(w, 1), int(t.timestamp() * 1000)))
                per[m] = per.get(m, 0) + 1
        t += datetime.timedelta(minutes=1)

    try:
        os.remove(cfg["token_file"])
    except OSError:
        pass
    with open(args.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("lines", len(lines), "->", args.out)
    for m, n in sorted(per.items()):
        print("  %-55s %d" % (m, n))
    print("worst |main - (circuits + balance)| = %.1f W" % worst)
    if not args.write:
        print("dry run; add --write to load it")
        return
    r = subprocess.run(["influx", "write", "--bucket", args.bucket, "--precision", "ms", "--file", args.out],
                       capture_output=True, text=True)
    print("influx write rc", r.returncode, r.stdout.strip(), r.stderr.strip()[:300])
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
