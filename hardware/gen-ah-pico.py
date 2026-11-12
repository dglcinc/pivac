#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""The air-handler node's Pico W carrier for the Hammond 1593K, Rev C (docs/air-handler-shield-pcb-plan.md §0).

Run with KiCad's Python. Writes hardware/ahpc-board/ahpc-board.kicad_pcb with the parts placed and the
nets assigned, and the hand-laid copper in place; ahp-build.sh routes it. Rev B as ordered is
hardware/ahp-board and git history. Coordinates: x 0.3-56.7 between the side walls, y 0-56 from the top panel (USB-A,
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

W, L = 57.0, 56.0      # coordinate frame; the box centre is x 28.5, y 28
X0, X1 = 0.3, 56.7     # board edges: 56.4 wide, against 56.62 between the walls in Hammond's model
CX, CY = W / 2, L / 2
BOSS = [(CX - 14, CY - 14), (CX + 14, CY - 14), (CX - 14, CY + 14), (CX + 14, CY + 14)]
COVER = [(CX - 25, 20.7), (CX + 25, 20.7)]
NOTCH = 3.4            # half width of the cover-post notch
HEAD = 2.8             # radius of a #4 pan head
R_0805 = ("Resistor_SMD", "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
C_0805 = ("Capacitor_SMD", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")

ap = argparse.ArgumentParser()
ap.add_argument("--models"); ap.add_argument("--box"); ap.add_argument("--out", default=os.path.join(HERE, "ahpc-board"))
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
# 0.5 mm applies to the rectified 24 VAC side only; GND, +5V and 3V3 are the low side, beside 0.5 mm pitch pins
# a project file left from an earlier run would keep its net class patterns
if os.path.exists(os.path.join(args.out, "ahpc-board.kicad_pro")):
    os.remove(os.path.join(args.out, "ahpc-board.kicad_pro"))
B = gb.Board(os.path.join(args.out, "ahpc-board.kicad_pcb"), W, L, power_clearance=0.5, power_nets=("VS", "COM", "AC*"))
ds = B.board.GetDesignSettings(); ds.m_MinClearance = FromMM(0.15)
ds.m_TentViasFront = True; ds.m_TentViasBack = True    # the Pico sits flat on the front; vias must not touch its test pads
supply = pcbnew.NETCLASS("Supply"); supply.SetClearance(FromMM(0.2)); supply.SetTrackWidth(FromMM(0.4))
supply.SetViaDiameter(FromMM(0.8)); supply.SetViaDrill(FromMM(0.4)); ds.m_NetSettings.SetNetclass("Supply", supply)
for pat in ("GND", "+5V", "3V3", "VSYS", "VBUS"):
    ds.m_NetSettings.SetNetclassPatternAssignment(pat, "Supply")

# --- outline with the two cover-post notches
for d in [d for d in B.board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]:
    B.board.Remove(d)
ny0, ny1 = COVER[0][1] - NOTCH, COVER[0][1] + NOTCH
nx = 7.0
pts = [(X0, 0), (X1, 0), (X1, ny0), (W - nx, ny0), (W - nx, ny1), (X1, ny1), (X1, L), (X0, L), (X0, ny1), (nx, ny1), (nx, ny0), (X0, ny0)]
for a, b in zip(pts, pts[1:] + pts[:1]):
    B.line(a[0], a[1], b[0], b[1], layer="Edge.Cuts", width=0.1)

# --- Pico W flat, micro-USB at the top edge
PY = 26.8
pico = B.lib("U4", "Module", "RaspberryPi_Pico_W_SMD_HandSolder", CX, PY, 0, value="Pico W SC0918")
pico.Reference().SetPosition(mm(CX, 54.3)); pico.Reference().SetTextAngleDegrees(0)
# the footprint's keep-outs: the two wide ones cover the sensor headers either side of the antenna and
# the four small ones TP2 and TP3's new holes, so they go and the antenna gets its own to the board edge
for z in pico.Zones():
    r = z.GetBoundingBox()
    if pcbnew.ToMM(r.GetLeft()) < 8:
        z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    elif pcbnew.ToMM(r.GetBottom()) < 4:
        z.SetDoNotAllowPads(False)
B.rect_keepout(21.4, 43.8, 35.6, L, layers=("F.Cu", "B.Cu"), name="antenna", pads=False, footprints=False, tracks=True, vias=True, pour=True)
# plated holes under TP2 (D-) and TP3 (D+), 0.2 toward the centre to clear the USB leg holes;
# filled with solder from the back
for num, x in (("TP2", 0.8), ("TP3", -0.8)):
    p = gb._pad(pico, num, CX + x, PY - 24.3, 1.1, 0.7)
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
    B.place(f"H{i}", h, x, y, 0, value="#4 x 1/4"); h.Reference().SetVisible(False)

# --- top edge: USB-A jack, Wurth 61400416021, face on the edge (datasheet hole pattern)
JX = 8.7
JY = -1.5              # the jack stands 1.5 past the board edge, so its pins and legs clear the post beneath it
j = pcbnew.FOOTPRINT(B.board); j.SetFPID(pcbnew.LIB_ID("pivac", "USB_A_61400416021"))
# Wurth: with the opening toward the viewer pin 1 is on the left, so seen from above with the opening
# toward the top edge pin 1 is on the right
for n, x in ((1, 3.5), (2, 1.0), (3, -1.0), (4, -3.5)):
    gb._pad(j, n, x, 12.99, 1.5, 0.92)
for x in (-6.57, 6.57):
    gb._pad(j, "S", x, 10.28, 2.9, 2.3)
gb._fp_rect(j, -7.25, 1.5, 7.25, 14.0, pcbnew.F_SilkS, 0.12)
gb._fp_rect(j, -7.6, 1.5, 7.6, 14.3, pcbnew.F_CrtYd, 0.05)
B.place("J4", j, JX, JY, 0, value="61400416021"); j.Reference().SetVisible(False)
B.text("USB-A", JX, 15.3, size=0.9, bold=True)

# --- top edge: 24 VAC, Phoenix MC 1,5/2-G-3,81 footprint, entry toward the edge
MX = 47.5
mc = B.lib("J1", "Connector_Phoenix_MC", "PhoenixContact_MC_1,5_2-G-3.81_1x02_P3.81mm_Horizontal", MX + 1.905, 8.5, 180, value="3.81 mm 2-pin 24VAC")
mc.Reference().SetVisible(False)
B.text("24 VAC", 42.0, 5.0, size=0.8, bold=True, rot=90)

# --- bottom edge: sensors on PTSM surface-mount headers, entry toward the edge
hdr = {}
for ref, n, x, lab in (("J2", 3, 9.6, "1-WIRE"), ("J3", 4, 48.2, "AIR NTC")):
    fp = gb.ptsm_hh_smd(B, n)
    B.place(ref, fp, x, L, 180, value=f"PTSM 0,5/{n}-HH-2,5-SMD")
    fp.Reference().SetVisible(False)
    if ref == "J3":     # its anchor pad clears the Pico's edge pads by 0.6 mm; the two courtyards overlap by 0.2
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_CrtYd:
                g.SetLayer(pcbnew.F_Fab)
    B.text(lab, x, L - 11.9, size=0.8, bold=True)

# --- power
B.lib("F1", "Fuse", "Fuse_1812_4532Metric_Pad1.30x3.40mm_HandSolder", 48.6, 14.2, 0, value="PTC 0.2A")
B.lib("D2", "Diode_SMD", "D_SMA", 54.8, 13.0, 90, value="SMAJ43CA")
u1 = gb.sip8_converter(B, pin5=True)
B.place("U1", u1, 0, 0, 90, value="TMR 3-4811WI")
bb = u1.GetCourtyard(pcbnew.F_CrtYd).BBox()
dx, dy = 40.25 - pcbnew.ToMM(bb.GetLeft()), 16.8 - pcbnew.ToMM(bb.GetTop())
u1.SetPosition(mm(dx, dy))
for g in u1.GraphicalItems():
    if g.GetLayer() == pcbnew.F_CrtYd:      # D1 and C1 stand against the body, which ends at x 49.7
        g.SetLayer(pcbnew.F_Fab)
u1.Reference().SetPosition(mm(47.6, 40.15)); u1.Reference().SetTextAngleDegrees(0)
B.lib("C1", "Capacitor_SMD", "CP_Elec_6.3x7.7", 53.2, 29.6, 90, value="47u 50V")
B.lib("D1", "Diode_SMD", "D_SMA", 53.0, 37.5, 0, value="S1M")
B.lib("C2", "Capacitor_SMD", "C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", 53.5, 41.9, 0, value="10u")

# --- I2C: DS2482 and ADS1115 beside the Pico, under the jack
B.lib("U2", "Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", 12.0, 20.7, 0, value="DS2482S-100+")
B.lib("C3", *C_0805, 12.0, 26.3, 0, value="100n")
B.lib("U3", "Package_SO", "MSOP-10_3x3mm_P0.5mm", 12.0, 31.5, 0, value="ADS1115IDGS")
B.lib("C4", *C_0805, 12.0, 35.9, 0, value="100n")
B.lib("R1", *R_0805, 3.7, 26.3, 90, value="4k7")
B.lib("R2", *R_0805, 6.9, 26.3, 90, value="4k7")
B.lib("R3", *R_0805, 3.7, 30.3, 90, value="10k0 0.1%")
B.lib("R4", *R_0805, 6.9, 30.3, 90, value="10k0 0.1%")
B.lib("C5", *C_0805, 3.7, 34.3, 90, value="100n")
B.lib("C6", *C_0805, 6.9, 34.3, 90, value="100n")

# --- status LEDs: top-view 0805s on the back, under the USB-A side's cover screw (x 3.5), shining through six
# holes drilled in the base's floor, which carries the label. Seen from outside the floor, the column runs
# down from the right-hand screw hole, PWR first. The parts are the unbranded 200-piece 0805 kit, so each
# is checked for polarity with the diode test before it goes on.
LX = CX - 25.0         # the cover screw's x
LED = (("LED1", 26.5, "PWR", "R5", "3V3", None, "green"), ("LED2", 30.5, "FAN", "R6", "L_FAN", 16, "yellow"),
       ("LED3", 34.5, "Y1", "R7", "L_Y1", 11, "blue"), ("LED4", 38.5, "Y2", "R8", "L_Y2", 12, "blue"),
       ("LED5", 42.5, "W1", "R9", "L_W1", 14, "red"), ("LED6", 46.5, "W2", "R10", "L_W2", 15, "red"))
for ref, y, lab, rref, net, pin, part in LED:
    fp = B.lib(ref, "LED_SMD", "LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder", LX, y, 0, back=True, value="0805 " + part)
    if B.pad_xy(ref, 1)[0] > LX:       # the cathode goes outboard, toward the ground bus at the edge
        fp.SetOrientationDegrees(180)
    fp.Reference().SetVisible(False)
    r = B.lib(rref, *R_0805, LX + 3.1, y, 90, back=True, value="220R")
    r.Reference().SetVisible(False)
    B.text(lab, LX + 5.6, y, layer="B.SilkS", size=0.7, bold=True)

# --- USB lockout (plan §0, Rev C), on the back: a laptop on the micro-USB cuts U1 off the Pico and J4 off its data
# Q1 and R11 behind the Pico's VBUS and VSYS pins; U5 under the Pico, straight below TP2 and TP3 between the
# Pico's USB leg holes, its common pins up toward them and its HSD1 pins down, from where J4 is routed
B.lib("Q1", "Package_TO_SOT_SMD", "SOT-23_Handsoldering", 42.6, 5.2, 0, back=True, value="DMG2305UX-7")
B.lib("R11", *R_0805, 40.6, 9.3, 90, back=True, value="100k")
UY = 9.5
u5 = B.lib("U5", "Package_SO", "MSOP-10_3x3mm_P0.5mm", CX, UY, 90, back=True, value="FSUSB42MUX")
for rot in (90, 270):       # pins 1-5 along the top, D+ (3) left of D- (4), under TP3 and TP2
    u5.SetOrientationDegrees(rot)
    if B.pad_xy("U5", 1)[1] < UY and B.pad_xy("U5", 3)[0] < B.pad_xy("U5", 4)[0]:
        break
else:
    raise SystemExit("no orientation of U5 puts pins 1-5 at the top with D+ left of D-")
B.lib("C7", *C_0805, 24.6, 8.7, 180, back=True, value="100n")     # pad 1 (3V3) toward U5
B.lib("R12", *R_0805, 23.6, 13.8, 90, back=True, value="22k")
B.lib("R13", *R_0805, 25.8, 13.8, 90, back=True, value="33k")
for ref, x, y, ang in (("Q1", 43.0, 2.2, 0), ("R11", 38.7, 9.3, 0), ("R12", 22.1, 13.8, 90), ("R13", 27.3, 13.8, 90)):
    t = B.refs[ref].Reference(); t.SetPosition(mm(x, y)); t.SetTextAngleDegrees(ang)

for u in ("U3", "U5"):              # 0.5 mm pitch leaves 0.195 mm between pads
    for p in B.refs[u].Pads():
        p.SetLocalClearance(FromMM(0.15))

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
nets("J4", (1, "+5V"), (2, "D-"), (3, "D+"), (4, "GND"))     # J4's data comes through U5
for p in B.refs["J4"].Pads():
    if p.GetNumber() == "S":
        p.SetNet(B.net("GND"))
# Pico W: 40 VBUS, 39 VSYS, 36 3V3(OUT), 6 GP4 SDA, 7 GP5 SCL, grounds 3 8 13 18 23 28 33 38. VBUS is the
# micro-USB's own 5 V; U1 reaches VSYS through Q1, which a laptop's VBUS turns off (Pico datasheet §4.5)
nets("U4", (40, "VBUS"), (39, "VSYS"), (36, "3V3"), (6, "SDA"), (7, "SCL"), ("TP2", "PD-"), ("TP3", "PD+"))
# DMG2305UX SOT-23: 1 gate, 2 source, 3 drain
nets("Q1", (1, "VBUS"), (2, "VSYS"), (3, "+5V"))
nets("R11", (1, "VBUS"), (2, "GND"))
# FSUSB42MUX MSOP-10: 1 VCC, 2 SEL, 3 D+, 4 D-, 5 GND, 6 HSD1-, 7 HSD1+, 8 HSD2-, 9 HSD2+, 10 OE.
# OE high (a laptop's VBUS through R12 over R13, 3.0 V) disconnects; low with SEL low joins D to HSD1
nets("U5", (1, "3V3"), (2, "GND"), (3, "PD+"), (4, "PD-"), (5, "GND"), (6, "D-"), (7, "D+"), (10, "OE"))
nets("C7", (1, "3V3"), (2, "GND"))
nets("R12", (1, "VBUS"), (2, "OE")); nets("R13", (1, "OE"), (2, "GND"))
for g in (3, 8, 13, 18, 23, 28, 33, 38):
    B.connect("U4", g, "GND")
# DS2482-100 SO-8: 1 VCC, 2 IO, 3 GND, 4 SCL, 5 SDA, 6 PCTLZ, 7 AD1, 8 AD0
nets("U2", (1, "3V3"), (2, "OW"), (3, "GND"), (4, "SCL"), (5, "SDA"), (7, "GND"), (8, "GND"))
nets("C3", (1, "3V3"), (2, "GND"))
# ADS1115 MSOP-10: 1 ADDR, 2 ALERT, 3 GND, 4 AIN0, 5 AIN1, 6 AIN2, 7 AIN3, 8 VDD, 9 SDA, 10 SCL
nets("U3", (1, "GND"), (3, "GND"), (4, "SUP"), (5, "RET"), (6, "3V3"), (7, "3V3"), (8, "3V3"), (9, "SDA"), (10, "SCL"))
nets("C4", (1, "3V3"), (2, "GND"))
# LEDs: 3V3 for power; Y1 GP8 pin 11, Y2 GP9 pin 12, W1 GP10 pin 14, W2 GP11 pin 15, fan GP12 pin 16
for ref, y, lab, rref, net, pin, part in LED:
    nets(rref, (1, "A_" + ref), (2, net)); nets(ref, (2, "A_" + ref), (1, "GND"))
    if pin:
        B.connect("U4", pin, net)
nets("R1", (1, "3V3"), (2, "SDA")); nets("R2", (1, "3V3"), (2, "SCL"))
nets("R3", (1, "3V3"), (2, "SUP")); nets("R4", (1, "3V3"), (2, "RET"))
nets("C5", (1, "SUP"), (2, "GND")); nets("C6", (1, "RET"), (2, "GND"))
nets("J2", (1, "3V3"), (2, "OW"), (3, "GND"))
nets("J3", (1, "SUP"), (2, "GND"), (3, "RET"), (4, "GND"))

# --- hand-laid copper, locked, because Freerouting leaves these open: U3's 0.5 mm pads, whose 0.195 mm gaps
# are under its clearance, and the 24 VAC side, whose 0.5 mm clearance has little room around U1 and the notch
def via(net, x, y, dia=1.0, drill=0.5):
    v = pcbnew.PCB_VIA(B.board); v.SetPosition(mm(x, y)); v.SetWidth(FromMM(dia)); v.SetDrill(FromMM(drill))
    v.SetNet(B.net(net)); v.SetLocked(True); B.board.Add(v)
def path(net, layer, *pts, width=0.5):
    for a, b in zip(pts, pts[1:]):
        B.track(net, a[0], a[1], b[0], b[1], layer=layer, width=width)
u3 = lambda n: B.pad_xy("U3", n)
xl, xr = u3(1)[0], u3(6)[0]
path("GND", "F.Cu", u3(1), (8.7, u3(1)[1]), (8.7, u3(3)[1]), u3(3), width=0.2)
path("GND", "F.Cu", (8.7, u3(2)[1]), (8.1, u3(2)[1]), width=0.2)
path("SUP", "F.Cu", u3(4), (8.9, u3(4)[1]), (8.3, u3(4)[1] + 0.6), width=0.2)
via("SUP", 8.3, u3(4)[1] + 0.6, 0.8, 0.4)
path("RET", "F.Cu", u3(5), (9.3, u3(5)[1]), (9.3, u3(5)[1] + 0.8), width=0.2)
via("RET", 9.3, u3(5)[1] + 0.8, 0.8, 0.4)
path("3V3", "F.Cu", u3(8), (15.5, u3(8)[1]), (15.5, u3(6)[1] + 0.9), width=0.2)
path("3V3", "F.Cu", u3(7), (15.5, u3(7)[1]), width=0.2); path("3V3", "F.Cu", u3(6), (15.5, u3(6)[1]), width=0.2)
path("SDA", "F.Cu", u3(9), (15.9, u3(9)[1]), width=0.2)
path("SCL", "F.Cu", u3(10), (15.5, u3(10)[1]), (15.5, u3(10)[1] - 0.7), width=0.2)
pj1, pj2 = B.pad_xy("J1", 1), B.pad_xy("J1", 2)
f1a, f1b = B.pad_xy("F1", 1), B.pad_xy("F1", 2)
d2a, d2c = B.pad_xy("D2", 1), B.pad_xy("D2", 2)
d1v, d1a = B.pad_xy("D1", 1), B.pad_xy("D1", 2)
c1v, c1c = B.pad_xy("C1", 1), B.pad_xy("C1", 2)
u1c, u1v = B.pad_xy("U1", 1), B.pad_xy("U1", 2)
# LEDs: anode to its resistor beside it; every cathode on one ground bus along the outboard pads, taken to
# the front through one via between LED2 and LED3
for ref, y, lab, rref, net, pin, part in LED:
    k, a_ = B.pad_xy(ref, 1), B.pad_xy(ref, 2)
    assert k[0] < a_[0], "the cathode is outboard"
    r1 = B.pad_xy(rref, 1)
    path("A_" + ref, "B.Cu", a_, (a_[0] + 0.9, a_[1]), r1, width=0.25)
kx = B.pad_xy("LED1", 1)[0]
path("GND", "B.Cu", (kx, LED[0][1]), (kx, LED[-1][1]), width=0.4)
gy = (LED[1][1] + LED[2][1]) / 2
via("GND", kx, gy, 0.8, 0.4)
c5g = B.pad_xy("C5", 2)
path("GND", "F.Cu", (kx, 25.0), (kx, 45.0), width=0.4)        # a ground spine on the front for the router, as on Rev B
path("GND", "F.Cu", (kx, c5g[1]), c5g, width=0.4)
# U5's 0.5 mm pads, hand laid because Freerouting cannot leave pads closer than its clearance. D+ and D- come
# straight down from TP3 and TP2 between the Pico's USB leg holes into pins 3 and 4. VCC leaves pin 1 by its
# inner end to C7; SEL and GND (2, 5) leave by their inner ends onto a ground strip under the body that
# reaches the pour. Pins 6, 7 and 10 get stubs downward, staggered, for the router.
u = lambda n: B.pad_xy("U5", n)
tp3, tp2 = B.pad_xy("U4", "TP3"), B.pad_xy("U4", "TP2")
path("PD+", "B.Cu", tp3, (tp3[0], 5.6), (u(3)[0], 6.4), u(3), width=0.2)
path("PD-", "B.Cu", tp2, (tp2[0], 5.6), (u(4)[0], 5.9), u(4), width=0.2)
assert B.pad_xy("C7", 1)[0] > B.pad_xy("C7", 2)[0], "C7 pad 1 faces U5"
path("3V3", "B.Cu", u(1), (u(1)[0], 8.7), B.pad_xy("C7", 1), width=0.25)
path("GND", "B.Cu", u(2), (u(2)[0], UY), (CX + 2.7, UY), width=0.25)
path("GND", "B.Cu", u(5), (u(5)[0], UY), width=0.25)
for n, reach in ((6, 2.3), (7, 1.3), (10, 1.3)):
    x, y = u(n)
    net = B.refs["U5"].FindPadByNumber(str(n)).GetNetname()
    path(net, "B.Cu", (x, y), (x, y + reach), width=0.2)
path("ACR", "F.Cu", pj1, (47.8, 11.2), f1a)
path("ACF", "F.Cu", f1b, (52.6, d2a[1]), d2a)
path("ACF", "F.Cu", f1b, (49.4, 16.4)); via("ACF", 49.4, 16.4)
path("ACF", "B.Cu", (49.4, 16.4), (49.0, 17.0), (49.0, 26.0), (55.7, 33.0), (55.7, 35.6)); via("ACF", 55.7, 35.6)
path("ACF", "F.Cu", (55.7, 35.6), d1a)
path("VS", "F.Cu", u1v, (50.5, u1v[1]), d1v); path("VS", "F.Cu", (51.2, u1v[1]), (50.5, u1v[1])); path("VS", "F.Cu", (51.2, u1v[1]), c1v)
path("COM", "B.Cu", u1c, (45.9, u1c[1]), (47.5, 35.4), (47.5, 12.0), pj2)
path("COM", "B.Cu", (47.5, 12.0), (52.9, 12.0), (52.9, d2c[1])); via("COM", 52.9, d2c[1])
path("COM", "F.Cu", (52.9, d2c[1]), d2c)
path("COM", "F.Cu", c1c, (47.5, c1c[1])); via("COM", 47.5, c1c[1])

# no copper near the notches: Freerouting takes the edge clearance from the outline's rectangle only
for x0, x1, name in ((X0, 7.5, "left notch"), (49.6, X1, "right notch")):
    B.rect_keepout(x0, 16.9 if x0 == X0 else 17.0, x1, 24.5, layers=("F.Cu", "B.Cu"), name=name, pads=False, footprints=False, tracks=True, vias=True, pour=False)
# no vias through the monogram and legends, front or back
for x0, y0, x1, y1, name in ((2.9, 36.4, 8.1, 44.1, "monogram"), (7.5, 37.0, 16.0, 38.9, "AIR HANDLER"), (8.0, 38.9, 11.8, 41.6, "PICO W Rev C"),
                             (CX - 8.0, 48.8, CX + 8.0, 52.0, "licence"),
                             *((LX + 4.5, y - 0.7, LX + 6.7, y + 0.7, "LED legend") for y in (26.5, 30.5, 34.5, 38.5, 42.5, 46.5))):
    B.rect_keepout(x0, y0, x1, y1, layers=("F.Cu", "B.Cu"), name=name, pads=False, footprints=False, tracks=False, vias=True, pour=False)

# --- test loops for a probe hook, the rev A shield's plated loops: VS and COM on the 24 VAC side, GND on the low side
for ref, x, y, net, lab, lx, ly in (("TP1", 49.8, 41.7, "VS", "VS", 47.9, 41.9), ("TP2", 55.2, 3.2, "COM", "COM", 55.2, 5.3),
                                    ("TP3", 2.4, 15.7, "GND", "GND", 4.8, 15.7)):
    fp = pcbnew.FOOTPRINT(B.board); fp.SetFPID(pcbnew.LIB_ID("pivac", "TestLoop"))
    gb._pad(fp, 1, 0, 0, 1.8, 1.0)
    B.place(ref, fp, x, y, 0, value=net); fp.Reference().SetVisible(False)
    B.connect(ref, 1, net); B.text(lab, lx, ly, size=0.7, bold=True)
path("VS", "F.Cu", (49.8, 41.7), (50.0, 39.6), (50.9, 38.4))
path("COM", "B.Cu", (55.2, 3.2), (52.9, 5.5), (52.9, 11.0))

# --- legends
gb.monogram(B, 4.2, 40.2, 0.8)
B.text("AIR HANDLER", 7.7, 38.0, size=0.8, bold=True, left=True)
B.text("PICO W", 8.2, 39.5, size=0.7, left=True)
B.text("Rev C", 8.2, 40.8, size=0.7, left=True)
# the lower left screw head and the 1-wire legend leave no room beside the title block on the front, so the
# licence goes on the back, in the open pour under the Pico
B.text("\u00a9 2026 David Lewis", CX, 49.6, layer="B.SilkS", size=0.9)
B.text("CC BY-NC 4.0", CX, 51.2, layer="B.SilkS", size=0.9)
# reference designators the part bodies or their neighbours would cover
for ref, x, y, angle in (("F1", 52.3, 14.2, 90), ("D2", 54.8, 8.6, 0), ("C1", 51.2, 25.0, 0)):
    t = B.refs[ref].Reference(); t.SetPosition(mm(x, y)); t.SetTextAngleDegrees(angle)
# R and C mark J1's pins, so the footprint's pin 1 triangle moves off the silkscreen
for g in mc.GraphicalItems():
    if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() != "PCB_TEXT" and pcbnew.ToMM(g.GetBoundingBox().GetTop()) > 10.2:
        g.SetLayer(pcbnew.F_Fab)
# U1's outline stops inside the body on the right, where D1 and C1 stand against it
for g in u1.GraphicalItems():
    if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() != "PCB_TEXT" and g.GetShape() == pcbnew.SHAPE_T_RECT:
        g.SetLayer(pcbnew.F_Fab)
for a, b in (((49.6, 16.99), (40.44, 16.99)), ((40.44, 16.99), (40.44, 39.2)), ((40.44, 39.2), (49.6, 39.2))):
    B.line(a[0], a[1], b[0], b[1], "F.SilkS", 0.12)
for lab, ref, pad in (("R", "J1", 1), ("C", "J1", 2)):
    x, y = B.pad_xy(ref, pad); B.text(lab, x, y + 2.6, size=0.7, bold=True)
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
for ref in ("U2", "U3", "C1", "D1", "D2", "F1", "J1", "J2", "J3", "J4", "C2"):
    bb = B.refs[ref].GetCourtyard(pcbnew.F_CrtYd).BBox()
    print(ref, *(round(pcbnew.ToMM(v), 2) for v in (bb.GetLeft(), bb.GetRight(), bb.GetTop(), bb.GetBottom())))
B.save()
print("wrote", B.path)
