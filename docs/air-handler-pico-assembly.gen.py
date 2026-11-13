#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""Generate docs/air-handler-pico-assembly.svg, the placement drawing for the bench sheet
docs/air-handler-pico-assembly.md.

Run from the repo root: python3 docs/air-handler-pico-assembly.gen.py
With the argument revc it draws Rev C from hardware/ahpc-board/ahpc-board.kicad_pcb into
docs/air-handler-pico-revc-assembly.svg, for docs/air-handler-pico-revc-assembly.md.

Reads every footprint's position, rotation, pads and body outline from hardware/ahp-board/ahp-board.kicad_pcb, so the
drawing is the Rev B board as fabricated. The front is drawn from above with the USB-A edge at the top; the back is
drawn as seen when the board is turned over left to right, so the USB-A edge stays at the top and the left and right
edges swap. Each part is filled with the colour of its assembly step; a red dot marks pad 1 on every part with an
orientation (cathode on a diode or LED, + on C1, pin 1 on a chip or connector).
"""
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVC = sys.argv[1:] == ["revc"]
REV = "Rev C" if REVC else "Rev B"
PCB = ROOT / ("hardware/ahpc-board/ahpc-board.kicad_pcb" if REVC else "hardware/ahp-board/ahp-board.kicad_pcb")
OUT = ROOT / ("docs/air-handler-pico-revc-assembly.svg" if REVC else "docs/air-handler-pico-assembly.svg")

S = 10.0                          # px per mm
BX0, BX1 = 0.3, 56.7              # board outline, mm
BY0, BY1 = 0.0, 56.0
TOP = 140                         # px above the board, room for J4 past the edge and the titles
GAP = 90                          # px between the two views
FX = 40                           # left edge of the front view, px
BKX = FX + (BX1 - BX0) * S + GAP  # left edge of the back view, px
LEG = BKX + (BX1 - BX0) * S + 50  # legend
W, H = int(LEG + 330), int(TOP + (BY1 - BY0) * S + 150)
FONT = "IBM Plex Mono, ui-monospace, monospace"

# assembly step: (label, fill colour, refs)
STEPS = [
    ("1  U3, U2 (chips)", "#e0c3f0", ["U3", "U2"]),
    ("2  R1-R4, C2-C6", "#cfe3f7", ["R1", "R2", "R3", "R4", "C2", "C3", "C4", "C5", "C6"]),
    ("3  D1, D2, F1", "#fbd5c4", ["D1", "D2", "F1"]),
    ("4  C1 electrolytic", "#f7e7a6", ["C1"]),
    ("5  U4 Pico W", "#d6efc9", ["U4"]),
    ("6  back: R5-R10, LED1-LED6", "#f2c6cf", ["R5", "R6", "R7", "R8", "R9", "R10",
                                              "LED1", "LED2", "LED3", "LED4", "LED5", "LED6"]),
    ("7  J2, J3 (PTSM)", "#c9ecea", ["J2", "J3"]),
    ("8  U1, J1, J4 (through-hole)", "#e8d3b5", ["U1", "J1", "J4"]),
]
if REVC:
    STEPS[5:6] = [("6  back: U5, Q1", "#f5b7a3", ["U5", "Q1"]),
                  ("7  back: R5-R13, C7, LED1-LED6", "#f2c6cf", ["R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12",
                                                               "R13", "C7", "LED1", "LED2", "LED3", "LED4", "LED5",
                                                               "LED6"])]
    STEPS[7:] = [(f"{i + 8}{lab[1:]}", c, r) for i, (lab, c, r) in enumerate(STEPS[7:])]
STEP_OF = {r: i for i, (_, _, refs) in enumerate(STEPS) for r in refs}
BARE = {"TP1", "TP2", "TP3", "H1", "H2", "H3"}
POLAR = {"U1", "U2", "U3", "U4", "U5", "Q1", "D1", "C1", "J4", "LED1", "LED2", "LED3", "LED4", "LED5", "LED6"}
LABEL = {"TP1": "TP1 VS", "TP2": "TP2 COM", "TP3": "TP3 GND"}


def rot(px, py, deg):
    t = math.radians(deg)
    return px * math.cos(t) + py * math.sin(t), -px * math.sin(t) + py * math.cos(t)


def parse():
    s = PCB.read_text()
    starts = [m.start() for m in re.finditer(r"\n\t\(footprint ", s)] + [len(s)]
    parts = []
    for a, b in zip(starts, starts[1:]):
        t = s[a:b]
        ref = re.search(r'\(property "Reference" "([^"]+)"', t).group(1)
        side = "B" if re.search(r'^\s*\(layer "B\.Cu"\)', t, re.M) else "F"
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
        for layer in (f"{side}.Fab", f"{side}.CrtYd"):
            for it in items:
                if f'(layer "{layer}")' not in it or not it.startswith(("(fp_line", "(fp_rect", "(fp_poly")):
                    continue
                xy = [tuple(map(float, m.groups())) for m in
                      re.finditer(r"\((?:start|end|xy) ([-\d.]+) ([-\d.]+)\)", it)]
                body += [(xy[i], xy[i + 1]) for i in range(len(xy) - 1)]
            if body:
                break
        pts = [(fx + rot(*p, fr)[0], fy + rot(*p, fr)[1]) for seg in body for p in seg]
        if not pts:
            pts = [(p[3] + dx * p[5] / 2, p[4] + dy * p[6] / 2) for p in pads for dx in (-1, 1) for dy in (-1, 1)]
        bb = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
        bb = (max(bb[0], BX0), max(bb[1], -8), min(bb[2], BX1), min(bb[3], BY1))
        parts.append(dict(ref=ref, side=side, x=fx, y=fy, pads=pads, bb=bb))
    return parts


def view(a, parts, side, ox, title, sub):
    """Draw one face. ox: left edge in px. The back is mirrored left to right."""
    def X(x):
        return ox + ((BX1 - x) if side == "B" else (x - BX0)) * S

    def Y(y):
        return TOP + (y - BY0) * S

    a(f'<text x="{ox}" y="{TOP - 62}" font-size="16" font-weight="bold" fill="#1a1a1a">{title}</text>')
    a(f'<text x="{ox}" y="{TOP - 44}" font-size="11" fill="#555">{sub}</text>')
    a(f'<rect x="{ox}" y="{Y(BY0)}" width="{(BX1 - BX0) * S}" height="{(BY1 - BY0) * S}" fill="#2f6b3a" '
      f'fill-opacity="0.10" stroke="#1a1a1a" stroke-width="2"/>')
    a(f'<text x="{ox + (BX1 - BX0) * S / 2}" y="{Y(BY1) + 18}" font-size="11" fill="#666" text-anchor="middle">'
      f'sensor end: J2 1-wire, J3 NTC</text>')
    mine = [p for p in parts if p["side"] == side or p["ref"] in BARE]
    other = [p for p in parts if p["side"] != side and p["ref"] not in BARE]
    for p in other:                                     # the other face's parts, faint, for orientation
        x0, y0, x1, y1 = p["bb"]
        xa, xb = sorted((X(x0), X(x1)))
        a(f'<rect x="{xa:.1f}" y="{Y(y0):.1f}" width="{xb - xa:.1f}" height="{(y1 - y0) * S:.1f}" rx="2" '
          f'fill="none" stroke="#bbb" stroke-width="0.8" stroke-dasharray="2 2"/>')
        for num, kind, shape, px, py, sw, sh, pr in p["pads"]:
            if kind == "thru_hole":
                a(f'<circle cx="{X(px):.1f}" cy="{Y(py):.1f}" r="{min(sw, sh) / 2 * S:.1f}" fill="#d8c27a" '
                  f'fill-opacity="0.6"/>')
        if p["ref"] in ("U4", "J4", "U1", "J1"):
            cx = (X(x0) + X(x1)) / 2
            a(f'<text x="{cx:.1f}" y="{Y((y0 + y1) / 2):.1f}" font-size="11" fill="#999" '
              f'text-anchor="middle">{p["ref"]} (front)</text>')
    order = sorted(mine, key=lambda p: -((p["bb"][2] - p["bb"][0]) * (p["bb"][3] - p["bb"][1])))
    for p in order:
        ref = p["ref"]
        x0, y0, x1, y1 = p["bb"]
        xa, xb = sorted((X(x0), X(x1)))
        if ref in STEP_OF:
            a(f'<rect x="{xa:.1f}" y="{Y(y0):.1f}" width="{xb - xa:.1f}" height="{(y1 - y0) * S:.1f}" rx="2" '
              f'fill="{STEPS[STEP_OF[ref]][1]}" stroke="#1a1a1a" stroke-width="1"/>')
        for num, kind, shape, px, py, sw, sh, pr in p["pads"]:
            if kind == "np_thru_hole":
                a(f'<circle cx="{X(px):.1f}" cy="{Y(py):.1f}" r="{sw / 2 * S:.1f}" fill="#ffffff" stroke="#333" '
                  f'stroke-width="1"/>')
            elif kind == "thru_hole" or shape == "circle":
                a(f'<circle cx="{X(px):.1f}" cy="{Y(py):.1f}" r="{min(sw, sh) / 2 * S:.1f}" fill="#c9a227" '
                  f'fill-opacity="0.9" stroke="#7a5c00" stroke-width="0.6"/>')
            else:
                ang = pr if side == "F" else -pr
                a(f'<rect x="{X(px) - sw / 2 * S:.1f}" y="{Y(py) - sh / 2 * S:.1f}" width="{sw * S:.1f}" '
                  f'height="{sh * S:.1f}" fill="#c9a227" fill-opacity="0.85" '
                  f'transform="rotate({-ang:.0f} {X(px):.1f} {Y(py):.1f})"/>')
        cx, cy = (xa + xb) / 2, Y((y0 + y1) / 2)
        fs = 10 if (x1 - x0) * (y1 - y0) < 20 else 13
        anchor = "middle"
        lab = LABEL.get(ref, ref)
        if ref.startswith("LED"):
            cx, anchor = xb + 4, "start"    # Rev C: past the board edge, clear of the resistors inboard
        if ref.startswith("H"):
            lab, fs, cy = "", 0, cy
        if ref == "U4":
            cy = Y(y0 + 30)
        if ref == "J4":
            cy = Y(y0 + 3)
        if lab:
            a(f'<text x="{cx:.1f}" y="{cy + fs * 0.35:.1f}" font-size="{fs}" font-weight="bold" fill="#111" '
              f'text-anchor="{anchor}" paint-order="stroke" stroke="#fff" stroke-width="2.5">{lab}</text>')
    for p in mine:
        if p["ref"] in POLAR:
            pad1 = next(q for q in p["pads"] if q[0] == "1")
            a(f'<circle cx="{X(pad1[3]):.1f}" cy="{Y(pad1[4]):.1f}" r="3.6" fill="#c0392b" stroke="#fff" '
              f'stroke-width="1"/>')
    # call out U4's own holes on the face where they are worked
    u4 = next(p for p in parts if p["ref"] == "U4")
    usb = [q for q in u4["pads"] if q[0] in ("TP2", "TP3")]
    swd = [q for q in u4["pads"] if q[0] in ("D1", "D2", "D3")]
    ux = sum(X(q[3]) for q in usb) / 2
    uy = Y(usb[0][4])
    for q in usb:
        a(f'<circle cx="{X(q[3]):.1f}" cy="{Y(q[4]):.1f}" r="7" fill="none" stroke="#c0392b" stroke-width="1.6"/>')
    if side == "B":
        a(f'<text x="{ux:.1f}" y="{uy + 26:.1f}" font-size="11" font-weight="bold" fill="#c0392b" '
          f'text-anchor="middle" paint-order="stroke" stroke="#fff" stroke-width="3">USB D-/D+: fill from here</text>')
    sx = sum(X(q[3]) for q in swd) / 3
    sy = Y(swd[0][4])
    a(f'<text x="{sx:.1f}" y="{sy + 20:.1f}" font-size="10" fill="#555" text-anchor="middle" paint-order="stroke" '
      f'stroke="#fff" stroke-width="3">SWD holes, leave empty</text>')


def main():
    parts = parse()
    led1 = next(p for p in parts if p["ref"] == "LED1")
    assert led1["side"] == "B", "LED1 should be on the back"
    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 {W} {H}" '
      f'font-family="{FONT}">')
    led_lines = (("LEDs from the top: green PWR,", "yellow FAN, blue Y1, blue Y2,", "red W1, red W2. Lens to the",
                  "floor, cathode to the board", "edge.") if REVC else
                 ("LEDs from the top: green PWR,", "yellow FAN, blue Y1, blue Y2,", "red W1, red W2. Lens to the",
                  "board edge."))
    a(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
    a(f'<text x="{FX}" y="30" font-size="20" font-weight="bold" fill="#1a1a1a">AirMaster carrier {REV}: '
      f'where each part goes</text>')
    view(a, parts, "F", FX, "Front", "From above, USB-A edge at the top.")
    view(a, parts, "B", BKX, "Back", "Turned over left to right: USB-A edge still at the top.")
    lx, ly = LEG, TOP
    a(f'<text x="{lx}" y="{ly}" font-size="14" font-weight="bold" fill="#1a1a1a">Assembly steps</text>')
    for i, (lab, col, refs) in enumerate(STEPS):
        yy = ly + 24 + i * 26
        a(f'<rect x="{lx}" y="{yy - 13}" width="22" height="16" rx="2" fill="{col}" stroke="#1a1a1a"/>')
        a(f'<text x="{lx + 30}" y="{yy}" font-size="13" fill="#1a1a1a">{lab}</text>')
    yy = ly + 24 + len(STEPS) * 26 + 6
    a(f'<circle cx="{lx + 11}" cy="{yy - 5}" r="4" fill="#c0392b" stroke="#fff"/>')
    a(f'<text x="{lx + 30}" y="{yy}" font-size="13" fill="#1a1a1a">pad 1</text>')
    yy += 24
    a(f'<rect x="{lx}" y="{yy - 13}" width="22" height="16" rx="2" fill="none" stroke="#bbb" '
      f'stroke-dasharray="2 2"/>')
    a(f'<text x="{lx + 30}" y="{yy}" font-size="13" fill="#1a1a1a">part on the other face</text>')
    yy += 34
    for line in ("Pad 1 = cathode on D1 and the",
                 "LEDs, + on C1, pin 1 on chips",
                 "and connectors. D2 has no",
                 "polarity.",
                 "",
                 *led_lines,
                 "",
                 "TP1-TP3 and the three screw",
                 "holes take no part.",
                 "",
                 "J1: R, C.  J2: V, D, G.",
                 "J3: SUP, G, RET, G."):
        a(f'<text x="{lx}" y="{yy}" font-size="12" fill="#333">{line}</text>')
        yy += 18
    a(f'<text x="{FX}" y="{H - 20}" font-size="11" fill="#777">Generated by docs/air-handler-pico-assembly.gen.py '
      f'{"revc " if REVC else ""}from {PCB.relative_to(ROOT)}.</text>')
    a("</svg>")
    OUT.write_text("\n".join(o) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
