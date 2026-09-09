#!/usr/bin/env python3
"""Daily boiler gas input against outdoor temperature, from the Sentry record in InfluxDB.

Runs on the Pi (needs the `influx` CLI configured for the pivac bucket). For each day it
integrates `hvac.boiler.sentry.gasInputValue` through the Ti200 display-to-input chart in the
NTI Trinity Ti100-200 manual (page 48), splits DHW-priority minutes from space heating, sums
the hours the status word reads `Run`, and regresses space-heating input on the RedLink outdoor
mean. The regression is what docs/chiltrix-shoulder-season-heating-plan.md §8 rests on.

    python3 scripts/boiler-heat-by-outdoor.py [--start 2026-04-01] [--stop 2026-05-21]
"""
import argparse
import bisect
import collections
import csv
import datetime as dt
import io
import math
import subprocess

# Ti200 curve read from the manual's chart: (LED display, kBTU/h input).
CHART = [(40, 25), (48, 40), (65, 65), (90, 105), (115, 140), (140, 160),
         (165, 170), (190, 183), (215, 193), (240, 199)]


def mbh(v):
    """Display value to kBTU/h input, piecewise linear on CHART."""
    if v < 30:
        return 0.0
    if v < 40:
        return 25.0
    if v >= 240:
        return 199.0
    for (a, x), (b, y) in zip(CHART, CHART[1:]):
        if a <= v <= b:
            return x + (y - x) * (v - a) / (b - a)
    return 0.0


def pull(meas, start, stop):
    q = (f'from(bucket:"pivac") |> range(start: {start}, stop: {stop}) '
         f'|> filter(fn:(r)=> r._measurement=="{meas}" and r._field=="value") '
         f'|> keep(columns:["_time","_value"])')
    out = subprocess.run(["influx", "query", "--raw", q], capture_output=True, text=True).stdout
    rows = []
    for r in csv.reader(io.StringIO(out)):
        if len(r) >= 5 and r[3].startswith("20"):
            rows.append((dt.datetime.fromisoformat(r[3].replace("Z", "+00:00")), r[4]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-04-01")
    ap.add_argument("--stop", default="2026-05-21")
    ap.add_argument("--max-t", type=float, default=64.0,
                    help="exclude days warmer than this from the regression")
    args = ap.parse_args()

    gas = pull("hvac.boiler.sentry.gasInputValue", args.start, args.stop)
    dhw = pull("hvac.boiler.sentry.dhwPriority", args.start, args.stop)
    status = pull("hvac.boiler.sentry.status", args.start, args.stop)
    outdoor = pull("environment.outside.thermostat.temperature", args.start, args.stop)

    dhw_t = [t for t, _ in dhw]
    dhw_v = [float(v) for _, v in dhw]

    def is_dhw(t):
        i = bisect.bisect_right(dhw_t, t) - 1
        return i >= 0 and dhw_v[i] >= 0.5

    days = collections.defaultdict(lambda: dict(sp=0.0, dh=0.0, run=0.0, fire=0.0, ot=[]))
    for (t, v), (t2, _) in zip(gas, gas[1:]):
        g = float(v)
        if g <= 0:
            continue
        gap = min((t2 - t).total_seconds(), 30.0)
        k = mbh(g) * gap / 3600.0
        d = days[t.date().isoformat()]
        if is_dhw(t):
            d["dh"] += k
        else:
            d["sp"] += k
            d["fire"] += gap / 3600.0
    for (t, v), (t2, _) in zip(status, status[1:]):
        if v == "Run":
            days[t.date().isoformat()]["run"] += min((t2 - t).total_seconds(), 30.0) / 3600.0
    for t, v in outdoor:
        days[t.date().isoformat()]["ot"].append((float(v) - 273.15) * 9 / 5 + 32)

    print("day,outF,space_kBTU_in,dhw_kBTU_in,gas_fire_h,status_run_h")
    xs, ys = [], []
    for day in sorted(days):
        d = days[day]
        if not d["ot"]:
            continue
        o = sum(d["ot"]) / len(d["ot"])
        print(f"{day},{o:.1f},{d['sp']:.0f},{d['dh']:.0f},{d['fire']:.1f},{d['run']:.1f}")
        if o < args.max_t and d["run"] > 0:
            xs.append(o)
            ys.append(d["sp"])

    n = len(xs)
    if n < 3:
        return
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    a = my - b * mx
    se = math.sqrt(sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys)) / (n - 2))
    print(f"REG n={n}: space_kBTU_in/day = {a:.0f} {b:+.1f}*T  (zero at {-a / b:.1f} F, resid sd {se:.0f})")
    for T in (35, 40, 45, 50, 55, 60):
        print(f"  T={T}: {a + b * T:.0f} kBTU/day in = {(a + b * T) / 100:.2f} therms")


if __name__ == "__main__":
    main()
