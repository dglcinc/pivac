#!/usr/bin/env python3
"""Generate docs/air-handler-shield-assembly.svg, the placement drawing for the bench sheet
docs/air-handler-shield-assembly.md.

Run from the repo root: python3 docs/air-handler-shield-assembly.gen.py

Reads every footprint's position, rotation, pads and body outline from
hardware/ah-board/ah-board.kicad_pcb, so the drawing is the board as fabricated, seen from the component side
with the DIGITAL header along the top edge. Each part is filled with the colour of the assembly step that fits it;
a dot marks pad 1 on every part with an orientation (cathode on a diode or LED, + on C1, pin 1 on a chip).
"""
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "hardware/ah-board/ah-board.kicad_pcb"
OUT = ROOT / "docs/air-handler-shield-assembly.svg"

S = 11.0                       # px per mm
BW, BH = 86.36, 53.34
BX, BY = 40, 70
W, H = int(BX + BW * S + 380), int(BY + BH * S + 120)
FONT = "IBM Plex Mono, ui-monospace, monospace"

# assembly step: (label, fill colour, refs)
STEPS = [
    ("1  U2, only with DS2482 firmware", "#e0c3f0", ["U2"]),
    ("2  0805 / 1206 R and C", "#cfe3f7", ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11",
                                          "R12", "R13", "R14", "R15", "R16", "C2", "C3", "C4", "C5", "C6",
                                          "C7", "C8"]),
    ("3  LEDs and diodes", "#fbd5c4", ["LED1", "LED2", "LED3", "D1", "D2", "D3", "D4"]),
    ("4  optocouplers, fuses", "#d6efc9", ["U3", "U4", "F1", "F2"]),
    ("5  C1 electrolytic", "#f7e7a6", ["C1"]),
    ("6  PTSM headers", "#c9ecea", ["TB2", "TB3"]),
    ("7  TB1, U1 (through-hole)", "#f2c6cf", ["TB1", "U1"]),
    ("8  Arduino headers", "#dddddd", ["J10", "J11", "J12", "J13"]),
]
STEP_OF = {r: i for i, (_, _, refs) in enumerate(STEPS) for r in refs}
NOT_FITTED = {"TB4", "R17", "R18", "C9"}
BRIDGE = {"JP1"}
BARE = {"J1", "TP1", "TP2", "TP3"}
POLAR = {"U1", "U2", "U3", "U4", "D1", "D3", "D4", "LED1", "LED2", "LED3", "C1"}


def X(x):
    return BX + x * S


def Y(y):
    return BY + y * S


def rot(px, py, deg):
    # KiCad: y down, angles counter-clockwise as drawn
    t = math.radians(deg)
    return px * math.cos(t) + py * math.sin(t), -px * math.sin(t) + py * math.cos(t)


def parse():
    s = PCB.read_text()
    starts = [m.start() for m in re.finditer(r"\n\t\(footprint ", s)] + [len(s)]
    parts = []
    for a, b in zip(starts, starts[1:]):
        t = s[a:b]
        ref = re.search(r'\(property "Reference" "([^"]+)"', t).group(1)
        val = re.search(r'\(property "Value" "([^"]+)"', t).group(1)
        fx, fy, *fr = map(float, re.search(r"\n\t\t\(at ([-\d. ]+)\)", t).group(1).split())
        fr = fr[0] if fr else 0.0
        pads = []
        for m in re.finditer(r'\(pad "([^"]*)" (\w+) (\w+)\s*\(at ([-\d. ]+)\)\s*\(size ([-\d. ]+)\)', t):
            num, kind, shape = m.group(1), m.group(2), m.group(3)
            px, py, *pr = map(float, m.group(4).split())
            sw, sh = map(float, m.group(5).split())
            dx, dy = rot(px, py, fr)
            pads.append((num, kind, shape, fx + dx, fy + dy, sw, sh, pr[0] if pr else fr))
        items = re.split(r"\n\t\t(?=\()", t)
        body = []
        for layer in ("F.Fab", "F.CrtYd"):
            for it in items:
                if f'(layer "{layer}")' not in it or not it.startswith(("(fp_line", "(fp_rect", "(fp_poly")):
                    continue
                xy = [tuple(map(float, m.groups())) for m in
                      re.finditer(r"\((?:start|end|xy) ([-\d.]+) ([-\d.]+)\)", it)]
                body += [(xy[i], xy[i + 1]) for i in range(len(xy) - 1)]
            if body:
                break
        pts = [(fx + rot(*p, fr)[0], fy + rot(*p, fr)[1]) for seg in body for p in seg]
        if pts:
            bb = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
        else:
            bb = (min(p[3] - p[5] / 2 for p in pads) - 0.4, min(p[4] - p[6] / 2 for p in pads) - 0.4,
                  max(p[3] + p[5] / 2 for p in pads) + 0.4, max(p[4] + p[6] / 2 for p in pads) + 0.4)
        # keep outlines on the board for the drawing
        bb = (max(bb[0], 0), max(bb[1], 0), min(bb[2], BW), min(bb[3], BH))
        parts.append(dict(ref=ref, val=val, x=fx, y=fy, r=fr, pads=pads, bb=bb))
    return parts


def main():
    parts = parse()
    u1p8 = [p for p in next(q for q in parts if q["ref"] == "U1")["pads"] if p[0] == "8"][0]
    assert abs(u1p8[3] - 5.02) < 0.05, f"pad transform wrong: U1 pin 8 at x {u1p8[3]}"

    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'font-family="{FONT}">')
    a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    a(f'<text x="{BX}" y="32" font-size="20" font-weight="bold" fill="#1a1a1a">Air-handler shield rev A: '
      f'where each part goes</text>')
    a(f'<text x="{BX}" y="54" font-size="13" fill="#555">Component side, DIGITAL header at the top. '
      f'Colour = assembly step. Dot = pad 1 (cathode, C1 +, chip pin 1).</text>')
    # board and R4 outline
    a(f'<rect x="{X(0)}" y="{Y(0)}" width="{BW * S}" height="{BH * S}" fill="#2f6b3a" fill-opacity="0.10" '
      f'stroke="#1a1a1a" stroke-width="2"/>')
    a(f'<line x1="{X(68.58)}" y1="{Y(0)}" x2="{X(68.58)}" y2="{Y(BH)}" stroke="#777" stroke-dasharray="6 5"/>')
    a(f'<text x="{X(68.58) - 6}" y="{Y(BH) + 16}" font-size="11" fill="#666" text-anchor="end">R4 edge</text>')
    a(f'<text x="{X(77.5)}" y="{Y(BH) + 16}" font-size="11" fill="#666" text-anchor="middle">tab</text>')
    # USB-C and barrel jack under the board, from Arduino's R4 WiFi drawing (left edge)
    for y0, y1, x1, lab in ((11.0, 20.0, 7.0, "R4 USB-C below"), (41.0, 50.0, 13.0, "R4 barrel jack below")):
        a(f'<rect x="{X(0.3)}" y="{Y(y0)}" width="{(x1 - 0.3) * S}" height="{(y1 - y0) * S}" fill="none" '
          f'stroke="#888" stroke-dasharray="3 3"/>')
        a(f'<text x="{X(0.6)}" y="{Y(y1) + 13}" font-size="10" fill="#777">{lab}</text>')
    order = sorted(parts, key=lambda p: (p["ref"] in NOT_FITTED, -((p["bb"][2] - p["bb"][0]) *
                                                                    (p["bb"][3] - p["bb"][1]))))
    for p in order:
        ref = p["ref"]
        x0, y0, x1, y1 = p["bb"]
        if ref in STEP_OF:
            fill, stroke, dash = STEPS[STEP_OF[ref]][1], "#1a1a1a", ""
        elif ref in NOT_FITTED:
            fill, stroke, dash = "none", "#999", ' stroke-dasharray="4 3"'
        elif ref in BRIDGE:
            fill, stroke, dash = "#ffe08a", "#b8860b", ""
        else:
            fill, stroke, dash = "none", "#666", ' stroke-dasharray="2 2"'
        a(f'<rect x="{X(x0):.1f}" y="{Y(y0):.1f}" width="{(x1 - x0) * S:.1f}" height="{(y1 - y0) * S:.1f}" '
          f'rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1"{dash}/>')
        for num, kind, shape, px, py, sw, sh, pr in p["pads"]:
            if kind == "np_thru_hole":
                continue
            if shape == "circle" or (kind == "thru_hole" and shape == "oval" and abs(sw - sh) < 0.01):
                a(f'<circle cx="{X(px):.1f}" cy="{Y(py):.1f}" r="{sw / 2 * S:.1f}" fill="#c9a227" '
                  f'fill-opacity="0.85"/>')
            else:
                a(f'<rect x="{X(px) - sw / 2 * S:.1f}" y="{Y(py) - sh / 2 * S:.1f}" width="{sw * S:.1f}" '
                  f'height="{sh * S:.1f}" fill="#c9a227" fill-opacity="0.85" '
                  f'transform="rotate({-pr:.0f} {X(px):.1f} {Y(py):.1f})"/>')
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        small = (x1 - x0) * (y1 - y0) < 20
        fs = 10 if small else 13
        label = ref
        if ref in ("J10", "J11", "J12", "J13"):
            cy = y1 + 1.3 if y0 < 10 else y0 - 0.8
        if ref == "J1":
            label, cy = "J1 test row (bare pads)", y0 - 0.9
        anchor = "middle"
        if ref.startswith("LED"):
            cx, anchor = x1 + 0.4, "start"
        a(f'<text x="{X(cx):.1f}" y="{Y(cy) + fs * 0.35:.1f}" font-size="{fs}" font-weight="bold" '
          f'fill="#111" text-anchor="{anchor}" paint-order="stroke" stroke="#fff" stroke-width="2.5">{label}</text>')
    for p in parts:
        if p["ref"] in POLAR:
            pad1 = next(q for q in p["pads"] if q[0] == "1")
            a(f'<circle cx="{X(pad1[3]):.1f}" cy="{Y(pad1[4]):.1f}" r="3.6" fill="#c0392b" stroke="#fff" '
              f'stroke-width="1"/>')
    # legend
    lx, ly = X(BW) + 40, BY + 10
    a(f'<text x="{lx}" y="{ly}" font-size="14" font-weight="bold" fill="#1a1a1a">Assembly steps</text>')
    for i, (lab, col, refs) in enumerate(STEPS):
        yy = ly + 24 + i * 26
        a(f'<rect x="{lx}" y="{yy - 13}" width="22" height="16" rx="2" fill="{col}" stroke="#1a1a1a"/>')
        a(f'<text x="{lx + 30}" y="{yy}" font-size="13" fill="#1a1a1a">{lab}</text>')
    yy = ly + 24 + len(STEPS) * 26 + 6
    a(f'<rect x="{lx}" y="{yy - 13}" width="22" height="16" rx="2" fill="#ffe08a" stroke="#b8860b"/>')
    a(f'<text x="{lx + 30}" y="{yy}" font-size="13" fill="#1a1a1a">JP1: solder bridge</text>')
    yy += 26
    a(f'<rect x="{lx}" y="{yy - 13}" width="22" height="16" rx="2" fill="none" stroke="#999" '
      f'stroke-dasharray="4 3"/>')
    a(f'<text x="{lx + 30}" y="{yy}" font-size="13" fill="#1a1a1a">not fitted</text>')
    yy += 26
    a(f'<circle cx="{lx + 11}" cy="{yy - 5}" r="4" fill="#c0392b" stroke="#fff"/>')
    a(f'<text x="{lx + 30}" y="{yy}" font-size="13" fill="#1a1a1a">pad 1</text>')
    yy += 34
    for line in (                 "For the present AirHandler sketch:",
                 "U2 empty, R15 fitted, JP1 bridged.",
                 "With DS2482 firmware: U2 fitted,",
                 "R15 empty, JP1 open.",
                 "",
                 "TB1, top to bottom: R, C, Y2, W2.",
                 "TB2: SUP, G, RET, G.",
                 "TB3: V, D, G.",
                 "",
                 "Dashed box at left: the R4's USB-C",
                 "under U1. Clip U1's pins to 1.5 mm."):
        a(f'<text x="{lx}" y="{yy}" font-size="12" fill="#333">{line}</text>')
        yy += 18
    a(f'<text x="{BX}" y="{H - 24}" font-size="11" fill="#777">Generated by docs/air-handler-shield-assembly.gen.py '
      f'from hardware/ah-board/ah-board.kicad_pcb.</text>')
    a("</svg>")
    OUT.write_text("\n".join(o) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
