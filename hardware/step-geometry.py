#!/usr/bin/env python3
"""Extract the board geometry from the Phoenix RPI-BC STEP models.

Reads the AP214 STEP files in hardware/vendor/ and prints, for each board, the
outline, the hole grid, the off-grid connector holes and the restricted areas,
in the frame the build docs use (docs/rpi-io-board-design.md §1 and
docs/ds18b20-bus-topology.md §1): column 1 on the left, row 1 at the top, the
component side facing the viewer, y increasing downward as in KiCad.

The STEP frames differ from the doc frames. The INT model is mirrored in x
(doc col = 24 - STEP col); the EXT model is not. Both put the board's bottom
(solder) face at z = 0 and the top at z = 1.6, and both carry the housing's
restricted areas as a 0.02 mm solid on the z = 0 face, which is where the
housing ribs touch the board.

Usage: python3 hardware/step-geometry.py hardware/vendor/*.stp
"""
import collections
import math
import re
import sys

PITCH = 2.54


def load(path):
    text = open(path, encoding="latin-1").read()
    text = text[text.index("DATA;"):]
    ents = {}
    for m in re.finditer(r"#(\d+)\s*=\s*([A-Z_0-9]+)\s*\((.*?)\)\s*;", text, re.S):
        ents[int(m.group(1))] = (m.group(2), m.group(3).replace("\n", ""))
    return ents


def nums(a):
    return [float(x) for x in re.findall(r"-?\d+\.?\d*(?:E[+-]?\d+)?", a)]


def refs(a):
    return [int(x) for x in re.findall(r"#(\d+)", a)]


def circles(ents, pts):
    out = []
    for t, a in ents.values():
        if t != "CIRCLE":
            continue
        r = refs(a)
        radius = nums(a.rsplit(",", 1)[1])[0]
        ar = refs(ents[r[0]][1])
        c = pts[ar[0]]
        out.append((round(radius, 3), round(c[0], 3), round(c[1], 3), round(c[2], 3)))
    return out


def lines_at(ents, pts, z, min_len=0.3):
    segs = set()
    for t, a in ents.values():
        if t != "EDGE_CURVE":
            continue
        r = refs(a)
        if len(r) < 3 or ents[r[2]][0] != "LINE":
            continue
        v1 = pts[refs(ents[r[0]][1])[0]]
        v2 = pts[refs(ents[r[1]][1])[0]]
        if abs(v1[2] - z) < 1e-6 and abs(v2[2] - z) < 1e-6 and math.dist(v1[:2], v2[:2]) > min_len:
            segs.add(tuple(sorted([(round(v1[0], 3), round(v1[1], 3)), (round(v2[0], 3), round(v2[1], 3))])))
    return sorted(segs)


def on_pitch(v, origin):
    d = (v - origin) % PITCH
    return min(d, PITCH - d) < 0.05


def board(path):
    ents = load(path)
    pts = {k: nums(v[1].split(",", 1)[1]) for k, v in ents.items() if v[0] == "CARTESIAN_POINT"}
    outline = lines_at(ents, pts, 0.0)
    xs = [p[0] for s in outline for p in s]
    ys = [p[1] for s in outline for p in s]
    width, length = max(xs), max(ys)
    mirror = "INT" in path.upper()
    fx = (lambda x: width - x) if mirror else (lambda x: x)

    circ = circles(ents, pts)
    holes = sorted(set((c[1], c[2]) for c in circ if c[0] == 0.5))
    ox = collections.Counter(round(x % PITCH, 2) for x, y in holes).most_common(1)[0][0]
    oy = collections.Counter(round(y % PITCH, 2) for x, y in holes).most_common(1)[0][0]
    on = [(x, y) for x, y in holes if on_pitch(x, ox) and on_pitch(y, oy)]
    off = [h for h in holes if h not in set(on)]
    X = sorted(set(x for x, y in on))
    Y = sorted(set(y for x, y in on))
    if mirror:
        X = X[::-1]
    col = {x: i + 1 for i, x in enumerate(X)}
    row = {y: j + 1 for j, y in enumerate(Y)}
    have = set((col[x], row[y]) for x, y in on)

    name = path.split("/")[-1]
    print(f"===== {name}")
    print(f"outline {width} x {length} mm; doc frame x' = {'width - x' if mirror else 'x'}, y' = y")
    print(f"grid {len(X)} cols x {len(Y)} rows, pitch {PITCH}, hole 1.0, pad 1.6")
    print(f"  col 1 at x' = {fx(X[0]):.2f}, col {len(X)} at x' = {fx(X[-1]):.2f}")
    print(f"  row 1 at y  = {Y[0]:.2f}, row {len(Y)} at y  = {Y[-1]:.2f}")
    missing = collections.defaultdict(list)
    for c in range(1, len(X) + 1):
        for r in range(1, len(Y) + 1):
            if (c, r) not in have:
                missing[c].append(r)
    print("  missing grid holes by doc column:", dict(missing))
    print("  map (doc col 1 left, row 1 top; # hole, . none)")
    for r in range(1, len(Y) + 1):
        print(f"  {r:3} " + "".join("#" if (c, r) in have else "." for c in range(1, len(X) + 1)))
    if off:
        ox_ = sorted(set(round(fx(x), 2) for x, y in off))
        oy_ = sorted(set(y for x, y in off))
        print(f"off-grid 1.0 mm holes ({len(off)}): x' {ox_}, y {oy_[0]:.2f}..{oy_[-1]:.2f} in {len(oy_)} rows of {PITCH}")
    for radius in sorted(set(c[0] for c in circ)):
        if radius in (0.5, 0.8):
            continue
        xy = sorted(set((fx(c[1]), c[2]) for c in circ if c[0] == radius and abs(c[3]) < 0.1 or c[0] == radius and abs(c[3] + 0.07) < 0.01))
        if 2 < len(xy) < 40:
            kind = "holes" if radius >= 0.5 else "trace-end arcs (not holes)"
            print(f"{kind} of diameter {2 * radius}: " + ", ".join(f"({x:.2f},{y:.2f})" for x, y in xy))
    print("restricted areas (0.02 mm solid on the solder face), edges in the doc frame:")
    for (a, b), (c, d) in lines_at(ents, pts, 0.02):
        print(f"  ({fx(a):.2f},{b:.2f})-({fx(c):.2f},{d:.2f})")
    bulges = sorted(set((fx(c[1]), c[2], 2 * c[0]) for c in circ if abs(c[3] - 0.02) < 1e-6 and c[0] > 1.0))
    if bulges:
        print("  bulges (x', y, diameter):", bulges)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        board(p)
