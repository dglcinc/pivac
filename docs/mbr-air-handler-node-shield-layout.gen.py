#!/usr/bin/env python3
"""Generate the parts layout on the Olimex PROTO-SHIELD rev A: docs/mbr-air-handler-node-shield-layout.svg (the whole
board) and docs/mbr-air-handler-node-shield-holes.svg (the proto area enlarged, with every lead hole named).

Run from the repo root: python3 docs/mbr-air-handler-node-shield-layout.gen.py

Coordinates are millimetres in the frame of Olimex's mechanical drawing (manual page 9): origin at the
bottom-left corner of the board, x to the right, y up, the DIGITAL header along the top edge.

Parts are drawn as outlines under the pads, so every hole stays visible. A coloured ring marks a hole that takes a
part's lead, a pink pad a joint on the 5 V rail, and a coloured dot a hole where a solder-side wire lands.
"""
import math
from pathlib import Path

S = 11.0                 # px per mm; reset for each drawing
BX, BY = 240, 120         # SVG position of the board's top-left corner (x = 0, y = 53.34)
BW, BH = 68.58, 53.34

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
C_JOINT = "#f7b3b3"

COLS = [25.40 + 2.54 * i for i in range(13)]          # c1..c13
ROWS = [43.18 - 2.54 * i for i in range(14)]          # r1..r14

# ref, value, mounting, first hole, second hole, colour, label position, first-hole name, second-hole name
PARTS = [
    ("R7", "4.7 kΩ", "standing", (55.88, 43.18), (58.42, 45.72), C_DQ, (53.34, 44.45), "c13 r1", "D2 inner pad"),
    ("R10", "1 kΩ", "standing", (40.64, 43.18), (40.64, 45.72), C_D8, (42.55, 44.45), "c7 r1", "D8 inner pad"),
    ("R8", "10.0 kΩ", "flat", (38.10, 10.16), (50.80, 10.16), C_AN, (43.18, 11.43), "c6 r14", "c11 r14"),
    ("R9", "10.0 kΩ", "flat", (38.10, 15.24), (53.34, 15.24), C_AN, (45.72, 16.51), "c6 r12", "c12 r12"),
    ("C6", "0.1 µF", "disc", (50.80, 12.70), (52.07, 11.43), C_AN, (49.53, 12.70), "c11 r13", "b11 hole"),
    ("C7", "0.1 µF", "disc", (53.34, 17.78), (52.07, 16.51), C_AN, (55.88, 16.51), "c12 r11", "b11 hole"),
]
RAIL = [(38.10, 7.62), (38.10, 43.18), (55.88, 43.18)]
RAIL_JOINTS = [(38.10, 7.62), (38.10, 43.18), (38.10, 15.24), (38.10, 10.16), (40.64, 43.18), (55.88, 43.18)]

# solder-side wires: points, colour, terminal tag (None for lead tails and ground runs), tag position
WIRES = [
    ([(1.28, 43.18), (2.6, 44.3), (37.0, 44.3), (38.10, 43.18)], C_5V, "pos 1", (33.0, 44.3)),
    ([(1.28, 40.64), (14.0, 46.9), (57.3, 46.9), (58.42, 48.26)], C_DQ, "pos 2", (54.0, 46.9)),
    ([(1.28, 35.56), (2.4, 37.0), (2.4, 47.0), (1.28, 48.26)], C_GND, None, None),
    ([(1.28, 33.02), (17.5, 33.02), (19.0, 47.4), (39.6, 47.4), (40.64, 48.26)], C_D8, "pos 5", (35.5, 47.4)),
    ([(1.28, 30.48), (19.4, 30.48), (19.4, 6.6), (49.6, 6.6), (50.80, 5.08)], C_AN, "pos 6", (46.5, 6.6)),
    ([(1.28, 20.32), (2.75, 21.6), (2.75, 47.0), (3.82, 48.26)], C_GND, None, None),
    ([(1.28, 17.78), (18.8, 17.78), (18.8, 6.1), (52.2, 6.1), (53.34, 5.08)], C_AN, "pos 11", (33.0, 6.1)),
    ([(50.80, 12.70), (50.80, 7.62)], C_AN, None, None),       # A0 lead tail, c11 r13-r14 to the A0 pad
    ([(53.34, 17.78), (53.34, 7.62)], C_AN, None, None),       # A1 lead tail, c12 r11-r14 to the A1 pad
]
BRIDGES = [[(1.28, 38.10), (1.28, 35.56)], [(1.28, 27.94), (1.28, 20.32)]]


def px(x, y):
    return BX + x * S, BY + (BH - y) * S


def text(x, y, s, size=12, anchor="start", weight="normal", fill="#000", rot=None, halo=False):
    t = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    h = ' stroke="#fff" stroke-width="3.5" stroke-linejoin="round" paint-order="stroke"' if halo else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
        f'font-weight="{weight}" fill="{fill}"{h}{t}>{s}</text>')


def mtext(x, y, s, size=10, anchor="middle", **kw):
    X, Y = px(x, y)
    text(X, Y + size * 0.35, s, size, anchor, **kw)


def circ(x, y, r, fill="#fff", stroke=C_PAD, sw=1.6, dash=None, fop=None):
    X, Y = px(x, y)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    extra += f' fill-opacity="{fop}"' if fop is not None else ""
    add(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="{r*S:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw:.1f}"{extra}/>')


def pad(x, y, r=0.75, fill="#fff", stroke=C_PAD, sw=None):
    circ(x, y, r, fill, stroke, sw if sw is not None else 0.145 * S)


def hole(x, y, color):
    circ(x, y, 0.38, color, "none", 0)


def line(pts, color, width=2.0, dash=None, opacity=1.0):
    d = " ".join("%.1f,%.1f" % px(x, y) for x, y in pts)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width:.1f}" '
        f'stroke-linejoin="round" stroke-linecap="round" opacity="{opacity}"{extra}/>')


def dash(a, b):
    k = S / 11
    return f"{a*k:.1f} {b*k:.1f}"


def body(kind, p1, p2, color):
    """Part body as a see-through outline; the pads drawn after it stay visible."""
    sw = 0.18 * S
    if kind == "flat":
        (x1, y1), (x2, _) = p1, p2
        mx = (x1 + x2) / 2
        X0, Y0 = px(mx - 3.15, y1 + 1.2)
        add(f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{6.3*S:.1f}" height="{2.4*S:.1f}" rx="{0.6*S:.1f}" '
            f'fill="{color}" fill-opacity="0.12" stroke="{color}" stroke-width="{sw:.1f}"/>')
        line([p1, (mx - 3.15, y1)], color, 0.12 * S)
        line([(mx + 3.15, y1), p2], color, 0.12 * S)
    elif kind == "standing":
        circ(*p1, 1.3, color, color, sw, dash(4, 3), fop=0.10)
        line([p1, p2], color, 0.12 * S)
    else:
        (x1, y1), (x2, y2) = p1, p2
        X, Y = px((x1 + x2) / 2, (y1 + y2) / 2)
        X1, Y1 = px(x1, y1)
        X2, Y2 = px(x2, y2)
        ang = math.degrees(math.atan2(Y2 - Y1, X2 - X1))
        add(f'<ellipse cx="{X:.1f}" cy="{Y:.1f}" rx="{1.9*S:.1f}" ry="{1.0*S:.1f}" fill="{color}" fill-opacity="0.12" '
            f'stroke="{color}" stroke-width="{sw:.1f}" stroke-dasharray="{dash(4, 3)}" '
            f'transform="rotate({ang:.1f} {X:.1f} {Y:.1f})"/>')


def draw_proto(detail):
    """Buses, the rail, parts, solder-side wires, then every pad and hole on top, then the marks and names."""
    fs = 13 if detail else 8
    for k in range(14):
        bx = 24.13 + 2.54 * k
        line([(bx, 42.6), (bx, 10.9)], C_3V3 if k % 2 == 0 else C_GND, 0.2 * S, opacity=0.35)
    line(RAIL, C_5V, 0.42 * S, opacity=0.85)
    for ref, val, kind, p1, p2, col, *_ in PARTS:
        body(kind, p1, p2, col)
    for pts, col, *_ in WIRES:
        line(pts, col, 0.2 * S, dash(7, 4))
    for pts in BRIDGES:
        line(pts, C_GND, 0.29 * S, dash(2, 2))
    # bus holes and pads, on top of the parts and wires
    for k in range(14):
        bx = 24.13 + 2.54 * k
        for m in range(13):
            hole(bx, 11.43 + 2.54 * m, C_3V3 if k % 2 == 0 else C_GND)
    for x in COLS:
        for y in ROWS:
            pad(x, y, fill=C_JOINT if (round(x, 2), round(y, 2)) in RAIL_JOINTS else "#fff")
    # headers and their duplicate pads
    dig_left = ["AREF", "GND", "D13", "D12", "D11", "D10", "D9", "D8"]
    dig_right = ["D7", "D6", "D5", "D4", "D3", "D2", "D1", "D0"]
    for i, name in enumerate(dig_left):
        hx, gx = 23.88 + 2.54 * i, 22.86 + 2.54 * i
        pad(hx, 50.80, 0.8)
        for y in (48.26, 45.72):
            pad(gx, y)
        mtext(hx, 52.4, name, fs, fill="#555")
    for i, name in enumerate(dig_right):
        hx = 45.72 + 2.54 * i
        pad(hx, 50.80, 0.8)
        for y in (48.26, 45.72):
            pad(hx, y)
        mtext(hx, 52.4, name, fs, fill="#555")
    for names, x0 in ((["A6", "A7", "RST", "3V3", "5V", "GND", "GND", "VIN"], 27.94),
                      (["A0", "A1", "A2", "A3", "A4", "A5"], 50.80)):
        for i, name in enumerate(names):
            hx = x0 + 2.54 * i
            for y in (2.54, 5.08, 7.62):
                pad(hx, y, fill=C_JOINT if (round(hx, 2), y) in RAIL_JOINTS else "#fff")
            mtext(hx, 0.9, name, fs, fill="#555")
    # lead holes: a ring in the part's colour
    for ref, val, kind, p1, p2, col, *_ in PARTS:
        for (x, y) in (p1, p2):
            on_bus = abs((x - 24.13) / 2.54 - round((x - 24.13) / 2.54)) < 0.01
            circ(x, y, 0.62 if on_bus else 1.08, "none", col, 0.22 * S)
    # wire landings: a dot in the wire's colour
    for pts, col, *_ in WIRES:
        circ(*pts[-1], 0.32, col, "none", 0)
    for x, y in ((50.80, 10.16), (53.34, 15.24)):          # tails pass under these lead holes and join them
        circ(x, y, 0.25, C_AN, "none", 0)
    # grid names
    cfs = 12 if detail else 7
    for i, x in enumerate(COLS):
        mtext(x, 8.89, f"c{i+1}", cfs, fill="#777", halo=True)
    for j, y in enumerate(ROWS):
        mtext(58.5 if detail else 59.6, y, f"r{j+1}", cfs, "start", fill="#777")
    # part names beside their bodies, between pad rows
    for ref, val, kind, p1, p2, col, (lx, ly), *_ in PARTS:
        mtext(lx, ly, ref, (13 if ref == "C6" else 15) if detail else 9.5, weight="bold", fill=col, halo=True)


# ===================================================================================================
# Drawing 1: the whole board
# ===================================================================================================
W, H = 1560, 860
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="Helvetica, Arial, sans-serif" font-size="12">')
add('<title>Master bedroom air-handler node: PROTO-SHIELD layout</title>')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
text(20, 32, "Master bedroom air-handler node: parts on the Olimex PROTO-SHIELD rev A, component side", 18, weight="bold")
text(20, 54, "To scale, 11 px per mm. Parts are outlines under the pads; the red 5 V rail is on the component side; dashed "
     "wires run on the solder side, drawn as seen through the board.", 12, fill="#444")
text(20, 72, "Coordinates in mm from the board's bottom-left corner, as on Olimex's mechanical drawing. Columns c1–c13 "
     "run left to right, rows r1–r14 top to bottom. mbr-air-handler-node-shield-holes.svg enlarges the proto area.",
     12, fill="#444")

# --- board outline -------------------------------------------------------------------------------
outline = [(0, 0), (66.04, 0), (68.58, 2.54), (68.58, 38.10), (66.04, 40.64), (66.04, 53.34), (0, 53.34), (0, 0)]
d = " ".join("%.1f,%.1f" % px(x, y) for x, y in outline)
add(f'<polygon points="{d}" fill="#fbeaea" stroke="#8b1e1e" stroke-width="2"/>')
for hx, hy in [(13.97, 2.54), (15.24, 50.80), (66.04, 7.62), (66.04, 35.56)]:
    circ(hx, hy, 1.6, "#fff", "#8b1e1e", 1.5)

# --- CON-A / CON-B SMD areas (faint) ----------------------------------------------------------------
for (x0, y0, x1, y1) in [(6.0, 26.0, 18.5, 43.5), (6.0, 6.0, 18.5, 24.5)]:
    X0, Y0 = px(x0, y1)
    X1, Y1 = px(x1, y0)
    add(f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{X1-X0:.1f}" height="{Y1-Y0:.1f}" fill="#f1dede" '
        f'stroke="{C_FAINT}" stroke-dasharray="3 3"/>')
mtext(12.2, 34.5, "CON-A SMD", 9, fill="#999")
mtext(12.2, 15.0, "CON-B SMD", 9, fill="#999")

# --- the shield's own parts (faint) -----------------------------------------------------------------
for (x0, y0, x1, y1, lab) in [(61.5, 40.0, 65.0, 44.5, "LED1/2"), (63.0, 25.5, 67.5, 31.0, "BUT1"),
                              (63.0, 13.0, 67.5, 18.5, "BUT2")]:
    X0, Y0 = px(x0, y1)
    X1, Y1 = px(x1, y0)
    add(f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{X1-X0:.1f}" height="{Y1-Y0:.1f}" fill="#eee" stroke="{C_FAINT}"/>')
    mtext((x0 + x1) / 2, (y0 + y1) / 2, lab, 8, fill="#999")

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

draw_proto(False)

# CON through-holes and the GND / 3V3 clusters, after the wires so the wire ends land on them
for i in range(30):
    y = 43.18 - 1.27 * i
    pad(1.28 if i % 2 == 0 else 3.82, y, 0.7)
    pad(22.86 if i % 2 == 0 else 20.32, y, 0.7, stroke=C_FAINT)
for x in (1.28, 3.82, 6.35, 8.89, 11.43):
    for y in (48.26, 50.80):
        pad(x, y, 0.8, fill="#444", stroke="#222")
    for y in (2.54, 5.08):
        pad(x, y, 0.8, fill="#f6c46a", stroke=C_3V3)
mtext(6.35, 45.6, "GND cluster", 9, fill="#222")
mtext(6.35, 0.6, "3V3 cluster", 9, fill=C_3V3)
for i, (tb, net, field, col) in enumerate(TERM):
    y = TY[i]
    pad(1.28, y, 0.75, fill=col, stroke="#000", sw=1.2)
    X, Y = px(-1.6, y)
    text(X - 8, Y + 4, f"{i+1}  {net}", 11, "end", "bold", fill=col)
    text(X - 8, Y + 16, field, 9, "end", fill="#666")
mtext(36.83, 27.0, "5 V rail, c6", 9, "middle", weight="bold", fill=C_5V, rot=-90, halo=True)

# --- callouts ---------------------------------------------------------------------------------------
X, Y = px(68.58, 53.34)
cx = X + 40
notes = [
    ("5 V rail", C_5V, ["Bare 22 AWG solid tinned wire on the", "component side: up c6 from the 5V",
                        "duplicate pad (38.10, 7.62) to r1, then", "along r1 to c13. Solder it only at the",
                        "pink pads: c6 r1, r12 and r14, c7 r1,", "c13 r1 and the 5V pad."]),
    ("Holes", "#555", ["A ring marks a hole that takes a part's", "lead; a dot marks a hole where a",
                       "solder-side wire lands. The enlarged", "drawing names every one."]),
    ("Buses", C_3V3, ["Between the pad columns the shield runs", "buses of small holes, 3V3 (orange) and",
                      "GND (black) alternately, 3V3 first."]),
    ("Ground", C_GND, ["C6 and C7 take ground from the GND bus", "between c11 and c12 (b11). The terminals'",
                       "two ground groups (3–4 and 7–10) are", "bridged on the solder side and each runs",
                       "to the GND cluster top left."]),
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
    y += 12

# legend
ly = BY + BH * S + 50
items = [(C_5V, "5 V", None), (C_DQ, "D2, 1-Wire", None), (C_D8, "D8, Y2 relay", None), (C_AN, "A0 / A1", None),
         (C_GND, "GND", None), (C_3V3, "3V3 bus (shield)", None), ("#444", "solder-side wire", "7 4")]
x = 20
for col, lab, dsh in items:
    extra = f' stroke-dasharray="{dsh}"' if dsh else ""
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


# ===================================================================================================
# Drawing 2: the proto area enlarged, every lead hole named
# ===================================================================================================
out.clear()
S = 20.0
X_MIN, X_MAX, Y_MIN, Y_MAX = 23.0, 61.6, 0.0, 53.34
BX, BY = 40 - X_MIN * S, 110 - (BH - Y_MAX) * S
PW, PH = (X_MAX - X_MIN) * S, (Y_MAX - Y_MIN) * S
W, H = int(40 + PW + 470), int(110 + PH + 40)

PAGE_W = 7.25            # inches: fits the printable width of US letter and A4 with the usual margins
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}in" height="{PAGE_W * H / W:.2f}in" '
    f'viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif" font-size="13">')
add('<title>Master bedroom air-handler node: PROTO-SHIELD lead holes</title>')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
text(20, 32, "PROTO-SHIELD rev A: the proto area enlarged, component side", 20, weight="bold")
text(20, 56, "Prints on one page at 2.9 times actual size. Columns c1–c13 left to right, rows r1–r14 top to bottom; the small holes between the "
     "columns are the 3V3 (orange) and GND (black) buses.", 13, fill="#444")
text(20, 76, "Parts are outlines under the pads. Ring: a part's lead hole. Pink pad: a joint on the 5 V rail. "
     "Dot: a solder-side wire lands here.", 13, fill="#444")

X0, Y0 = px(X_MIN, Y_MAX)
add(f'<clipPath id="area"><rect x="{X0:.1f}" y="{Y0:.1f}" width="{PW:.1f}" height="{PH:.1f}"/></clipPath>')
add(f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{PW:.1f}" height="{PH:.1f}" fill="#fbeaea" stroke="#8b1e1e" '
    f'stroke-width="1.5" stroke-dasharray="6 4"/>')
add('<g clip-path="url(#area)">')
draw_proto(True)
for pts, col, tag, pos in WIRES:
    if tag:
        mtext(*pos, f"from {tag}", 12, weight="bold", fill=col, halo=True)
mtext(36.83, 27.0, "5 V rail", 13, "middle", weight="bold", fill=C_5V, rot=-90, halo=True)
mtext(52.07, 21.59, "b11 GND", 11, weight="bold", fill=C_GND, halo=True, rot=-90)
add('</g>')

# hole list
tx = 40 + PW + 30
ty = 130
text(tx, ty, "Lead holes, x and y in mm", 16, weight="bold")
ty += 26
for ref, val, kind, p1, p2, col, _lab, n1, n2 in PARTS:
    text(tx, ty, f"{ref}  {val}", 14, weight="bold", fill=col)
    text(tx + 120, ty, {"flat": "lying flat", "standing": "standing", "disc": "disc, standing"}[kind], 13, fill="#555")
    ty += 20
    for name, (x, y) in ((n1, p1), (n2, p2)):
        text(tx + 14, ty, name, 13)
        text(tx + 140, ty, f"{x:.2f}, {y:.2f}", 13, fill="#333")
        ty += 18
    ty += 10
ty += 6
text(tx, ty, "Rail joints (pink)", 16, weight="bold", fill=C_5V)
ty += 22
for ln in ["5V inner pad (38.10, 7.62); c6 r1, r12", "and r14; c7 r1; c13 r1."]:
    text(tx, ty, ln, 13)
    ty += 18
ty += 14
text(tx, ty, "Solder-side wires (dots)", 16, weight="bold")
ty += 22
for ln in ["pos 1 → c6 r1", "pos 2 → D2 outer pad (58.42, 48.26)", "pos 5 → D8 outer pad (40.64, 48.26)",
           "pos 6 → A0 outer pad (50.80, 5.08)", "pos 11 → A1 outer pad (53.34, 5.08)",
           "A0 tail: c11 r13 and r14 → A0 inner pad", "A1 tail: c12 r11 to r14 → A1 inner pad"]:
    text(tx, ty, ln, 13)
    ty += 18
ty += 14
for ln in ["Inner pads sit at y 45.72 (DIGITAL) and", "7.62 (POWER, ANALOG); outer pads at", "48.26 and 5.08."]:
    text(tx, ty, ln, 13, fill="#555")
    ty += 18

add("</svg>")
Path(__file__).with_name("mbr-air-handler-node-shield-holes.svg").write_text("\n".join(out) + "\n")
