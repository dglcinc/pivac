#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""Write JLCPCB's two assembly files for an AirMaster carrier from the board file itself:

    python3 hardware/ahp-jlc.py [c|d]

    hardware/ahp<rev>-board/ahp<rev>-board-jlc-bom.csv   Comment, Designator, Footprint, LCSC Part #
    hardware/ahp<rev>-board/ahp<rev>-board-jlc-cpl.csv   Designator, Mid X, Mid Y, Layer, Rotation

It reads the .kicad_pcb as text, so it needs no KiCad. PARTS maps each reference to the part JLCPCB places, by its
LCSC number, checked against JLCPCB's assembly library on 2026-11-16. A reference in HAND is left for the bench and
appears in neither file. Rev C leaves five parts for the bench; Rev D leaves none, and its three through-hole parts
(U1, J1, J4) are in both files for JLCPCB's through-hole soldering. Positions are KiCad's own placement
convention (millimetres, Y up, rotation as stored), so check every polarised part in JLCPCB's placement preview
before paying: its library does not share KiCad's zero.
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REV = sys.argv[1].lower() if len(sys.argv) > 1 else "c"
NAME = {"c": "ahpc-board", "d": "ahpd-board"}[REV]
BOARD = os.path.join(HERE, NAME, NAME + ".kicad_pcb")

# reference -> (comment for the BOM, LCSC number, library, unit price in USD at one board)
BASIC, EXT = "basic", "extended"
PARTS = {}
def part(refs, comment, lcsc, lib, usd):
    for r in refs.split():
        PARTS[r] = (comment, lcsc, lib, usd)
part("U3", "ADS1115IDGSR", "C37593", EXT, 1.283)
part("U2", "DS2482S-100+T&R", "C143306", EXT, 2.815)
part("U5", "FSUSB42MUX", "C11355", EXT, 0.299)
part("Q1", "DMG2305UX-7", "C150470", EXT, 0.504)
part("R1 R2", "4.7k 1% 0805", "C17673", BASIC, 0.003)
part("R3 R4", "RT0805BRD0710KL 10k 0.1% 0805", "C110775", EXT, 0.044)
part("R5 R6 R7 R8 R9 R10", "220R 1% 0805", "C17557", BASIC, 0.003)
part("R11", "100k 1% 0805", "C149504", BASIC, 0.006)
part("R12", "22k 1% 0805", "C17560", BASIC, 0.005)
part("R13", "33k 1% 0805", "C17633", BASIC, 0.003)
part("C1", "UUD1H470MCL1GS 47uF 50V", "C445256", EXT, 0.281)
part("C2", "GCJ31CR71A106KA13L 10uF 10V 1206", "C437428", EXT, 0.410)
part("C3 C4 C5 C6 C7", "CC0805KRX7R9BB104 100nF 50V 0805", "C49678", BASIC, 0.014)
part("F1", "1812L020/60DR", "C315900", EXT, 0.386)
part("D1", "S1M-E3/61T", "C144860", EXT, 0.036)
part("D2", "SMAJ43CA", "C223990", EXT, 0.137)
part("LED1", "KT-0805G green", "C2297", BASIC, 0.016)
part("LED2", "KT-0805Y yellow", "C2296", BASIC, 0.015)
part("LED3 LED4", "KT-0805B blue", "C2293", EXT, 0.013)
part("LED5 LED6", "NCD0805R1 red", "C84256", BASIC, 0.013)
part("J2", "1778777 PTSM 0,5/3-HH-2,5-SMD", "C3583902", EXT, 1.663)
if REV == "d":      # Rev D: every part from JLCPCB's stock, a basic part where one serves
    part("D1", "M7 1N4007 SMA", "C95872", BASIC, 0.010)
    part("C2", "CL31A107MQHNNNE 100uF 6.3V 1206", "C15008", BASIC, 0.094)
    part("J3 J5", "1778764 PTSM 0,5/2-HH-2,5-SMD", "C5149246", EXT, 1.491)
    part("U4", "Raspberry Pi Pico W", "C7203003", EXT, 12.842)
    part("U1", "URB4805S-3WR3", "C20198635", EXT, 3.589)
    part("J1", "1803277 MC 1,5/2-G-3,81", "C480537", EXT, 0.638)
    part("J4", "61400416021 USB-A", "C6264900", EXT, 1.173)

# Left for the bench, with the reason. J3 and U4 had no stock at JLCPCB on 2026-11-16; U4 also needs its two USB
# holes filled from the back by hand, and U1, J1 and J4 are through-hole.
HAND = {} if REV == "d" else {"U4": "Pico W SC0918: no JLCPCB stock, and its USB holes are filled by hand",
        "U1": "TEC 3-4811WI: through-hole, no JLCPCB stock",
        "J1": "3.81 mm header: through-hole",
        "J3": "1778780: no JLCPCB stock",
        "J4": "61400416021 USB-A: through-hole"}
NO_PART = ("H", "TP")


def sexpr(s):
    tok = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', s)
    st = [[]]
    for t in tok:
        if t == "(":
            st.append([])
        elif t == ")":
            x = st.pop()
            st[-1].append(x)
        else:
            st[-1].append(t[1:-1] if t.startswith('"') else t)
    return st[0][0]


def footprints():
    out = []
    for e in sexpr(open(BOARD).read()):
        if not (isinstance(e, list) and e and e[0] == "footprint"):
            continue
        d = {"fp": e[1].split(":")[-1], "rot": 0.0, "smd_pads": 0, "th_pads": 0}
        for c in e[2:]:
            if not isinstance(c, list):
                continue
            if c[0] == "layer":
                d["layer"] = c[1]
            elif c[0] == "at":
                d["x"], d["y"] = float(c[1]), float(c[2])
                d["rot"] = float(c[3]) if len(c) > 3 else 0.0
            elif c[0] in ("property", "fp_text") and c[1].lower() == "reference":
                d["ref"] = c[2]
            elif c[0] == "pad" and c[2] == "smd" and c[1]:
                d["smd_pads"] += 1
            elif c[0] == "pad" and c[2] == "thru_hole":
                d["th_pads"] += 1
        out.append(d)
    return out


def refkey(r):
    return (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r) or 0))


def main():
    fps = {d["ref"]: d for d in footprints()}
    unknown = [r for r in fps if r not in PARTS and r not in HAND and not r.startswith(NO_PART)]
    missing = [r for r in list(PARTS) + list(HAND) if r not in fps]
    if unknown or missing:
        raise SystemExit(f"board and table disagree: not in table {unknown}, not on board {missing}")
    groups = {}
    for r in sorted(PARTS, key=refkey):
        comment, lcsc, lib, usd = PARTS[r]
        groups.setdefault((comment, fps[r]["fp"], lcsc), []).append(r)
    out = os.path.join(HERE, NAME)
    with open(os.path.join(out, NAME + "-jlc-bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (comment, fp, lcsc), refs in groups.items():
            w.writerow([comment, ",".join(refs), fp, lcsc])
    with open(os.path.join(out, NAME + "-jlc-cpl.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in sorted(PARTS, key=refkey):
            d = fps[r]
            w.writerow([r, f"{d['x']:.3f}mm", f"{-d['y']:.3f}mm", "Top" if d["layer"] == "F.Cu" else "Bottom", f"{d['rot'] % 360:g}"])
    ext = sorted({v[1] for v in PARTS.values() if v[2] == EXT})
    joints = sum(fps[r]["smd_pads"] for r in PARTS)
    cost = sum(v[3] for v in PARTS.values())
    sides = {fps[r]["layer"] for r in PARTS}
    th = sum(fps[r]["th_pads"] for r in PARTS)
    print(f"Rev {REV.upper()}: {len(PARTS)} parts on {len(sides)} side(s), {len(groups)} BOM lines, {len(ext)} extended, "
          f"{joints} surface-mount joints, {th} through-hole joints, parts ${cost:.2f} a board")
    print("left for the bench:", ", ".join(sorted(HAND, key=refkey)) or "nothing")


if __name__ == "__main__":
    main()
