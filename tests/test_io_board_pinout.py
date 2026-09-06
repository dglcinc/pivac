#!/usr/bin/env python3
"""Cross-check the optocoupler pinout figure against the I/O board build procedure.

Dependency-free (no pytest): run directly with

    python tests/test_io_board_pinout.py

The figure in `docs/rpi-io-board-ic-pinout-{front,back}.svg` is a hand-entered
transcription of `docs/rpi-io-board-design.md`. A wrong pin there is a rebuilt board, so
every entry is re-derived from the document's own tables -- the section 2.1 channel master
map, the section 5.1 socket hole maps, and the section 5.3 rail stubs and feeders -- and
compared against the generator's data. It also asserts the DIP numbering is the LTV-847
standard, which is what makes the front/back mirroring meaningful.
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
GEN = os.path.join(ROOT, "docs", "rpi-io-board-ic-pinout.gen.py")
DOC = os.path.join(ROOT, "docs", "rpi-io-board-design.md")

# LTV-847 DIP-16: channels 1-4 are A/K on pins 1/2, 3/4, 5/6, 7/8 and E/C on 15/16, 13/14,
# 11/12, 9/10 (design doc section 7, confirmed by diode test).
LTV847 = {1: "A1", 2: "K1", 3: "A2", 4: "K2", 5: "A3", 6: "K3", 7: "A4", 8: "K4",
          9: "E4", 10: "C4", 11: "E3", 12: "C3", 13: "E2", 14: "C2", 15: "E1", 16: "C1"}

# section 5.1, columns 7..14 across each socket row
SOCKET_ROWS = {
    ("IC-A", 8):  ["K4", "A4", "K3", "A3", "K2", "A2", "K1", "A1"],
    ("IC-A", 11): ["E4", "C4", "E3", "C3", "E2", "C2", "E1", "C1"],
    ("IC-B", 13): ["K4", "A4", "K3", "A3", "K2", "A2", "K1", "A1"],
    ("IC-B", 16): ["E4", "C4", "E3", "C3", "E2", "C2", "E1", "C1"],
    ("IC-C", 18): ["C1", "E1", "C2", "E2", "C3", "E3", "C4", "E4"],
    ("IC-C", 21): ["A1", "K1", "A2", "K2", "A3", "K3", "A4", "K4"],
}
# section 5.3: ground-rail stubs must land on E pins, +14 V feeders on A pins
GND_STUBS = {"IC-A": [(7, 11), (9, 11), (11, 11), (13, 11)],
             "IC-B": [(7, 16), (9, 16), (11, 16), (13, 16)],
             "IC-C": [(8, 18), (10, 18), (12, 18), (14, 18)]}
FEEDERS = {"IC-A": (14, 8), "IC-B": (14, 13), "IC-C": (13, 21)}

ROW_RE = re.compile(
    r'^\|\s*(\d+)\s*\|\s*`?([^|`]+?)`?\s*\|\s*([ABC])·(\d)\s*\|\s*([\w.]+|—)\s*\|'
    r'[^|]*\|[^|]*\|\s*\((\d+),(\d+)\)\s*\|\s*\((\d+),(\d+)\)\s*\|'
    r'[^|]*\|\s*(\d+|—)\s*\|\s*(\d+|—)\s*\|', re.M)


def load_figure_data():
    """Import the generator's IC table without letting it write any SVG."""
    src = open(GEN).read().split("COL = {")[0]
    ns = {}
    exec(compile(src, GEN, "exec"), ns)
    return ns["IC"]


def main():
    IC = load_figure_data()
    doc = open(DOC).read()
    rows = ROW_RE.findall(doc)
    fails = []

    if len(rows) != 12:
        print(f"[FAIL] parsed {len(rows)} channel rows from section 2.1, expected 12")
        sys.exit(1)
    print(f"[PASS] section 2.1 parsed: {len(rows)} channels")

    for _, name, ic, ch, plug, kc, kr, cc, cr, pipin, bcm in rows:
        name = name.strip().replace("spare ", "")
        icn = "IC-" + ic
        by_leg = {(p[1][0], p[1][1]): p for p in IC[icn]["pins"]}
        k, c = by_leg[("K", ch)], by_leg[("C", ch)]
        if (k[2], k[3]) != (int(kc), int(kr)):
            fails.append(f"{icn} K·{ch} hole {(k[2], k[3])} != doc {(int(kc), int(kr))}")
        if (c[2], c[3]) != (int(cc), int(cr)):
            fails.append(f"{icn} C·{ch} hole {(c[2], c[3])} != doc {(int(cc), int(cr))}")
        if plug != "—" and plug not in k[6]:
            fails.append(f"{icn} K·{ch} label {k[6]!r} does not name plug {plug}")
        if pipin == "—":
            if k[4] != "non" or c[4] != "non":
                fails.append(f"{icn} ch{ch} has no plug position but is not marked unused")
        else:
            if f"Pi {pipin} " not in c[6] or f"BCM {bcm}" not in c[6]:
                fails.append(f"{icn} C·{ch} label {c[6]!r} != Pi {pipin} / BCM {bcm}")
            if name not in c[5]:
                fails.append(f"{icn} C·{ch} channel name {c[5]!r} != doc {name!r}")
    print(f"[{'PASS' if not fails else 'FAIL'}] section 2.1 holes, plugs, Pi pins and BCM numbers")

    before = len(fails)
    for (icn, row), legs in SOCKET_ROWS.items():
        by_hole = {(p[2], p[3]): p for p in IC[icn]["pins"]}
        for col, leg in zip(range(7, 15), legs):
            p = by_hole.get((col, row))
            if p is None:
                fails.append(f"{icn} has no pin at hole ({col},{row})")
            elif p[1] != leg:
                fails.append(f"{icn} ({col},{row}) is {p[1]}, section 5.1 says {leg}")
    print(f"[{'PASS' if len(fails) == before else 'FAIL'}] section 5.1 socket hole maps")

    before = len(fails)
    for icn, d in IC.items():
        for p in d["pins"]:
            if LTV847[p[0]] != p[1]:
                fails.append(f"{icn} pin {p[0]} is {p[1]}, LTV-847 pin {p[0]} is {LTV847[p[0]]}")
    print(f"[{'PASS' if len(fails) == before else 'FAIL'}] DIP numbering matches the LTV-847")

    before = len(fails)
    for icn, stubs in GND_STUBS.items():
        by_hole = {(p[2], p[3]): p for p in IC[icn]["pins"]}
        for h in stubs:
            if by_hole[h][1][0] != "E":
                fails.append(f"{icn} ground stub {h} lands on {by_hole[h][1]}, not an E pin")
    for icn, h in FEEDERS.items():
        by_hole = {(p[2], p[3]): p for p in IC[icn]["pins"]}
        if by_hole[h][1][0] != "A":
            fails.append(f"{icn} +14 V feeder {h} lands on {by_hole[h][1]}, not an A pin")
        if "feeder" not in by_hole[h][6]:
            fails.append(f"{icn} feeder pin {h} is not labelled as the feeder")
    print(f"[{'PASS' if len(fails) == before else 'FAIL'}] section 5.3 ground stubs and +14 V feeders")

    print()
    if fails:
        print(f"{len(fails)} MISMATCH(ES):")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print(f"all {sum(len(d['pins']) for d in IC.values())} pins agree with the build procedure")


if __name__ == "__main__":
    main()
