#!/usr/bin/env python3
"""The air-handler node's Pico W carrier for the Hammond 1593K (docs/air-handler-shield-pcb-plan.md §0).

Run with KiCad's Python. Writes hardware/ahp-board/ahp-board.kicad_pcb with the parts placed and the
nets assigned, unrouted. Coordinates: x 0-57 across the end panels, y 0-56 from the top panel (USB-A,
micro-USB, 24 VAC) to the bottom panel (sensors). The board's centre is the box's centre, so the
box's posts, from Hammond's 1593K drawing, stand at x 28.5 +/- 14, y 28 +/- 14 and the cover posts at
x 28.5 +/- 25, y 20.7.

    gen-ah-pico.py [--models DIR] [--box open|closed]
adds the 3D models of the render: parts.wrl always, base.wrl with --box, lid.wrl and plugs.wrl closed.
"""
import argparse, importlib.util, math, os, sys
import pcbnew
from pcbnew import FromMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gen_boards", os.path.join(HERE, "gen-boards.py"))
gb = importlib.util.module_from_spec(spec); spec.loader.exec_module(gb)
mm = gb.mm

W, L = 57.0, 56.0
CX, CY = W / 2, L / 2
BOSS = [(CX - 14, CY - 14), (CX + 14, CY - 14), (CX - 14, CY + 14), (CX + 14, CY + 14)]
COVER = [(CX - 25, 20.7), (CX + 25, 20.7)]
NOTCH = 3.4            # half width of the cover-post notch
HEAD = 2.8             # radius of a #4 pan head
R_0805 = ("Resistor_SMD", "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
C_0805 = ("Capacitor_SMD", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")

ap = argparse.ArgumentParser()
ap.add_argument("--models"); ap.add_argument("--box"); ap.add_argument("--out", default=os.path.join(HERE, "ahp-board"))
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
B = gb.Board(os.path.join(args.out, "ahp-board.kicad_pcb"), W, L, power_clearance=0.5)

# --- outline with the two cover-post notches
for d in [d for d in B.board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]:
    B.board.Remove(d)
ny0, ny1 = COVER[0][1] - NOTCH, COVER[0][1] + NOTCH
nx = 7.0
pts = [(0, 0), (W, 0), (W, ny0), (W - nx, ny0), (W - nx, ny1), (W, ny1), (W, L), (0, L), (0, ny1), (nx, ny1), (nx, ny0), (0, ny0)]
for a, b in zip(pts, pts[1:] + pts[:1]):
    B.line(a[0], a[1], b[0], b[1], layer="Edge.Cuts", width=0.1)

# --- Pico W flat, micro-USB at the top edge
PY = 26.8
pico = B.lib("U4", "Module", "RaspberryPi_Pico_W_SMD_HandSolder", CX, PY, 0, value="Pico W SC0918")
pico.Reference().SetVisible(False)
# plated holes under TP2 (D-) and TP3 (D+), 0.15 toward the centre to clear the USB leg holes;
# filled with solder from the back
for num, x in (("TP2", 0.85), ("TP3", -0.85)):
    p = gb._pad(pico, num, CX + x, PY - 24.3, 1.3, 0.8)
# pads beside a mounting screw are shortened so a #4 pan head clears them
for bx, by in BOSS[1:]:
    for pad in pico.Pads():
        if not pad.GetNumber().isdigit():
            continue
        px, py = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
        if abs(py - by) < HEAD + 0.9 and (px - CX) * (bx - CX) > 0:
            s = pad.GetSize()
            pad.SetSize(VECTOR2I(FromMM(2.6), s.y))
            pad.SetPosition(mm(px - math.copysign(0.3, px - CX), py))

# --- mounting holes: three screws; the post at the top left stands under the USB jack
for i, (x, y) in enumerate(BOSS[1:], start=1):
    h = pcbnew.FOOTPRINT(B.board)
    h.SetFPID(pcbnew.LIB_ID("pivac", "MH_4"))
    q = pcbnew.PAD(h); q.SetNumber(""); q.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    q.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    q.SetSize(VECTOR2I(FromMM(3.2), FromMM(3.2))); q.SetDrillSize(VECTOR2I(FromMM(3.2), FromMM(3.2)))
    q.SetLayerSet(pcbnew.PAD.UnplatedHoleMask()); h.Add(q)
    gb._fp_rect(h, -HEAD, -HEAD, HEAD, HEAD, pcbnew.F_CrtYd, 0.05)
    B.place(f"H{i}", h, x, y, 0, value="#4 x 1/4"); h.Reference().SetVisible(False)

# --- top edge: USB-A jack, Wurth 61400416021, face on the edge (datasheet hole pattern)
JX = 8.0
j = pcbnew.FOOTPRINT(B.board); j.SetFPID(pcbnew.LIB_ID("pivac", "USB_A_61400416021"))
for n, x in ((1, -3.5), (2, -1.0), (3, 1.0), (4, 3.5)):
    gb._pad(j, n, x, 12.99, 1.5, 0.92)
for x in (-6.57, 6.57):
    gb._pad(j, "S", x, 10.28, 2.9, 2.3)
gb._fp_rect(j, -7.25, 0, 7.25, 14.0, pcbnew.F_SilkS, 0.12)
gb._fp_rect(j, -7.6, 0, 7.6, 14.3, pcbnew.F_CrtYd, 0.05)
B.place("J4", j, JX, 0, 0, value="61400416021"); j.Reference().SetVisible(False)
B.text("USB-A", JX, 15.3, size=0.9, bold=True)

# --- top edge: 24 VAC, Phoenix MC 1,5/2-G-3,81 footprint, entry toward the edge
MX = 47.5
mc = B.lib("J1", "Connector_Phoenix_MC", "PhoenixContact_MC_1,5_2-G-3.81_1x02_P3.81mm_Horizontal", MX + 1.905, 8.5, 180, value="3.81 mm 2-pin 24VAC")
mc.Reference().SetVisible(False)
B.text("24 VAC", 41.3, 5.0, size=0.8, bold=True, rot=90)

# --- bottom edge: sensors on PTSM surface-mount headers, entry toward the edge
hdr = {}
for ref, n, x, lab in (("J2", 3, 9.6, "1-WIRE"), ("J3", 4, 48.5, "AIR NTC")):
    fp = gb.ptsm_hh_smd(B, n)
    B.place(ref, fp, x, L, 180, value=f"PTSM 0,5/{n}-HH-2,5-SMD")
    fp.Reference().SetVisible(False)
    B.text(lab, x + (1.5 if ref == "J3" else 0), L - 12.2, size=0.8, bold=True)

# --- power
B.lib("F1", "Fuse", "Fuse_1812_4532Metric_Pad1.30x3.40mm_HandSolder", 48.6, 14.2, 0, value="PTC 0.2A")
B.lib("D2", "Diode_SMD", "D_SMA", 54.8, 14.2, 90, value="SMAJ43CA")
u1 = gb.sip8_converter(B, pin5=True)
B.place("U1", u1, 0, 0, 90, value="TMR 3-4811WI")
bb = u1.GetCourtyard(pcbnew.F_CrtYd).BBox()
dx, dy = 40.25 - pcbnew.ToMM(bb.GetLeft()), 16.8 - pcbnew.ToMM(bb.GetTop())
u1.SetPosition(mm(dx, dy))
u1.Reference().SetPosition(mm(47.6, 41.2)); u1.Reference().SetTextAngleDegrees(0)
B.lib("C1", "Capacitor_SMD", "CP_Elec_6.3x7.7", 53.5, 29.6, 90, value="47u 50V")
B.lib("D1", "Diode_SMD", "D_SMA", 53.5, 37.2, 0, value="S1M")
B.lib("C2", "Capacitor_SMD", "C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", 53.5, 41.9, 0, value="10u")

# --- I2C: DS2482 and ADS1115 beside the Pico, under the jack
B.lib("U2", "Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", 12.0, 20.7, 0, value="DS2482S-100+")
B.lib("C3", *C_0805, 12.0, 26.3, 0, value="100n")
B.lib("U3", "Package_SO", "MSOP-10_3x3mm_P0.5mm", 12.0, 31.5, 0, value="ADS1115IDGS")
B.lib("C4", *C_0805, 12.0, 35.6, 0, value="100n")
B.lib("R1", *R_0805, 3.2, 26.8, 90, value="4k7")
B.lib("R2", *R_0805, 6.4, 26.8, 90, value="4k7")
B.lib("R3", *R_0805, 3.2, 31.6, 90, value="10k0 0.1%")
B.lib("R4", *R_0805, 6.4, 31.6, 90, value="10k0 0.1%")
B.lib("C5", *C_0805, 3.2, 36.4, 90, value="100n")
B.lib("C6", *C_0805, 6.4, 36.4, 90, value="100n")

# --- nets
def nets(ref, *pairs):
    for pad, n in pairs:
        B.connect(ref, pad, n)
nets("J1", (1, "ACR"), (2, "COM"))
nets("F1", (1, "ACR"), (2, "ACF"))
nets("D2", (1, "ACF"), (2, "COM"))
nets("D1", (1, "VS"), (2, "ACF"))
nets("C1", (1, "VS"), (2, "COM"))
nets("U1", (1, "COM"), (2, "VS"), (6, "+5V"), (7, "GND"))
nets("C2", (1, "+5V"), (2, "GND"))
nets("J4", (1, "+5V"), (2, "D-"), (3, "D+"), (4, "GND"))
# Pico W: 40 VBUS, 36 3V3(OUT), 6 GP4 SDA, 7 GP5 SCL, grounds 3 8 13 18 23 28 33 38
nets("U4", (40, "+5V"), (36, "3V3"), (6, "SDA"), (7, "SCL"), ("TP2", "D-"), ("TP3", "D+"))
for g in (3, 8, 13, 18, 23, 28, 33, 38):
    B.connect("U4", g, "GND")
# DS2482-100 SO-8: 1 VCC, 2 IO, 3 GND, 4 SCL, 5 SDA, 6 PCTLZ, 7 AD1, 8 AD0
nets("U2", (1, "3V3"), (2, "OW"), (3, "GND"), (4, "SCL"), (5, "SDA"), (7, "GND"), (8, "GND"))
nets("C3", (1, "3V3"), (2, "GND"))
# ADS1115 MSOP-10: 1 ADDR, 2 ALERT, 3 GND, 4 AIN0, 5 AIN1, 6 AIN2, 7 AIN3, 8 VDD, 9 SDA, 10 SCL
nets("U3", (1, "GND"), (3, "GND"), (4, "SUP"), (5, "RET"), (6, "3V3"), (7, "GND"), (8, "3V3"), (9, "SDA"), (10, "SCL"))
nets("C4", (1, "3V3"), (2, "GND"))
nets("R1", (1, "3V3"), (2, "SDA")); nets("R2", (1, "3V3"), (2, "SCL"))
nets("R3", (1, "3V3"), (2, "SUP")); nets("R4", (1, "3V3"), (2, "RET"))
nets("C5", (1, "SUP"), (2, "GND")); nets("C6", (1, "RET"), (2, "GND"))
nets("J2", (1, "3V3"), (2, "OW"), (3, "GND"))
nets("J3", (1, "SUP"), (2, "GND"), (3, "RET"), (4, "GND"))

# --- legends
gb.monogram(B, 3.6, 41.2, 0.6)
B.text("AIR HANDLER", 6.2, 38.7, size=0.8, bold=True, left=True)
B.text("PICO W", 6.8, 40.2, size=0.7, left=True)
B.text("Rev B", 6.8, 41.5, size=0.7, left=True)
B.refs["F1"].Reference().SetPosition(mm(47.5, 11.7))
B.refs["F1"].Reference().SetTextSize(VECTOR2I(FromMM(0.7), FromMM(0.7)))
for lab, ref, pad in (("R", "J1", 1), ("C", "J1", 2)):
    x, y = B.pad_xy(ref, pad); B.text(lab, x, y + 1.7, size=0.7, bold=True)
for ref, labs in (("J2", "VDG"), ("J3", "S-R-")):
    for i, lab in enumerate(labs, start=1):
        x, y = B.pad_xy(ref, i); B.text(lab, x, y - 2.4, size=0.7, bold=True)

# --- 3D models for the render: one carrier footprint at the board's centre, model z 0 on the top face
if args.models:
    m = pcbnew.FOOTPRINT(B.board); m.SetFPID(pcbnew.LIB_ID("pivac", "render"))
    names = ["parts.wrl"]
    if args.box:
        names.append("base.wrl")
    if args.box == "closed":
        names += ["lid.wrl", "plugs.wrl"]
    for n in names:
        md = pcbnew.FP_3DMODEL(); md.m_Filename = os.path.join(args.models, n)
        md.m_Scale = pcbnew.VECTOR3D(1 / 2.54, 1 / 2.54, 1 / 2.54)
        m.Models().push_back(md)
    B.place("MDL", m, CX, CY, 0, value=""); m.Reference().SetVisible(False)

# --- checks
for (bx, by), name in zip(BOSS[1:], ("top right", "bottom left", "bottom right")):
    worst = 99.0
    for fp in B.board.GetFootprints():
        if fp.GetReference().startswith("H") or fp.GetReference() == "MDL":
            continue
        for p in fp.Pads():
            if not p.GetNumber():      # the footprint's paste apertures carry no number and no copper
                continue
            bb = p.GetBoundingBox()
            ax = max(pcbnew.ToMM(bb.GetLeft()) - bx, bx - pcbnew.ToMM(bb.GetRight()), 0)
            ay = max(pcbnew.ToMM(bb.GetTop()) - by, by - pcbnew.ToMM(bb.GetBottom()), 0)
            d = math.hypot(ax, ay) - HEAD
            if d < worst:
                worst, who = d, f"{fp.GetReference()}.{p.GetNumber()}"
    print(f"screw {name}: {worst:.2f} mm from head to nearest pad, {who}")
for ref in ("U1", "U2", "U3", "C1", "D1", "D2", "F1", "J1", "J2", "J3", "J4", "C2"):
    bb = B.refs[ref].GetCourtyard(pcbnew.F_CrtYd).BBox()
    print(ref, *(round(pcbnew.ToMM(v), 2) for v in (bb.GetLeft(), bb.GetRight(), bb.GetTop(), bb.GetBottom())))
B.save()
print("wrote", B.path)
