#!/usr/bin/env python3
"""Generate docs/mbr-air-handler-node-shield-layout.svg, the parts layout on the Olimex PROTO-SHIELD rev A.

Run from the repo root: python3 docs/mbr-air-handler-node-shield-layout.gen.py

Coordinates are millimetres in the frame of Olimex's mechanical drawing (manual page 9): origin at the
bottom-left corner of the board, x to the right, y up, the DIGITAL header along the top edge.
"""
from pathlib import Path

S = 11.0                 # px per mm
BX, BY = 240, 120         # SVG position of the board's top-left corner (x = 0, y = 53.34)
BW, BH = 68.58, 53.34
W, H = 1560, 860

out = []
add = out.append

C_5V = "#d62728"
C_GND = "#1a1a1a"
C_3V3 = "#e08a00"
C_DQ = "#b8960b"
C_AN = "#1f77b4"
C_D8 = "#2ca02c"
C_PAD = "#c9a227"
C_FAINT = "#b0b0b0"


def px(x, y):
    return BX + x * S, BY + (BH - y) * S


def text(x, y, s, size=12, anchor="start", weight="normal", fill="#000", rot=None):
    t = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
        f'font-weight="{weight}" fill="{fill}"{t}>{s}</text>')


def mtext(x, y, s, size=10, anchor="middle", **kw):
    X, Y = px(x, y)
    text(X, Y, s, size, anchor, **kw)


def pad(x, y, r=0.8, fill="#fff", stroke=C_PAD, sw=1.6):
    X, Y = px(x, y)
    add(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{r*S:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def hole(x, y, color):
    X, Y = px(x, y)
    add(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{0.38*S:.1f}" fill="{color}" stroke="none"/>')


def line(pts, color, width=2.0, dash=None, opacity=1.0):
    d = " ".join("%.1f,%.1f" % px(x, y) for x, y in pts)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
        f'stroke-linejoin="round" stroke-linecap="round" opacity="{opacity}"{extra}/>')


def resistor(x1, y1, x2, y2, label, color, body=6.3):
    """Axial resistor lying flat between two holes, body centred."""
    line([(x1, y1), (x2, y2)], "#666", 1.6)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    X, Y = px(mx, my)
    horiz = abs(y2 - y1) < 0.01
    w, h = (body * S, 2.4 * S) if horiz else (2.4 * S, body * S)
    add(f'<rect x="{X-w/2:.1f}" y="{Y-h/2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="5" '
        f'fill="#f3e3c3" stroke="{color}" stroke-width="2"/>')
    text(X, Y + 4, label, 10.5, "middle", "bold")


def label(X, Y, s, anchor="start", fill="#000"):
    w = 6.4 * len(s) + 6
    x0 = X - 3 if anchor == "start" else (X - w + 3 if anchor == "end" else X - w / 2)
    add(f'<rect x="{x0:.1f}" y="{Y-11:.1f}" width="{w:.1f}" height="15" rx="2" fill="#fff" fill-opacity="0.9"/>')
    text(X, Y, s, 10.5, anchor, "bold", fill)


def standing(x1, y1, x2, y2, label_, color):
    """Resistor standing on end (hairpin): body over the first hole, lead bent to the second."""
    X1, Y1 = px(x1, y1)
    X2, Y2 = px(x2, y2)
    add(f'<line x1="{X1:.1f}" y1="{Y1:.1f}" x2="{X2:.1f}" y2="{Y2:.1f}" stroke="#666" stroke-width="1.6"/>')
    add(f'<circle cx="{X1:.1f}" cy="{Y1:.1f}" r="{1.3*S:.1f}" fill="#f3e3c3" stroke="{color}" stroke-width="2"/>')
    label(X1, Y1 + 32, label_, "middle")


def capacitor(x1, y1, x2, y2, label_, side="right"):
    X1, Y1 = px(x1, y1)
    X2, Y2 = px(x2, y2)
    mx, my = (X1 + X2) / 2, (Y1 + Y2) / 2
    add(f'<line x1="{X1:.1f}" y1="{Y1:.1f}" x2="{X2:.1f}" y2="{Y2:.1f}" stroke="#666" stroke-width="1.6"/>')
    add(f'<ellipse cx="{mx:.1f}" cy="{my:.1f}" rx="{1.9*S:.1f}" ry="{1.2*S:.1f}" fill="#f5d36b" '
        f'stroke="{C_AN}" stroke-width="2"/>')
    dx = 26 if side == "right" else -26
    label(mx + dx, my + 4, label_, "start" if side == "right" else "end")


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="Helvetica, Arial, sans-serif" font-size="12">')
add('<title>Master bedroom air-handler node: PROTO-SHIELD layout</title>')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
text(20, 32, "Master bedroom air-handler node: parts on the Olimex PROTO-SHIELD rev A, component side", 18, weight="bold")
text(20, 54, "To scale, 11 px per mm. Solid parts and the red 5 V rail are on the component side; dashed wires run on the "
     "solder side, drawn as seen through the board.", 12, fill="#444")
text(20, 72, "Coordinates in mm from the board's bottom-left corner, as on Olimex's mechanical drawing. Proto columns "
     "c1–c13 run left to right, rows r1–r14 top to bottom.", 12, fill="#444")

# --- board outline -------------------------------------------------------------------------------
outline = [(0, 0), (66.04, 0), (68.58, 2.54), (68.58, 38.10), (66.04, 40.64), (66.04, 53.34), (0, 53.34), (0, 0)]
d = " ".join("%.1f,%.1f" % px(x, y) for x, y in outline)
add(f'<polygon points="{d}" fill="#fbeaea" stroke="#8b1e1e" stroke-width="2"/>')
for hx, hy in [(13.97, 2.54), (15.24, 50.80), (66.04, 7.62), (66.04, 35.56)]:
    X, Y = px(hx, hy)
    add(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{1.6*S:.1f}" fill="#fff" stroke="#8b1e1e" stroke-width="1.5"/>')

# --- CON-A / CON-B SMD areas (faint) and their through-hole columns ---------------------------------
for (x0, y0, x1, y1) in [(6.0, 26.0, 18.5, 43.5), (6.0, 6.0, 18.5, 24.5)]:
    X0, Y0 = px(x0, y1)
    X1, Y1 = px(x1, y0)
    add(f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{X1-X0:.1f}" height="{Y1-Y0:.1f}" fill="#f1dede" '
        f'stroke="{C_FAINT}" stroke-dasharray="3 3"/>')
mtext(12.2, 34.5, "CON-A SMD", 9, fill="#999")
mtext(12.2, 15.0, "CON-B SMD", 9, fill="#999")
for i in range(30):
    y = 43.18 - 1.27 * i
    pad(1.28 if i % 2 == 0 else 3.82, y, 0.7)
    pad(22.86 if i % 2 == 0 else 20.32, y, 0.7, stroke=C_FAINT)

# --- GND and 3V3 corner clusters --------------------------------------------------------------------
for x in (1.28, 3.82, 6.35, 8.89, 11.43):
    for y in (48.26, 50.80):
        pad(x, y, 0.8, fill="#444", stroke="#222")
    for y in (2.54, 5.08):
        pad(x, y, 0.8, fill="#f6c46a", stroke=C_3V3)
mtext(6.35, 45.6, "GND cluster", 9, fill="#222")
mtext(6.35, 0.6, "3V3 cluster", 9, fill=C_3V3)

# --- headers and their duplicate pads ---------------------------------------------------------------
dig_left = ["AREF", "GND", "D13", "D12", "D11", "D10", "D9", "D8"]
dig_right = ["D7", "D6", "D5", "D4", "D3", "D2", "D1", "D0"]
for i, name in enumerate(dig_left):
    hx = 23.88 + 2.54 * i
    gx = 22.86 + 2.54 * i
    pad(hx, 50.80, 0.8)
    for y in (48.26, 45.72):
        pad(gx, y, 0.75)
    mtext(hx, 52.3, name, 8, fill="#555")
for i, name in enumerate(dig_right):
    hx = 45.72 + 2.54 * i
    pad(hx, 50.80, 0.8)
    for y in (48.26, 45.72):
        pad(hx, y, 0.75)
    mtext(hx, 52.3, name, 8, fill="#555")
pwr = ["A6", "A7", "RST", "3V3", "5V", "GND", "GND", "VIN"]
ana = ["A0", "A1", "A2", "A3", "A4", "A5"]
for i, name in enumerate(pwr):
    hx = 27.94 + 2.54 * i
    for y in (2.54, 5.08, 7.62):
        pad(hx, y, 0.75)
    mtext(hx, 0.4, name, 8, fill="#555")
for i, name in enumerate(ana):
    hx = 50.80 + 2.54 * i
    for y in (2.54, 5.08, 7.62):
        pad(hx, y, 0.75)
    mtext(hx, 0.4, name, 8, fill="#555")

# --- proto area: big pads and the alternating 3V3 / GND buses ----------------------------------------
COLS = [25.40 + 2.54 * i for i in range(13)]          # c1..c13
ROWS = [43.18 - 2.54 * i for i in range(14)]          # r1..r14
for k in range(14):
    bx = 24.13 + 2.54 * k
    color = C_3V3 if k % 2 == 0 else C_GND
    line([(bx, 42.6), (bx, 10.9)], color, 2.2, opacity=0.35)
    for m in range(13):
        hole(bx, 11.43 + 2.54 * m, color)
for x in COLS:
    for y in ROWS:
        pad(x, y, 0.75)
for i, x in enumerate(COLS):
    mtext(x, 8.85, f"c{i+1}", 7, fill="#888")
for j, y in enumerate(ROWS):
    mtext(59.6, y - 0.35, f"r{j+1}", 7, "start", fill="#888")

# --- the shield's own parts (faint) -----------------------------------------------------------------
for (x0, y0, x1, y1, lab) in [(61.5, 40.0, 65.0, 44.5, "LED1/2"), (63.0, 25.5, 67.5, 31.0, "BUT1"),
                              (63.0, 13.0, 67.5, 18.5, "BUT2")]:
    X0, Y0 = px(x0, y1)
    X1, Y1 = px(x1, y0)
    add(f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{X1-X0:.1f}" height="{Y1-Y0:.1f}" fill="#eee" stroke="{C_FAINT}"/>')
    mtext((x0 + x1) / 2, (y0 + y1) / 2 - 0.4, lab, 8, fill="#999")

# --- terminal blocks on the left edge (pins in the outer column) ------------------------------------
TERM = [
    ("TB1", "5V", "1-Wire VDD", C_5V),
    ("TB1", "D2", "1-Wire DQ", C_DQ),
    ("TB1", "GND", "1-Wire GND", C_GND),
    ("TB2", "GND", "K1 NO 5", C_GND),
    ("TB2", "D8", "K1 COM 9", C_D8),
    ("TB3", "A0", "return NTC", C_AN),
    ("TB3", "GND", "return NTC", C_GND),
    ("TB3", "SH", "return drain", C_GND),
    ("TB4", "SH", "supply drain", C_GND),
    ("TB4", "GND", "supply NTC", C_GND),
    ("TB4", "A1", "supply NTC", C_AN),
]
TY = [43.18 - 2.54 * i for i in range(11)]
groups = {}
for i, (tb, *_r) in enumerate(TERM):
    groups.setdefault(tb, []).append(TY[i])
for tb, ys in groups.items():
    X0, Y0 = px(-1.6, max(ys) + 1.2)
    X1, Y1 = px(4.6, min(ys) - 1.2)
    add(f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{X1-X0:.1f}" height="{Y1-Y0:.1f}" rx="3" fill="#2e7d32" '
        f'fill-opacity="0.18" stroke="#2e7d32" stroke-width="2"/>')
    X, Y = px(-0.55, (max(ys) + min(ys)) / 2)
    text(X + 4, Y, tb, 10, "middle", "bold", "#1b5e20", rot=-90)
for i, (tb, net, field, col) in enumerate(TERM):
    y = TY[i]
    pad(1.28, y, 0.75, fill=col, stroke="#000", sw=1.2)
    X, Y = px(-1.6, y)
    text(X - 8, Y + 4, f"{i+1}  {net}", 11, "end", "bold", fill=col)
    text(X - 8, Y + 16, field, 9, "end", fill="#666")

# --- 5 V rail: bare tinned wire, component side -----------------------------------------------------
line([(38.10, 7.62), (38.10, 43.18), (55.88, 43.18)], C_5V, 4.5)
mtext(36.4, 27.0, "5 V rail, c6", 9, "middle", weight="bold", fill=C_5V, rot=-90)

# --- parts ------------------------------------------------------------------------------------------
standing(40.64, 43.18, 40.64, 45.72, "R10 1k", C_D8)
standing(55.88, 43.18, 58.42, 45.72, "R7 4.7k", C_DQ)
resistor(38.10, 10.16, 50.80, 10.16, "R8 10.0k", C_AN)
resistor(38.10, 15.24, 53.34, 15.24, "R9 10.0k", C_AN)
capacitor(50.80, 12.70, 52.07, 11.43, "C6", side="left")
capacitor(53.34, 17.78, 52.07, 16.51, "C7")

# --- solder-side links and wires ---------------------------------------------------------------------
# lead tails: A0 node c11 r13-r14 to the A0 duplicate pad; A1 node c12 r11-r14 to the A1 duplicate pad
line([(50.80, 12.70), (50.80, 7.62)], C_AN, 2.6, "5 3")
line([(53.34, 17.78), (53.34, 7.62)], C_AN, 2.6, "5 3")
# terminal wires
line([(1.28, 43.18), (2.6, 44.3), (37.0, 44.3), (38.10, 43.18)], C_5V, 2.2, "7 4")
line([(1.28, 40.64), (14.0, 46.9), (57.3, 46.9), (58.42, 48.26)], C_DQ, 2.2, "7 4")
line([(1.28, 38.10), (1.28, 35.56)], C_GND, 3.2, "2 2")
line([(1.28, 35.56), (2.4, 37.0), (2.4, 47.0), (1.28, 48.26)], C_GND, 2.2, "7 4")
line([(1.28, 33.02), (17.5, 33.02), (19.0, 47.4), (39.6, 47.4), (40.64, 48.26)], C_D8, 2.2, "7 4")
line([(1.28, 30.48), (19.4, 30.48), (19.4, 6.6), (49.6, 6.6), (50.80, 5.08)], C_AN, 2.2, "7 4")
line([(1.28, 27.94), (1.28, 20.32)], C_GND, 3.2, "2 2")
line([(1.28, 20.32), (2.75, 21.6), (2.75, 47.0), (3.82, 48.26)], C_GND, 2.2, "7 4")
line([(1.28, 17.78), (18.8, 17.78), (18.8, 6.1), (52.2, 6.1), (53.34, 5.08)], C_AN, 2.2, "7 4")

# --- callouts ---------------------------------------------------------------------------------------
X, Y = px(68.58, 53.34)
cx = X + 40
notes = [
    ("5 V rail", C_5V, ["Bare 22 AWG solid tinned wire on the", "component side: up c6 from the 5V",
                        "duplicate pad (38.10, 7.62) to r1, then", "along r1 to c13. Solder it only where a",
                        "lead lands: c6 r1, r12 and r14, c7 r1, c13 r1."]),
    ("Buses", C_3V3, ["Between the pad columns the shield runs", "buses of small holes, 3V3 (orange) and",
                      "GND (black) alternately, 3V3 first."]),
    ("Ground", C_GND, ["C6 and C7 take ground from the GND bus", "between c11 and c12 (b11). The terminals'",
                       "two ground groups (3–4 and 7–10) are", "bridged on the solder side and each runs",
                       "to the GND cluster top left."]),
    ("Header pads", "#555", ["Each header pin has two duplicate pads", "beside it. Terminal wires land on the",
                             "outer one, parts on the inner one."]),
    ("Do not use", "#8b1e1e", ["c6's neighbours are the GND bus (left)", "and the 3V3 bus (right). Keep solder on",
                               "the rail's pads small. Leave the CON", "pads at x 20.32 and 22.86 empty."]),
]
y = Y + 10
for title, col, lines_ in notes:
    text(cx, y, title, 13, weight="bold", fill=col)
    y += 18
    for ln in lines_:
        text(cx, y, ln, 11.5, fill="#222")
        y += 16
    y += 14

# legend
ly = BY + BH * S + 50
items = [(C_5V, "5 V", None), (C_DQ, "D2, 1-Wire", None), (C_D8, "D8, Y2 relay", None), (C_AN, "A0 / A1", None),
         (C_GND, "GND", None), (C_3V3, "3V3 bus (shield)", None), ("#444", "solder-side wire", "7 4")]
x = 20
for col, lab, dash in items:
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x}" y1="{ly}" x2="{x+36}" y2="{ly}" stroke="{col}" stroke-width="3"{extra}/>')
    text(x + 44, ly + 4, lab, 12)
    x += 190

foot = [
    "Parts: R7 4.7 kΩ D2 pull-up; R8, R9 10.0 kΩ 0.1 % NTC dividers; R10 1 kΩ D8 pull-up; C6, C7 0.1 µF on A0, A1. "
    "The shield's own R1–R6 and C1–C5 are why ours start at R7 and C6.",
    "Terminal pins sit in the outer column of CON-A/CON-B through-holes (1A, 3A … 15A, 2B, 4B, 6B), 2.54 mm apart, "
    "wire entries facing off the left edge.",
    "Before soldering, ring with a meter: the 5V, A0, A1, D2 and D8 duplicate pads to their header pins, and the "
    "top-left cluster to GND.",
]
for i, f in enumerate(foot):
    text(20, ly + 36 + i * 20, f, 12, fill="#333")

add("</svg>")
Path(__file__).with_name("mbr-air-handler-node-shield-layout.svg").write_text("\n".join(out) + "\n")
