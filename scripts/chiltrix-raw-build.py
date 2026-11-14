#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""Forward-fill a chiltrix-raw-fetch.sh export to one row per sweep, as raw register values.

pivac.ChiltrixModbus sends a register only when it changes (and every refresh_s), and sends
registerCount every sweep, so each registerCount point marks a sweep and the last value of every
register is its value at that sweep. The named paths are converted back to raw register contents.
Output columns: utc, local (EST), registerCount, r0..r146, r200..r286. This is the format Chiltrix
support asked for. Usage: chiltrix-raw-build.py raw.csv.gz OUT.csv
"""
import csv, gzip, sys, datetime as dt
from collections import defaultdict

NAMED = {"switchOn": (140, "int"), "operatingMode": (141, "int"), "coolingTarget": (142, "wholeK"),
         "heatingTarget": (143, "wholeK"), "dhwTarget": (144, "wholeK"), "heatingAuMode": (145, "int"),
         "dhwAuMode": (146, "int"), "ambientTemp": (202, "tempK"), "outletTemp": (205, "tempK"),
         "waterFlow": (213, "div10"), "compressorHz": (227, "int"), "inputCurrent": (256, "div10"),
         "inletTemp": (281, "tempK")}
ADDRS = list(range(0, 147)) + list(range(200, 287))

def raw(kind, v):
    if kind == "tempK": return int(round((v - 273.15) * 10))
    if kind == "wholeK": return int(round(v - 273.15))
    if kind == "div10": return int(round(v * 10))
    return int(round(v))

def when(t):
    t = t.rstrip("Z")
    a, _, b = t.partition(".")
    return dt.datetime.strptime(a, "%Y-%m-%dT%H:%M:%S") + dt.timedelta(microseconds=int((b + "000000")[:6]))

def main(src, out):
    by_t, sweeps = defaultdict(dict), {}
    for row in csv.reader(gzip.open(src, "rt")):
        if len(row) != 6 or row[3] == "_time": continue
        t, v, name = row[3], float(row[4]), row[5].split("hvac.chiller.chiltrix.", 1)[1]
        if name == "registerCount": sweeps[t] = int(v)
        elif name.startswith("raw.r"): by_t[t][int(name[5:])] = int(round(v))
        elif name in NAMED: by_t[t][NAMED[name][0]] = raw(NAMED[name][1], v)
    state, n = {}, 0
    with open(out, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["utc", "local", "registerCount"] + ["r%d" % a for a in ADDRS])
        for t in sorted(set(by_t) | set(sweeps), key=when):
            state.update(by_t.get(t, {}))
            if t not in sweeps or any(a not in state for a in ADDRS): continue
            u = when(t); loc = u - dt.timedelta(hours=5)
            w.writerow([u.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3], loc.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " EST",
                        sweeps[t]] + [state[a] for a in ADDRS]); n += 1
    print("rows", n)

if __name__ == "__main__":
    main(*sys.argv[1:3])
