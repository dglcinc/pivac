#!/usr/bin/env python3
"""Generate docs/mbr-air-handler-node-wiring.svg, the wiring of the master bedroom air-handler node.

Run from the repo root: python3 docs/mbr-air-handler-node-wiring.gen.py
"""
from pathlib import Path

W, H = 1640, 1220
out = []
add = out.append

C_R = "#d35400"      # 24 VAC R
C_C = "#7f8c8d"      # 24 VAC C
C_Y2 = "#8e44ad"     # Y2
C_5V = "#d62728"     # +5 V
C_GND = "#000000"    # ground
C_DQ = "#b8960b"     # 1-Wire data
C_AN = "#1f77b4"     # analog
C_D8 = "#2ca02c"     # relay sense
C_USB = "#555555"    # USB-C cable


def wire(points, color, width=2.5, dash=None):
    d = " ".join(f"{x},{y}" for x, y in points)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
        f'stroke-linejoin="round"{extra}/>')


def dot(x, y, color="#000"):
    add(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{color}"/>')


def screw(x, y, label=None, anchor="end", dx=-12, dy=4):
    add(f'<circle cx="{x}" cy="{y}" r="7" fill="#fff" stroke="#333" stroke-width="1.5"/>')
    add(f'<line x1="{x-4}" y1="{y-4}" x2="{x+4}" y2="{y+4}" stroke="#333" stroke-width="1.2"/>')
    if label:
        add(f'<text x="{x+dx}" y="{y+dy}" text-anchor="{anchor}" font-size="12" font-weight="bold">{label}</text>')


def text(x, y, s, size=13, anchor="start", weight="normal", fill="#000"):
    add(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}">{s}</text>')


def box(x, y, w, h, fill="#f4f4f4"):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="#333" stroke-width="1.5"/>')


def resistor_v(x, y1, y2, color, label, side="right"):
    """Vertical resistor from y1 to y2 with the body centred."""
    mid = (y1 + y2) / 2
    wire([(x, y1), (x, mid - 18)], color)
    wire([(x, mid + 18), (x, y2)], color)
    add(f'<rect x="{x-7}" y="{mid-18}" width="14" height="36" fill="#fff" stroke="#333" stroke-width="1.5"/>')
    tx, anchor = (x + 12, "start") if side == "right" else (x - 12, "end")
    text(tx, mid + 4, label, 11, anchor)


def cap_v(x, y1, y2, color, label, side="right"):
    mid = (y1 + y2) / 2
    wire([(x, y1), (x, mid - 4)], color)
    wire([(x, mid + 4), (x, y2)], C_GND)
    add(f'<line x1="{x-11}" y1="{mid-4}" x2="{x+11}" y2="{mid-4}" stroke="#333" stroke-width="2.5"/>')
    add(f'<line x1="{x-11}" y1="{mid+4}" x2="{x+11}" y2="{mid+4}" stroke="#333" stroke-width="2.5"/>')
    tx, anchor = (x + 15, "start") if side == "right" else (x - 15, "end")
    text(tx, mid + 4, label, 11, anchor)


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="Helvetica, Arial, sans-serif" font-size="13">')
add('<title>Master bedroom air-handler node wiring</title>')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
text(20, 30, "Master bedroom air-handler node: UNO R4 WiFi, two DS18B20, two 10K NTC, Y2 on a 792 relay", 18, weight="bold")
text(20, 52, "Everything but the sensors mounts on DIN rail. Filled dots are joins; bare crossings are not. "
     "Socket terminals as printed on the 70-782EL14-1: NC 1–4, NO 5–8, COM 9–12, coil 13 (A1) and 14 (A2).", 12, fill="#444")

# --- Unico control terminals ---------------------------------------------------------------
box(30, 110, 220, 250)
text(140, 135, "Unico M2430", 14, "middle", "bold")
text(140, 152, "control terminal strip", 11, "middle", fill="#555")
for y, lab in [(170, "R  (24 VAC hot)"), (230, "C  (24 VAC common)"), (290, "Y2 (high fan call)")]:
    screw(250, y, lab, "end", -14)
text(140, 340, "leave the existing wires in place;", 11, "middle", fill="#555")
text(140, 354, "add these under the same screws", 11, "middle", fill="#555")

# --- PS1 buck converter ---------------------------------------------------------------------
box(330, 100, 230, 150, "#eef4fb")
text(445, 125, "PS1  24 VAC → 5 V DC", 14, "middle", "bold")
text(445, 142, "buck converter, USB-C out", 11, "middle", fill="#555")
screw(330, 140, "AC", "start", 12)
screw(330, 200, "AC", "start", 12)
add('<rect x="548" y="160" width="16" height="22" rx="4" fill="#ddd" stroke="#333"/>')
text(445, 235, "USB-C", 11, "middle", fill="#555")

# R and C to the converter
wire([(257, 170), (290, 170), (290, 140), (323, 140)], C_R)
wire([(257, 230), (300, 230), (300, 200), (323, 200)], C_C)
dot(300, 230, C_C)

# --- K1 relay socket (same template as hpheat-hpcool-wiring.svg) ----------------------------
SX, SY = 330, 400
add(f'<rect x="{SX}" y="{SY}" width="220" height="300" rx="8" fill="#fbfbf2" stroke="#333" stroke-width="1.5"/>')
term = {12: (40, 50), 11: (90, 50), 10: (140, 50), 9: (190, 50),
        8: (40, 115), 7: (90, 115), 6: (140, 115), 5: (190, 115),
        4: (40, 180), 3: (90, 180), 2: (140, 180), 1: (190, 180),
        14: (65, 255), 13: (165, 255)}
for n, (cx, cy) in term.items():
    add(f'<circle cx="{SX+cx}" cy="{SY+cy}" r="14" fill="#fff" stroke="#333"/>')
    text(SX + cx, SY + cy + 4, str(n), 12, "middle", "bold")
for lab, cy in [("COM", 50), ("NO", 115), ("NC", 180)]:
    add(f'<text x="{SX+20}" y="{SY+cy}" font-size="10" fill="#666" text-anchor="end" '
        f'transform="rotate(-90 {SX+20} {SY+cy})">{lab}</text>')
text(SX + 65, SY + 282, "A2", 10, "middle", fill="#666")
text(SX + 165, SY + 282, "A1", 10, "middle", fill="#666")
text(SX + 110, SY + 292, "coil", 10, "middle", fill="#666")
text(SX + 110, SY - 12, "K1  792, 24 VAC coil, on socket", 14, "middle", "bold")


def T(n):
    return SX + term[n][0], SY + term[n][1]


# Coil: Y2 to 13 (A1), C to 14 (A2)
x13, y13 = T(13)
x14, y14 = T(14)
wire([(257, 290), (262, 290), (262, 760), (x13, 760), (x13, y13 + 14)], C_Y2)
wire([(300, 230), (300, 730), (x14, 730), (x14, y14 + 14)], C_C)

# Poles 1 and 2 in parallel: jumper COM 9-10 and NO 5-6
x9, y9 = T(9)
x10, y10 = T(10)
x5, y5 = T(5)
x6, y6 = T(6)
wire([(x10, y10 - 14), (x10, y10 - 26), (x9, y9 - 26), (x9, y9 - 14)], "#444", 2)
wire([(x6, y6 + 14), (x6, y6 + 24), (x5, y5 + 24), (x5, y5 + 14)], "#444", 2)
text(SX + 165, SY + 13, "jumper", 10, "middle", fill="#444")

# --- U1 Arduino + proto shield --------------------------------------------------------------
AX0, AY0, AX1, AY1 = 700, 330, 1100, 850
box(AX0, AY0, AX1 - AX0, AY1 - AY0, "#f2f8f2")
text(900, 318, "U1  Arduino UNO R4 WiFi + Olimex PROTO-SHIELD, on a DIN bracket", 14, "middle", "bold")
add(f'<rect x="{AX0-8}" y="349" width="16" height="22" rx="4" fill="#ddd" stroke="#333"/>')
text(AX0 + 14, 364, "USB-C", 11)

# USB-C cable PS1 -> U1
wire([(564, 171), (620, 171), (620, 360), (AX0 - 8, 360)], C_USB, 4)
text(626, 270, "USB-C cable", 11, fill="#555")

# Left screws: D8, GND (TB2)
Y_D8, Y_GL = 470, 540
screw(AX0, Y_D8, "D8", "start", 12, -9)
screw(AX0, Y_GL, "GND", "start", 12, -9)
wire([(x9 + 14, y9), (640, y9), (640, Y_D8), (AX0 - 7, Y_D8)], C_D8)
wire([(x5 + 14, y5), (660, y5), (660, Y_GL), (AX0 - 7, Y_GL)], C_GND)

# Right screws
Y_5V, Y_D2, Y_G1, Y_A0, Y_G2, Y_S2, Y_A1, Y_G3, Y_S3 = 378, 492, 548, 600, 640, 680, 730, 770, 810
for y, lab in [(Y_5V, "5V"), (Y_D2, "D2"), (Y_G1, "GND"), (Y_A0, "A0"), (Y_G2, "GND"), (Y_S2, "SH"),
               (Y_A1, "A1"), (Y_G3, "GND"), (Y_S3, "SH")]:
    screw(AX1, y, lab, "end", -12, -9)

# Internal +5 V rail
wire([(800, Y_5V), (AX1 - 7, Y_5V)], C_5V)
# R10 1k pull-up for D8
wire([(AX0 + 7, Y_D8), (800, Y_D8)], C_D8)
dot(800, Y_D8, C_D8)
resistor_v(800, Y_5V, Y_D8, C_5V, "R10 1k")
dot(800, Y_5V, C_5V)
# R7 4.7k 1-Wire pull-up 5V -> D2
resistor_v(1040, Y_5V, Y_D2, C_5V, "R7 4.7k")
dot(1040, Y_5V, C_5V)
wire([(1040, Y_D2), (AX1 - 7, Y_D2)], C_DQ)
dot(1040, Y_D2, C_DQ)
# R8 / C6 on A0
resistor_v(970, Y_5V, Y_A0, C_5V, "R8 10.0k")
dot(970, Y_5V, C_5V)
wire([(970, Y_A0), (AX1 - 7, Y_A0)], C_AN)
dot(970, Y_A0, C_AN)
cap_v(970, Y_A0, Y_G2, C_AN, "C6 0.1µ")
wire([(970, Y_G2), (AX1 - 7, Y_G2)], C_GND)
# R9 / C7 on A1
resistor_v(900, Y_5V, Y_A1, C_5V, "R9 10.0k")
dot(900, Y_5V, C_5V)
wire([(900, Y_A1), (AX1 - 7, Y_A1)], C_AN)
dot(900, Y_A1, C_AN)
cap_v(900, Y_A1, Y_G3, C_AN, "C7 0.1µ")
wire([(900, Y_G3), (AX1 - 7, Y_G3)], C_GND)
# GND bus joining the shield's GND screws and the left GND
wire([(1055, Y_G1), (1055, 835)], C_GND)
wire([(AX1 - 7, Y_G1), (1055, Y_G1)], C_GND)
for y in (Y_S2, Y_S3):
    wire([(1055, y), (AX1 - 7, y)], C_GND)
for y in (Y_G1, Y_G2, Y_S2, Y_G3, Y_S3):
    dot(1055, y)
wire([(AX0 + 7, Y_GL), (740, Y_GL), (740, 835), (1055, 835)], C_GND)
text(760, 828, "shield GND", 10, fill="#555")
text(760, 700, "D3 free (flow meter)", 11, fill="#555")
text(760, 716, "layout: shield-layout.svg", 11, fill="#555")

# --- DS18B20 probes on the 1-Wire bus -------------------------------------------------------
BUS_END = 1560
wire([(AX1 + 7, Y_5V), (BUS_END, Y_5V)], C_5V)
wire([(AX1 + 7, Y_D2), (BUS_END, Y_D2)], C_DQ)
wire([(AX1 + 7, Y_G1), (BUS_END, Y_G1)], C_GND)
text(1176, Y_5V - 8, "VDD", 11, fill=C_5V)
text(1176, Y_D2 - 8, "DQ", 11, fill=C_DQ)
text(1176, Y_G1 - 8, "GND", 11)


def probe(x, title, sub):
    box(x, 150, 200, 110, "#fff8e8")
    text(x + 100, 175, title, 13, "middle", "bold")
    text(x + 100, 192, sub, 11, "middle", fill="#555")
    text(x + 100, 208, "DS18B20 stainless probe", 11, "middle", fill="#555")
    for dx, col, y, lab in [(40, C_5V, Y_5V, "VDD"), (100, C_DQ, Y_D2, "DQ"), (160, C_GND, Y_G1, "GND")]:
        wire([(x + dx, 260), (x + dx, y)], col)
        dot(x + dx, y, col)
        text(x + dx, 250, lab, 10, "middle", fill="#555")


probe(1180, "T1  water to coil", "coil supply pipe")
probe(1400, "T2  water from coil", "coil return pipe")

# --- NTC air sensors ------------------------------------------------------------------------


def ntc(y_sig, y_gnd, y_sh, title, sub):
    bx = 1430
    box(bx, y_sig - 30, 180, y_gnd - y_sig + 60, "#eef4fb")
    text(bx + 90, y_sig - 8, title, 13, "middle", "bold")
    text(bx + 90, y_sig + 10, sub, 11, "middle", fill="#555")
    text(bx + 90, y_gnd + 18, "10K NTC duct sensor", 11, "middle", fill="#555")
    wire([(AX1 + 7, y_sig), (bx, y_sig)], C_AN)
    wire([(AX1 + 7, y_gnd), (bx, y_gnd)], C_GND)
    # shield around the pair, drain to the GND screw at the board end only
    add(f'<rect x="1190" y="{y_sig-12}" width="220" height="{y_gnd-y_sig+24}" rx="10" fill="none" '
        f'stroke="#888" stroke-width="1.5" stroke-dasharray="6 4"/>')
    wire([(1190, y_gnd + 6), (1180, y_gnd + 6), (1180, y_sh), (AX1 + 7, y_sh)], "#888", 1.8, "4 3")
    text(1300, y_gnd + 28, "Belden 8451; drain to SH, grounded at the board only", 10, "middle", fill="#555")


ntc(Y_A0, Y_G2, Y_S2, "RA  return air", "return plenum, before coil")
ntc(Y_A1, Y_G3, Y_S3, "SA  supply air", "supply plenum, after blower")

# --- XT1-XT9 Phoenix QUATTRO feed-through blocks on the DIN rail ----------------------------
XT_X = 1128
text(XT_X + 20, AY0 - 34, "XT1–XT9 QUATTRO", 11, "middle", "bold")
for i, y in enumerate((Y_5V, Y_D2, Y_G1, Y_A0, Y_G2, Y_S2, Y_A1, Y_G3, Y_S3)):
    add(f'<rect x="{XT_X}" y="{y-11}" width="40" height="22" rx="3" fill="#e8f0e8" stroke="#2e7d32" stroke-width="1.5"/>')
    text(XT_X + 20, y + 4, f"XT{i+1}", 10, "middle", "bold", "#1b5e20")

# --- DIN rail order -------------------------------------------------------------------------
add('<rect x="30" y="880" width="1580" height="26" fill="#d9d9d9" stroke="#999"/>')
text(40, 898, "35 mm DIN rail, left to right:  PS1 buck converter   ·   K1 792 relay on its socket   ·   "
     "XT1–XT9 QUATTRO feed-through blocks   ·   U1 Arduino + proto shield on DIN bracket", 12)

# --- Legend and notes -----------------------------------------------------------------------
lx, ly = 30, 945
for i, (col, lab) in enumerate([(C_R, "24 VAC R"), (C_C, "24 VAC C"), (C_Y2, "Y2"), (C_5V, "+5 V"),
                                (C_GND, "GND"), (C_DQ, "1-Wire DQ"), (C_AN, "analog A0/A1"),
                                (C_D8, "D8 relay sense"), (C_USB, "USB-C cable")]):
    x = lx + i * 172
    wire([(x, ly), (x + 40, ly)], col, 3)
    text(x + 48, ly + 4, lab, 12)

notes = [
    "1. K1: Y2 to coil 13 (A1), C to coil 14 (A2). Poles 1 and 2 are paralleled (COM 9–10, NO 5–6) so a dirty contact on one does not drop the reading.",
    "   COM goes to D8 and NO to GND; R10 pulls D8 to 5 V, so D8 reads LOW while Y2 is on and the contact carries 5 mA, enough to keep it clean.",
    "2. Field cables land on XT1–XT9, both probes' like leads on one block; one 22 AWG patch wire runs from each block to its shield terminal. Confirm VDD/DQ/GND on the probe before landing.",
    "3. Shield parts: R7 4.7 kΩ, R8 and R9 10.0 kΩ 0.1 % 25 ppm, R10 1 kΩ, C6 and C7 0.1 µF. Placement and the 5 V rail: mbr-air-handler-node-shield-layout.svg.",
    "4. PS1 and the probes: with a non-isolated converter, the Arduino's GND rides on the 24 VAC transformer. Check PS1 input-to-output with an ohmmeter (open = isolated)",
    "   and each probe sheath and NTC body to its leads (open). Unplug PS1's USB-C before plugging a laptop into U1.",
]
for i, n in enumerate(notes):
    text(30, 995 + i * 22, n, 12)

add("</svg>")
Path(__file__).with_name("mbr-air-handler-node-wiring.svg").write_text("\n".join(out) + "\n")
