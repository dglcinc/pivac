#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""Tables behind docs/chiltrix-heating-control-analysis.md, from a chiltrix-raw-build.py CSV.

Prints every fault (r284), every low-speed period of 100 s or more (compressor 30-41 Hz) with its
lowest valve opening and flow and its highest pressure, and every mid-run jump of the commanded
frequency (r228) by 20 Hz or more with the peak input current. Usage: chiltrix-heating-events.py CSV
"""
import csv, sys, datetime as dt

COLS = (200, 202, 203, 205, 210, 213, 227, 228, 240, 245, 248, 256, 281, 284)
def main(path):
    rd = csv.reader(open(path)); head = next(rd); ix = {a: head.index("r%d" % a) for a in COLS}
    T, R = [], {a: [] for a in COLS}
    for row in rd:
        T.append(dt.datetime.strptime(row[0], "%Y-%m-%dT%H:%M:%S.%f"))
        for a in COLS: R[a].append(int(row[ix[a]]))
    est = lambda i: (T[i] - dt.timedelta(hours=5)).strftime("%m-%d %H:%M:%S")
    hz, f, n = R[227], R[284], len(T)
    print("faults (r284):")
    for i in range(1, n):
        if f[i] and not f[i - 1]: print(" ", est(i), f[i])
    print("low-speed periods >= 100 s: start, s, min r240, min flow L/min, min fan, r210 start -> max, ambient C, inlet C at end")
    i = 0
    while i < n:
        if 30 <= hz[i] <= 41 and R[205][i] > R[281][i] and R[240][i] < 470:
            j = i
            while j < n and 0 < hz[j] <= 41: j += 1
            s = (T[j - 1] - T[i]).total_seconds()
            if s >= 100:
                print("  %s %5.0f %4d %5.1f %4d  %4d -> %4d  %5.1f %5.1f %s" % (est(i), s, min(R[240][i:j]), min(R[213][i:j]) / 10,
                      min(R[245][i:j]), R[210][i], max(R[210][i:j]), R[202][i] / 10, R[281][j - 1] / 10, "P1" if 2 in f[i:j + 20] else ""))
            i = j
        i += 1
    print("mid-run jumps of r228 by >= 20 Hz in 30 s to 65 Hz or more: time, from, to, inlet C, peak A, max r210, fault")
    i = 30
    while i < n:
        if hz[i - 30] > 30 and R[228][i] - R[228][i - 30] >= 20 and R[228][i] >= 65:
            print("  %s %3d %3d %5.1f %5.1f %5d %3d" % (est(i), R[228][i - 30], max(R[228][i:i + 30]), R[281][i] / 10,
                  max(R[256][i:i + 60]) / 10, max(R[210][i:i + 60]), max(f[i:i + 70])))
            i += 120
        i += 1

if __name__ == "__main__":
    main(sys.argv[1])
