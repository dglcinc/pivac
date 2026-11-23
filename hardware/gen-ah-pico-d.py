#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""The AirMaster Pico W carrier Rev D (docs/air-handler-pico-revd-plan.md): every part on the front, every part
one JLCPCB places or solders, for the printed case of ahpd-case.py.

Run with KiCad's Python. Writes hardware/ahpd-board/ahpd-board.kicad_pcb with the parts placed, the nets assigned
and the hand-laid copper in place; ahpd-build.sh routes it. The circuit and the Pico's pin assignments are Rev C's,
so the firmware is unchanged. The parts are laid out in Rev C's frame and the whole board is then moved 7 mm
right, so the finished board runs x 0.3-65.7, y 0-56, from the top edge (USB-A, micro-USB, 24 VAC) to the bottom
edge (air sensors, 1-wire). The 7 mm strip on the left carries the six status LEDs, which face the case's cap.
"""
import argparse, importlib.util, math, os, sys
import pcbnew
from pcbnew import FromMM, VECTOR2I

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gen_boards", os.path.join(HERE, "gen-boards.py"))
gb = importlib.util.module_from_spec(spec); spec.loader.exec_module(gb)
mm = gb.mm

W, L = 57.0, 56.0      # coordinate frame; the box centre is x 28.5, y 28
X0, X1 = -6.7, 58.7    # board edges in Rev C's frame: 7 mm more on the left for the LEDs, 2 on the right for U1
SHIFT = 7.0            # the finished board is moved this far right, so its left edge is x 0.3
CX, CY = W / 2, L / 2  # the Pico's centre line, Rev C's
# where the cap's four pins press the board on to the tray's posts; nothing else holds it
PINS = [(-4.6, 14.5), (55.6, 7.6), (-4.6, 44.1), (42.5, 42.0)]
PIN_R = 1.2
R_0805 = ("Resistor_SMD", "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder")
C_0805 = ("Capacitor_SMD", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder")

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(HERE, "ahpd-board"))
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
# 0.5 mm applies to the rectified 24 VAC side only; GND, +5V and 3V3 are the low side, beside 0.5 mm pitch pins
# a project file left from an earlier run would keep its net class patterns
if os.path.exists(os.path.join(args.out, "ahpd-board.kicad_pro")):
    os.remove(os.path.join(args.out, "ahpd-board.kicad_pro"))
B = gb.Board(os.path.join(args.out, "ahpd-board.kicad_pcb"), W, L, power_clearance=0.5, power_nets=("VS", "COM", "AC*"))
ds = B.board.GetDesignSettings(); ds.m_MinClearance = FromMM(0.15)
ds.m_TentViasFront = True; ds.m_TentViasBack = True    # the Pico sits flat on the front; vias must not touch its test pads
supply = pcbnew.NETCLASS("Supply"); supply.SetClearance(FromMM(0.2)); supply.SetTrackWidth(FromMM(0.4))
supply.SetViaDiameter(FromMM(0.8)); supply.SetViaDrill(FromMM(0.4)); ds.m_NetSettings.SetNetclass("Supply", supply)
for pat in ("GND", "+5V", "3V3", "VSYS", "VBUS"):
    ds.m_NetSettings.SetNetclassPatternAssignment(pat, "Supply")

# --- outline: a plain rectangle, no holes
for d in [d for d in B.board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]:
    B.board.Remove(d)
pts = [(X0, 0), (X1, 0), (X1, L), (X0, L)]
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
    elif pcbnew.ToMM(r.GetBottom()) < 4:   # TP2 and TP3's own: this board joins them
        z.SetDoNotAllowPads(False); z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False)
B.rect_keepout(21.4, 43.8, 35.6, L, layers=("F.Cu", "B.Cu"), name="antenna", pads=False, footprints=False, tracks=True, vias=True, pour=True)
# plated holes under the Pico's TP2 (D-) and TP3 (D+), Rev C's: filled with solder from the back on a hand build,
# and on an assembled board the paste on each pad joins it in the oven and the hole shows the joint
for num, x in (("TP2", 0.8), ("TP3", -0.8)):
    p = gb._pad(pico, num, CX + x, PY - 24.3, 1.1, 0.7)

# --- top edge: USB-A jack, HRO U-A-24SS-W-1, surface mount (LCSC C283549; pads from its drawing and JLCPCB's
# footprint). Seen from above with the opening toward the top edge, pin 1 is on the right. Two plastic pegs
# locate it in unplated holes; the shell solders to a pad each side.
JX = 7.7               # 1.1 mm between the shell's pad and the Pico's pads
JY = -2.8              # the jack's face stands 2.8 past the board edge, flush with the outside of the tray's wall,
                       # which keeps its pads clear of U5 below them
JO = JY + 13.3         # the footprint's origin: the face is 13.3 from it
j = pcbnew.FOOTPRINT(B.board); j.SetFPID(pcbnew.LIB_ID("pivac", "USB_A_HRO_U-A-24SS-W-1"))
j.SetAttributes(pcbnew.FP_SMD)
for n, x in ((1, 3.5), (2, 1.0), (3, -1.0), (4, -3.5)):
    gb._smd(j, n, x, 1.65, 1.2, 2.8)
for x in (-7.3, 7.3):
    gb._smd(j, "S", x, -1.65, 2.2, 5.0)
for x in (-2.5, 2.5):
    gb._peg(j, x, -3.1, 1.3)
gb._fp_rect(j, -6.6, -13.3, 6.6, 0.4, pcbnew.F_SilkS, 0.12)
gb._fp_rect(j, -8.45, -13.55, 8.45, 3.3, pcbnew.F_CrtYd, 0.05)
B.place("J4", j, JX, JO, 0, value="U-A-24SS-W-1")

# --- top edge: 24 VAC, Phoenix MC 1,5/2-G-3,81 footprint, entry toward the edge
MX = 47.5
mc = B.lib("J1", "Connector_Phoenix_MC", "PhoenixContact_MC_1,5_2-G-3.81_1x02_P3.81mm_Horizontal", MX + 1.905, 8.5, 180, value="3.81 mm 2-pin 24VAC")
B.text("24 VAC", 52.95, 6.7, size=0.8, bold=True, rot=90)

# --- bottom edge: PTSM surface-mount headers, entry toward the edge. The two air sensors take a 2-pin header each
# on the left, beside the ADS1115; the 1-wire pair shares the 3-pin header on the right
for ref, n, x, lab in (("J3", 2, -0.75, "SUP"), ("J5", 2, 10.85, "RET"), ("J2", 3, 49.5, "1-WIRE")):
    fp = gb.ptsm_hh_smd(B, n)
    B.place(ref, fp, x, L, 180, value=f"PTSM 0,5/{n}-HH-2,5-SMD")
    B.text(lab, x, L - 12.1 if n == 3 else L - 10.7, size=0.8, bold=True)     # J2's pin letters stand between

# --- power
B.lib("F1", "Fuse", "Fuse_1812_4532Metric_Pad1.30x3.40mm_HandSolder", 48.6, 14.2, 0, value="PTC 0.2A")
B.lib("D2", "Diode_SMD", "D_SMA", 54.8, 13.0, 90, value="SMAJ43CA")
u1 = gb.sip8_converter(B, pin5=True)      # pin 8 keeps its hole and no net: it is an internal node on the URB
B.place("U1", u1, 0, 0, 90, value="URB4805S-3WR3")
bb = u1.GetCourtyard(pcbnew.F_CrtYd).BBox()
dx, dy = 40.25 - pcbnew.ToMM(bb.GetLeft()), 16.8 - pcbnew.ToMM(bb.GetTop())
u1.SetPosition(mm(dx, dy))
for g in u1.GraphicalItems():
    if g.GetLayer() == pcbnew.F_CrtYd:      # D1 and C1 stand beside the body; the URB's ends at x 51.1, the TMR 3's at 49.7
        g.SetLayer(pcbnew.F_Fab)
u1.Reference().SetPosition(mm(47.6, 40.15)); u1.Reference().SetTextAngleDegrees(0)
B.lib("C1", "Capacitor_SMD", "CP_Elec_6.3x7.7", 55.1, 29.6, 90, value="47u 50V")
B.lib("D1", "Diode_SMD", "D_SMA", 54.9, 37.5, 0, value="M7")
B.lib("C2", "Capacitor_SMD", "C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", 55.4, 41.9, 0, value="100u 6.3V")

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

# --- status LEDs: top-view 0805s on the front in one column down the left strip, under six bores in the cap.
# Each lies across the board with its cathode outboard on a ground bus and its resistor inboard.
LX = -3.8
LED = (("LED1", 21.0, "PWR", "R5", "3V3", None, "green"), ("LED2", 25.0, "FAN", "R6", "L_FAN", 16, "yellow"),
       ("LED3", 29.0, "Y1", "R7", "L_Y1", 11, "blue"), ("LED4", 33.0, "Y2", "R8", "L_Y2", 12, "blue"),
       ("LED5", 37.0, "W1", "R9", "L_W1", 14, "red"), ("LED6", 41.0, "W2", "R10", "L_W2", 15, "red"))
for ref, y, lab, rref, net, pin, part in LED:
    fp = B.lib(ref, "LED_SMD", "LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder", LX, y, 0, value="0805 " + part)
    if B.pad_xy(ref, 1)[0] > LX:       # the cathode goes outboard
        fp.SetOrientationDegrees(180)
    r = B.lib(rref, *R_0805, LX + 3.1, y, 90, value="220R")
    B.text(lab, LX + 1.2, y - 1.6, size=0.6, bold=True)        # the LED's name and its call, in the gap above it

# --- USB lockout (Rev C's circuit), on the front: a laptop on the micro-USB cuts U1 off the Pico and J4 off its data.
# Q1, R11 and R12 stand beside the Pico's VBUS and VSYS pins at the top right. U5 stands under the jack's pins with
# its HSD1 pair up toward them, C7 and R13 beside it; D+ and D- reach it from TP3 and TP2 on the back.
B.lib("Q1", "Package_TO_SOT_SMD", "SOT-23_Handsoldering", 42.7, 13.6, 90, value="DMG2305UX-7")
B.lib("R11", *R_0805, 41.25, 2.4, 90, value="100k")
B.lib("R12", *R_0805, 41.25, 8.2, 90, value="22k")      # 2.4 mm below R11, for the two references
UX, UY = 6.2, 17.1
u5 = B.lib("U5", "Package_SO", "MSOP-10_3x3mm_P0.5mm", UX, UY, 90, value="FSUSB42MUX")
for rot in (90, 270):       # pins 6-10 along the top, D+ (7) left of D- (6), under the jack's pins 3 and 2
    u5.SetOrientationDegrees(rot)
    if B.pad_xy("U5", 1)[1] > UY and B.pad_xy("U5", 3)[0] < B.pad_xy("U5", 4)[0]:
        break
else:
    raise SystemExit("no orientation of U5 puts pins 6-10 at the top with D+ left of D-")
c7 = B.lib("C7", *C_0805, 2.4, UY + 1.7, 90, value="100n")
if B.pad_xy("C7", 1)[1] < UY + 1.7:        # pad 1 (3V3) at the bottom, toward U5's pin 1
    c7.SetOrientationDegrees(270)
r13 = B.lib("R13", *R_0805, 2.3, B.pad_xy("U5", 10)[1], 0, value="33k")
if B.pad_xy("R13", 1)[0] < 2.3:        # pad 1 (OE) toward U5
    r13.SetOrientationDegrees(180)

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
nets("J3", (1, "SUP"), (2, "GND")); nets("J5", (1, "RET"), (2, "GND"))

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
# LEDs: anode to its resistor beside it; every cathode on one ground bus along the outboard pads, which runs up
# the strip to the GND test loop and on to the jack's shield leg
for ref, y, lab, rref, net, pin, part in LED:
    k, a_ = B.pad_xy(ref, 1), B.pad_xy(ref, 2)
    assert k[0] < a_[0], "the cathode is outboard"
    r1 = B.pad_xy(rref, 1)
    path("A_" + ref, "F.Cu", a_, (a_[0] + 0.9, a_[1]), r1, width=0.25)
kx = B.pad_xy("LED1", 1)[0]
TP3 = (-3.2, 6.0)
path("GND", "F.Cu", (kx, LED[-1][1]), (kx, 7.6), TP3, width=0.4)
path("GND", "F.Cu", TP3, (-0.4, 8.8), (JX - 7.3, JO - 1.65), width=0.4)
c5g = B.pad_xy("C5", 2)
path("GND", "F.Cu", (2.54, 25.0), (2.54, 45.0), width=0.4)        # a ground spine on the front for the router, as on Rev C
path("GND", "F.Cu", (2.54, c5g[1]), c5g, width=0.4)
# U5's 0.5 mm pads, hand laid because Freerouting cannot leave pads closer than its clearance. HSD1+ and HSD1-
# (7, 6) go straight up into the jack's pins 3 and 2. OE (10) leaves sideways to R13. VCC (1) leaves by its outer
# end to C7; SEL and GND (2, 5) leave by their inner ends onto a ground strip under the body that reaches C7's
# other pad. D+ and D- (3, 4) get stubs downward, staggered, for the router to take to the back.
u = lambda n: B.pad_xy("U5", n)
j42, j43 = B.pad_xy("J4", 2), B.pad_xy("J4", 3)
ty = u(7)[1]
path("D+", "F.Cu", u(7), (u(7)[0], ty - 0.9), (j43[0], ty - 0.9 - (j43[0] - u(7)[0])), j43, width=0.2)
# D- passes under the foot of pad 3 and rises into pad 2
path("D-", "F.Cu", u(6), (u(6)[0], ty - 0.45), (u(6)[0] + 0.2, ty - 0.65), (j42[0] - 0.9, ty - 0.65), (j42[0], ty - 1.55), j42, width=0.2)
path("OE", "F.Cu", u(10), B.pad_xy("R13", 1), width=0.2)
c7v, c7g = B.pad_xy("C7", 1), B.pad_xy("C7", 2)
assert c7v[1] > c7g[1] and B.pad_xy("R13", 1)[0] > 2.3
path("3V3", "F.Cu", u(1), (u(1)[0], c7v[1] + 1.1), (c7v[0], c7v[1] + 1.1), c7v, width=0.25)
path("GND", "F.Cu", u(2), (u(2)[0], UY), width=0.25)
path("GND", "F.Cu", u(5), (u(5)[0], UY), (c7g[0] + 1.5, UY), c7g, width=0.25)
path("PD+", "F.Cu", u(3), (u(3)[0], u(3)[1] + 2.4), width=0.2)
path("PD-", "F.Cu", u(4), (u(4)[0], u(4)[1] + 1.3), (u(4)[0] + 0.8, u(4)[1] + 2.1), width=0.2)
path("ACR", "F.Cu", pj1, (47.8, 11.2), f1a)
path("ACF", "F.Cu", f1b, (52.6, d2a[1]), d2a)
path("ACF", "F.Cu", f1b, (49.4, 16.4)); via("ACF", 49.4, 16.4)
path("ACF", "B.Cu", (49.4, 16.4), (49.0, 17.0), (49.0, 26.0), (57.6, 34.6), (57.6, 35.6)); via("ACF", 57.6, 35.6)
path("ACF", "F.Cu", (57.6, 35.6), d1a)
path("VS", "F.Cu", u1v, (52.4, u1v[1]), d1v); path("VS", "F.Cu", (53.1, u1v[1]), (52.4, u1v[1])); path("VS", "F.Cu", (53.1, u1v[1]), c1v)
path("COM", "B.Cu", u1c, (45.9, u1c[1]), (47.5, 35.4), (47.5, 12.0), pj2)
path("COM", "B.Cu", (47.5, 12.0), (52.9, 12.0), (52.9, d2c[1])); via("COM", 52.9, d2c[1])
path("COM", "F.Cu", (52.9, d2c[1]), d2c)
path("COM", "F.Cu", c1c, (47.5, c1c[1])); via("COM", 47.5, c1c[1])

# no vias through the monogram and legends, front or back
for x0, y0, x1, y1, name in ((2.9, 37.5, 8.5, 43.1, "monogram"), (8.7, 37.7, 16.2, 39.5, "AirMaster"), (8.9, 39.5, 12.6, 41.2, "Rev D"),
                             (CX - 8.0, 48.8, CX + 8.0, 52.0, "licence"),
                             *((LX + 4.3, y - 0.6, LX + 6.3, y + 0.6, "LED legend") for y in (21, 25, 29, 33, 37, 41))):
    B.rect_keepout(x0, y0, x1, y1, layers=("F.Cu", "B.Cu"), name=name, pads=False, footprints=False, tracks=False, vias=True, pour=False)

# --- test holes, 1.0 mm plated, each named by its net. VS and COM stand on the 24 VAC side and GND on the left strip,
# named on both faces. Nine low-side nets stand in a column under the Pico, reached from the back, where the
# checkout table gives each one's reading: with the top off its base the back of a live board faces the bench.
def test_hole(ref, x, y, net):
    fp = pcbnew.FOOTPRINT(B.board); fp.SetFPID(pcbnew.LIB_ID("pivac", "TestHole"))
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    gb._pad(fp, 1, 0, 0, 1.8, 1.0)
    B.place(ref, fp, x, y, 0, value=net); fp.Reference().SetVisible(False)
    B.connect(ref, 1, net)
for ref, x, y, net, lx, ly in (("TP1", 49.8, 41.7, "VS", 47.9, 41.9), ("TP2", 56.2, 2.6, "COM", 56.2, 4.5),
                               ("TP3", TP3[0], TP3[1], "GND", TP3[0], TP3[1] - 2.0)):
    test_hole(ref, x, y, net)
    B.text(net, lx, ly, size=0.7, bold=True)
    B.text(net, x, y + 2.0, layer="B.SilkS", size=0.8, bold=True)
TX, TY0, TDY = CX - 5.5, 13.6, 2.7       # between the Pico's left pads and the keep-outs under its TP4 and TP6
# name, net, reading with the power off (ohms to GND unless it says otherwise), reading on 24 VAC
TABLE = (("GND", "GND", "", "reference"), ("3V3", "3V3", "no short", "3.3 V"), ("VSYS", "VSYS", "no short", "5 V"),
         ("VBUS", "VBUS", "no short", "0, laptop 5 V"), ("5V", "+5V", "no short", "5.1 V"), ("OE", "OE", "no short", "0, laptop 3 V"),
         ("SUP", "SUP", "20 k", "3.3 V open"), ("RET", "RET", "20 k", "3.3 V open"), ("1W", "OW", "no short", "3.3 V idle"),
         ("SDA", "SDA", "4k7 to 3V3", "3.3 V idle"), ("SCL", "SCL", "4k7 to 3V3", "3.3 V idle"))
XN, XOFF, XON = TX - 3.3, TX - 10.2, TX - 20.2    # seen from the back: hole, name, power off, power on
for i, (name, net, off, on) in enumerate(TABLE):
    y = TY0 + i * TDY
    test_hole("TP%d" % (i + 4), TX, y, net)
    B.text(name, XN, y, layer="B.SilkS", size=0.9, bold=True)
    if off:
        B.text(off, XOFF, y, layer="B.SilkS", size=0.8)
    B.text(on, XON, y, layer="B.SilkS", size=0.8)
B.text("POWER OFF", XOFF, TY0 - 4.3, layer="B.SilkS", size=0.8, bold=True)
B.text("to GND", XOFF, TY0 - 2.7, layer="B.SilkS", size=0.8)
B.text("ON 24 VAC", XON, TY0 - 4.3, layer="B.SilkS", size=0.8, bold=True)
B.text("to GND", XON, TY0 - 2.7, layer="B.SilkS", size=0.8)
yf = TY0 + len(TABLE) * TDY
B.text("VS to COM", XN - 2.0, yf, layer="B.SilkS", size=0.8, bold=True)
B.text("no short", XOFF - 2.6, yf, layer="B.SilkS", size=0.8); B.text("35 V", XON, yf, layer="B.SilkS", size=0.8)
B.text("COM to GND", XN - 2.4, yf + 1.5, layer="B.SilkS", size=0.8, bold=True)
B.text("open", XOFF - 2.6, yf + 1.5, layer="B.SilkS", size=0.8); B.text("open", XON, yf + 1.5, layer="B.SilkS", size=0.8)
for lab, num in (("D-", "TP2"), ("D+", "TP3")):
    x, y = B.pad_xy("U4", num)
    B.text(lab, x + (0.3 if lab == "D-" else -0.3), 0.95, layer="B.SilkS", size=0.5, bold=True)
path("VS", "F.Cu", (49.8, 41.7), (51.9, 39.6), (d1v[0] - 0.1, 38.4))
path("COM", "B.Cu", (56.2, 2.6), (52.9, 5.9), (52.9, 11.0))

# --- legends
gb.monogram(B, 5.7, 40.3, 0.6)         # smaller than Rev C's, to stand clear of the LED names
B.text("AirMaster", 8.9, 38.6, size=0.9, bold=True, left=True)
B.text("Rev D", 9.1, 40.4, size=0.7, left=True)
# the sensor legends leave no room beside the title block on the front, so the licence goes on the back, in the
# open pour under the Pico
B.text("\u00a9 2026 David Lewis", CX, 49.6, layer="B.SilkS", size=0.9)
B.text("CC BY-NC 4.0", CX, 51.2, layer="B.SilkS", size=0.9)
# reference designators the part bodies or their neighbours would cover
REFS = [("F1", 52.3, 14.2, 90, 0.8), ("D2", 57.7, 13.0, 90, 0.8), ("C1", 55.1, 24.2, 0, 0.8), ("D1", 56.9, 39.9, 0, 0.8), ("C2", 55.4, 44.0, 0, 0.8),
        ("R11", 41.57, 4.7, 0, 0.6), ("R12", 41.57, 5.9, 0, 0.6), ("Q1", 44.1, 11.8, 0, 0.6), ("J1", 47.5, 11.8, 0, 0.6),
        ("J2", 45.6, 43.9, 0, 0.7), ("J3", -3.7, 45.3, 0, 0.7), ("J5", 8.3, 45.3, 0, 0.7), ("J4", -3.8, 10.4, 0, 0.7),
        ("R13", -0.6, B.pad_xy("R13", 1)[1], 0, 0.7), ("C7", 0.8, 18.0, 0, 0.6), ("U5", 6.2, 20.75, 0, 0.7),
        ("R1", 2.2, 26.5, 90, 0.7), ("R3", 2.2, 30.5, 90, 0.7), ("C5", 2.2, 34.5, 90, 0.7),
        ("R2", 5.3, 26.5, 90, 0.7), ("R4", 5.3, 30.5, 90, 0.7), ("C6", 5.3, 34.5, 90, 0.7)]
for ref, y, lab, rref, net, pin, part in LED:
    REFS += [(ref, LX - 1.3, y - 1.6, 0, 0.6), (rref, 0.3, y + 0.15, 0, 0.6)]
for ref, x, y, angle, size in REFS:
    t = B.refs[ref].Reference(); t.SetPosition(mm(x, y)); t.SetTextAngleDegrees(angle)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size))); t.SetTextThickness(FromMM(size * 0.15))
    if ref in [l[3] for l in LED]:        # the LED resistors' references start beside their parts
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
for g in u1.GraphicalItems():           # U1's pin names would lie under its body
    if g.GetClass() == "PCB_TEXT" and g.GetLayer() == pcbnew.F_SilkS:
        g.SetLayer(pcbnew.F_Fab)
# R and C mark J1's pins, so the footprint's pin 1 triangle moves off the silkscreen
for g in mc.GraphicalItems():
    if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() != "PCB_TEXT" and pcbnew.ToMM(g.GetBoundingBox().GetTop()) > 10.2:
        g.SetLayer(pcbnew.F_Fab)
# U1's outline stops inside the body on the right, where D1 and C1 stand against it
for g in u1.GraphicalItems():
    if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() != "PCB_TEXT" and g.GetShape() == pcbnew.SHAPE_T_RECT:
        g.SetLayer(pcbnew.F_Fab)
for a, b in (((51.25, 16.99), (40.44, 16.99)), ((40.44, 16.99), (40.44, 39.2)), ((40.44, 39.2), (51.25, 39.2)), ((51.25, 16.99), (51.25, 39.2))):
    B.line(a[0], a[1], b[0], b[1], "F.SilkS", 0.12)
for lab, ref, pad in (("R", "J1", 1), ("C", "J1", 2)):
    x, y = B.pad_xy(ref, pad); B.text(lab, x, 11.8, size=0.6, bold=True)
for ref, labs in (("J2", "VDG"),):
    for i, lab in enumerate(labs, start=1):
        x, y = B.pad_xy(ref, i); B.text(lab, x, y - 2.5, size=0.7, bold=True)

# --- checks: each cap pin's clearance to the nearest pad, and every pair of front courtyards that overlap
T = pcbnew.ToMM
for px, py in PINS:
    worst = 99.0
    for fp in B.board.GetFootprints():
        for p in fp.Pads():
            if not p.GetNumber():
                continue
            bb = p.GetBoundingBox()
            ax = max(T(bb.GetLeft()) - px, px - T(bb.GetRight()), 0); ay = max(T(bb.GetTop()) - py, py - T(bb.GetBottom()), 0)
            d = math.hypot(ax, ay) - PIN_R
            if d < worst:
                worst, who = d, f"{fp.GetReference()}.{p.GetNumber()}"
    print(f"cap pin at {px + SHIFT:.1f}, {py:.1f}: {worst:.2f} mm to the nearest pad, {who}")
cys = []
for fp in B.board.GetFootprints():
    c = fp.GetCourtyard(pcbnew.F_CrtYd)
    if c.OutlineCount():
        r = c.BBox(); cys.append((fp.GetReference(), T(r.GetLeft()), T(r.GetRight()), T(r.GetTop()), T(r.GetBottom())))
for i, a in enumerate(cys):
    for b in cys[i + 1:]:
        ox, oy = min(a[2], b[2]) - max(a[1], b[1]), min(a[4], b[4]) - max(a[3], b[3])
        if ox > 0.01 and oy > 0.01:
            print(f"courtyards overlap: {a[0]} and {b[0]} by {ox:.2f} x {oy:.2f}")
assert not any(fp.IsFlipped() for fp in B.board.GetFootprints()), "a part is on the back"

# --- the silkscreen: every part's reference shows, and no text on either face touches a pad, a part's body,
# other text or the board's edge. A body is the footprint's fabrication outline.
def rect(bb, grow=0.0):
    return (T(bb.GetLeft()) - grow, T(bb.GetTop()) - grow, T(bb.GetRight()) + grow, T(bb.GetBottom()) + grow)
def meet(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > 0.01 and min(a[3], b[3]) - max(a[1], b[1]) > 0.01
BODY = {"J4": (JX - 6.6, JY, JX + 6.6, JO + 0.4)}
texts, pads, bodies = [], [], []
for fp in B.board.GetFootprints():
    ref = fp.GetReference()
    if not ref.startswith("TP"):
        assert fp.Reference().IsVisible(), ref + " has no visible reference"
        g = [i.GetBoundingBox() for i in fp.GraphicalItems() if i.GetLayer() == pcbnew.F_Fab and i.GetClass() == "PCB_SHAPE"]
        if ref in BODY:
            bodies.append((ref, BODY[ref]))
        elif g:
            r = [rect(i) for i in g]
            bodies.append((ref, (min(i[0] for i in r), min(i[1] for i in r), max(i[2] for i in r), max(i[3] for i in r))))
        texts.append((ref, fp.Reference().GetLayer(), rect(fp.Reference().GetBoundingBox())))
    for i in fp.GraphicalItems():
        if i.GetClass() == "PCB_TEXT" and i.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            texts.append((ref + " '" + i.GetText() + "'", i.GetLayer(), rect(i.GetBoundingBox())))
    for p in fp.Pads():
        through = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        pads.append((ref + "." + p.GetNumber(), through, rect(p.GetBoundingBox(), 0.1)))
for d in B.board.GetDrawings():
    if d.GetClass() == "PCB_TEXT" and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
        texts.append(("'" + d.GetText() + "'", d.GetLayer(), rect(d.GetBoundingBox())))
faults = []
for i, (name, layer, r) in enumerate(texts):
    front = layer == pcbnew.F_SilkS
    if r[0] < X0 + 0.3 or r[2] > X1 - 0.3 or r[1] < 0.3 or r[3] > L - 0.3:
        faults.append(name + " is at the board's edge")
    faults += ["%s is on pad %s" % (name, pn) for pn, through, pr in pads if (front or through) and meet(r, pr)]
    if front:
        faults += ["%s is on the body of %s" % (name, bn) for bn, br in bodies if meet(r, br)]
    faults += ["%s is on %s" % (name, n2) for n2, l2, r2 in texts[i + 1:] if l2 == layer and meet(r, r2)]
if os.environ.get("AHPD_DUMP"):
    want = os.environ["AHPD_DUMP"].split(",")
    for n, th, r in pads:
        if n.split(".")[0] in want: print("pad %-10s %6.2f %6.2f %6.2f %6.2f" % ((n,) + r))
    for n, r in bodies:
        if n in want: print("body %-9s %6.2f %6.2f %6.2f %6.2f" % ((n,) + r))
    for n, l, r in texts:
        if n.split(" ")[0].strip("'") in want or n.strip("'") in want: print("text %-9s %6.2f %6.2f %6.2f %6.2f" % ((n,) + r))
for f in faults:
    print("silkscreen:", f)
print("silkscreen: %d texts, %d faults" % (len(texts), len(faults)))
if not os.environ.get("AHPD_DRAFT"):
    assert not faults, "the silkscreen has %d faults" % len(faults)
# the whole board moves right, so its left edge is x 0.3
B.board.Move(VECTOR2I(FromMM(SHIFT), 0))
B.save()
# the nine test holes stand under the Pico by design, so KiCad's rule against a hole inside another part's
# courtyard is switched off in the project file
import json
pro = B.path[:-len("kicad_pcb")] + "kicad_pro"
if os.path.exists(pro):
    d = json.load(open(pro))
    d["board"]["design_settings"].setdefault("rule_severities", {})["pth_inside_courtyard"] = "ignore"
    json.dump(d, open(pro, "w"), indent=2)
print("wrote", B.path)
