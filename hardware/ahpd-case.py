#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""The printed case of the AirMaster carrier Rev D: a base and a top (docs/airmaster/rev-d/air-handler-pico-revd-plan.md).

Run with FreeCAD's command-line Python:  freecadcmd ahpd-case.py
Writes ahpd-case/airmaster-base.{step,stl} and ahpd-case/airmaster-top.{step,stl} beside this script, the review
drawing docs/airmaster/rev-d/air-handler-pico-revd-case.svg, and with AHPD_MODELS set, the VRML models of ahpd-render.sh in that
folder (tray.wrl, cap.wrl, parts.wrl, plugs.wrl).

The base is a plate that stays on the air handler, on VHB tape or two #6 screws through its slots. The top is the
shell and it carries the board: the board presses in from below, parts toward the face, against four pins under the
face, and three snap hooks in the walls catch its back. Every connector stands in a notch that is open toward the
base. Two latch tabs in the top's side walls, at opposite corners, catch a lug each on the base; squeezing the two
tabs releases the top, which comes away with the board and its plugs. A low rim on the base stands inside the
top's walls and locates it. Each of the six status LEDs stands under a shaft in a block on the left of the top,
and a clear light pipe, Bivar PLPC2-500, drops into each from inside and is trapped between a lip at the face and
the board. One pocket
in the face takes that label, which names the LEDs down its left edge and each port at its notch.

Positions are given in the board's own frame, as gen-ah-pico-d.py leaves it (x 0.3-65.7, y 0-56 from the top
edge, millimetres), z 0 on the board's top face and positive toward the top's face.
"""
import math, os, sys
import FreeCAD as App
import Part
import MeshPart
import TechDraw
V = App.Vector
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ahpd-case")
DOCS = os.path.join(HERE, "..", "docs", "airmaster", "rev-d")
MODELS = os.environ.get("AHPD_MODELS")
FONT = os.environ.get("AHPD_FONT", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")
os.makedirs(OUT, exist_ok=True)

BX0, BX1, BL, BT = 0.3, 65.7, 56.0, 1.6           # the board
OX, OY = (BX0 + BX1) / 2, BL / 2
X = lambda x: x - OX
Y = lambda y: OY - y
HX, HY = (BX1 - BX0) / 2, BL / 2                  # board half sizes

GAP = 0.4              # board to wall, each side: Xometry holds SLS nylon to +/-0.38 mm
WALL = 2.4
FLOOR = 2.0            # the base plate
STAND = 3.5            # under the board: a #6 pan head stands 2.4, the through-hole leads 2.6
ROOM = 13.0            # above the board: U1 is 12.0 tall
TOP = 2.0
IX, IY = HX + GAP, HY + GAP                       # cavity half sizes
EX, EY = IX + WALL, IY + WALL                     # outside half sizes
ZS = -BT - STAND                                  # the seam: the top's walls stand on the base plate here
ZB = ZS - FLOOR                                   # outside bottom
ZT = ROOM + TOP                                   # outside top
FIT = 0.3
WL, WR = BX0 - GAP, BX1 + GAP                     # inside faces of the side walls, board frame
WT, WB = -GAP, BL + GAP                           # inside faces of the power-end and sensor-end walls

# the four pins under the top's face that the hooks hold the board against
PINS = [(2.4, 14.5), (62.6, 7.6), (2.4, 44.1), (49.5, 42.0)]
# notches in the top's end walls, open toward the base: centre x, half width, height above the board
TOP_NOTCH = (("USB", 14.7, 7.0, 7.5), ("PGM", 35.5, 6.3, 5.6), ("24 VAC", 54.5, 5.3, 10.6))
BOT_NOTCH = (("SUP", 6.25, 3.9, 6.0), ("RET", 17.85, 3.9, 6.0), ("1-WIRE", 56.5, 5.1, 6.0))
# the light pipe over each LED: Bivar PLPC2-500, clear polycarbonate (drawing PLPC2-XXX rev F). Body 1.9 mm with ribs
# to 2.1, lens 2.3 mm on a head 0.3 deep, 12.7 mm overall. It is made to press into a drilled 2.0 mm hole; here it
# is dropped loose into a printed hole instead, head toward the LED, and trapped between a lip at the face and the
# board, so the case needs no drilling, no press fit and no glue.
PIPE_L, PIPE_D, PIPE_LENS = 12.7, 1.9, 2.3
PIPE_HOLE = 2.7        # printed: clears the 2.3 mm head at the looser limit of SLS, +/-0.3
LIP, APERTURE = 0.8, 1.5                          # the lip at the face that stops the pipe, and the window through it;
                                                  # 0.8 mm is the printer's least wall
FLOAT = 0.4            # the pipe's play between the lip and its LED; 0.1 to 0.7 over the print's tolerance
SEAT = ZT - (0.9 + FLOAT + PIPE_L + LIP)          # the lip's top sits this far under the face, in a sunk strip
GRIP = 3.0             # the guide hole's depth under the lip; below it the shaft is wide
LED_X = 3.2
LED = ((21.0, "PWR", "ledG"), (25.0, "FAN", "ledY"), (29.0, "Y1", "ledB"), (33.0, "Y2", "ledB"),
       (37.0, "W1", "ledR"), (41.0, "W2", "ledR"))
CELL = (1.0, 5.4, 1.2)                            # the wide shaft over each LED: x0, x1, half length along y
LABEL = (7.6, 65.0, -1.1, 57.1, 0.3)              # the label's pocket in the face: x0, x1, y0, y1, depth
# snap hooks for the board: a tab cut from the wall by two slits, hanging from ROOT, with a barb under the board.
# side ("L", "R" or "S", the sensor end), then the tab's extent along its wall
HOOKS = (("L", 3.5, 8.5), ("R", 30.0, 35.0), ("S", 33.0, 39.0))
# latch tabs for the base, at opposite corners: side, extent
LATCH = (("L", 48.9, 54.4), ("R", 2.5, 8.0))
SLIT = 0.8
TAB_T = 1.4            # a tab's thickness
HOOK_ROOT, LATCH_ROOT = 11.0, 9.0
CATCH = 0.8            # how far a hook's barb stands under the board
BARB = 0.9             # how far a latch's barb stands out of the wall
LUG_GAP, LUG_T, LUG_TOP, LIP_Z = 1.2, 2.0, -1.5, -2.7
RIM_T, RIM_TOP = 1.4, -2.0
SCREWS = ((12.0, 28.0, "x"), (44.0, 28.0, "y"))   # slots for #6 pan heads, 4.0 wide and 10 long
SLOT_W, SLOT_L = 4.0, 10.0


def box(x0, x1, y0, y1, z0, z1):
    """A box given in the board's frame."""
    xa, xb = sorted((X(x0), X(x1))); ya, yb = sorted((Y(y0), Y(y1)))
    return Part.makeBox(xb - xa, yb - ya, z1 - z0, V(xa, ya, z0))
def cyl(x, y, r, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(X(x), Y(y), z0))
def cone(x, y, r0, r1, z0, z1):
    return Part.makeCone(r0, r1, z1 - z0, V(X(x), Y(y), z0))
def rounded(hx, hy, z0, z1, r):
    b = Part.makeBox(2 * hx, 2 * hy, z1 - z0, V(-hx, -hy, z0))
    return b.makeFillet(r, [e for e in b.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1])
def prism(pts, y0, y1):
    """A profile in board x and z, extruded along board y."""
    ya, yb = sorted((Y(y0), Y(y1)))
    w = Part.makePolygon([V(X(x), ya, z) for x, z in pts] + [V(X(pts[0][0]), ya, pts[0][1])])
    return Part.Face(w).extrude(V(0, yb - ya, 0))
def prism_x(pts, x0, x1):
    """A profile in board y and z, extruded along board x."""
    w = Part.makePolygon([V(X(x0), Y(y), z) for y, z in pts] + [V(X(x0), Y(pts[0][0]), pts[0][1])])
    return Part.Face(w).extrude(V(x1 - x0, 0, 0))
def legend(s, size, x, y, z, depth=1.0, left=False):
    """Text cut down from height z, centred on board position x, y, or starting at x."""
    faces = [Part.makeFace(ch, "Part::FaceMakerBullseye") for ch in
             Part.makeWireString(s, os.path.dirname(FONT) + "/", os.path.basename(FONT), size, 0) if ch]
    t = Part.makeCompound(faces)
    b = t.BoundBox
    t.translate(V(-b.XMin if left else -b.Center.x, -b.Center.y, 0))
    t.translate(V(X(x), Y(y), z - depth))
    return t.extrude(V(0, 0, depth + 0.1))

# --- top
top = rounded(EX, EY, ZS, ZT, 3.0).cut(rounded(IX, IY, ZS - 1, ROOM, 1.0))
cx0, cx1, ch = CELL
# the LED column: a block from the left wall to the face with a shaft over each LED. With the top face down on the
# bench a pipe drops into each shaft, head up; pressing the board in traps all six. Each pipe then stands between a
# 0.8 mm lip at the face, with a 1.5 mm window through it, and its LED, with 0.4 mm of play. A strip of the face is
# sunk to put the lip at that height. With no pipe fitted the same shaft is an open hole over the LED.
tr0, tr1 = LED[0][0] - 2.5, LED[-1][0] + 2.5
top = top.fuse(box(WL - 0.1, cx1 + 1.0, tr0, tr1, 1.2, ROOM + 0.1))      # 1.0 mm between a shaft and the room beside it
for y in [LED[0][0] - 2.0] + [l[0] + 2.0 for l in LED]:                             # the walls reach down between the LEDs
    top = top.fuse(box(WL - 0.1, cx1, y - 0.8, y + 0.8, 0.3, 1.3))
top = top.cut(box(cx0 - 0.4, cx1 + 0.4, tr0 + 0.3, tr1 - 0.3, ZT - SEAT, ZT + 1))  # the sunk strip
ZL = ZT - SEAT - LIP                              # the lip's underside, which the pipe meets
for y, name, col in LED:
    top = top.cut(box(cx0, cx1, y - ch, y + ch, 0, ZL - GRIP))
    top = top.cut(cyl(LED_X, y, PIPE_HOLE / 2, ZL - GRIP - 0.1, ZL))
    top = top.cut(cyl(LED_X, y, APERTURE / 2, ZL - 0.1, ZT + 1))
PIPES = [(cone(LED_X, y, PIPE_LENS / 2, PIPE_D / 2, ZL - PIPE_L, ZL - PIPE_L + 0.3)
          .fuse(cyl(LED_X, y, PIPE_D / 2, ZL - PIPE_L + 0.3, ZL)), col) for y, name, col in LED]
for x, y in PINS:      # the two pins beside the LED column are straight, so neither tapers into a shaft
    top = top.fuse(cyl(x, y, 1.2, 0.1, ROOM + 0.1) if x < 10 else cone(x, y, 1.2, 2.6, 0.1, ROOM + 0.1))
for notches, end in ((TOP_NOTCH, "T"), (BOT_NOTCH, "B")):
    for name, xc, hw, h in notches:
        y0, y1 = (WT + 0.1, WT - WALL - 1) if end == "T" else (WB - 0.1, WB + WALL + 1)
        top = top.cut(box(xc - hw, xc + hw, y0, y1, ZS - 1, h))
lx0, lx1, ly0, ly1, ld = LABEL
top = top.cut(box(lx0, lx1, ly0, ly1, ZT - ld, ZT + 1))

def wall_box(side, a0, a1, d0, d1, z0, z1):
    """A box in a wall: a0-a1 along the wall, d0-d1 outward from its inside face."""
    if side == "L":
        return box(WL - d1, WL - d0, a0, a1, z0, z1)
    if side == "R":
        return box(WR + d0, WR + d1, a0, a1, z0, z1)
    return box(a0, a1, WB + d0, WB + d1, z0, z1)
def wall_prism(side, pts, a0, a1):
    """A profile in distance outward from the wall's inside face and z, extruded along the wall."""
    if side == "L":
        return prism([(WL - d, z) for d, z in pts], a0, a1)
    if side == "R":
        return prism([(WR + d, z) for d, z in pts], a0, a1)
    return prism_x([(WB + d, z) for d, z in pts], a0, a1)
def tab(shape, side, a0, a1, root, thin_inside, foot):
    for s0, s1 in ((a0 - SLIT, a0), (a1, a1 + SLIT)):
        shape = shape.cut(wall_box(side, s0, s1, -0.05, WALL + 0.1, ZS - 1, root))
    d0, d1 = (-0.05, WALL - TAB_T) if thin_inside else (TAB_T, WALL + 0.1)
    shape = shape.cut(wall_box(side, a0 - 0.01, a1 + 0.01, d0, d1, ZS - 1, root))
    return shape.cut(wall_box(side, a0 - 0.01, a1 + 0.01, -0.05, WALL + 0.1, ZS - 1, ZS + foot))
zc = -BT - 0.15                                   # a hook's catch face, under the board's back
for side, a0, a1 in HOOKS:
    top = tab(top, side, a0, a1, HOOK_ROOT, False, 0.6)
    top = top.fuse(wall_prism(side, [(0.05, zc), (-GAP - CATCH, zc), (-GAP - CATCH, zc - 0.45), (0.05, zc - 2.05)], a0, a1))
for side, a0, a1 in LATCH:
    top = tab(top, side, a0, a1, LATCH_ROOT, True, 0.3)
    top = top.fuse(wall_prism(side, [(WALL - 0.05, -3.0), (WALL + BARB, -3.0), (WALL + BARB, -3.6), (WALL - 0.05, -4.8)], a0, a1))
    for z in (2.0, 3.7, 5.4):                     # three ribs mark where to press
        top = top.fuse(wall_box(side, a0 + 0.6, a1 - 0.6, WALL - 0.05, WALL + 0.5, z, z + 0.8))
top = top.removeSplitter()

# --- base
base = rounded(EX, EY, ZB, ZS, 3.0)
rim = rounded(IX - FIT, IY - FIT, ZS - 0.1, RIM_TOP, 0.8).cut(rounded(IX - FIT - RIM_T, IY - FIT - RIM_T, ZS - 1, 0, 0.4))
for side, a0, a1 in HOOKS + LATCH:                # the rim stops where a tab comes down or moves in
    rim = rim.cut(wall_box(side, a0 - 1.6, a1 + 1.6, -4.0, 0.5, ZS, 1))
base = base.fuse(rim)
for side, a0, a1 in LATCH:
    d = WALL + LUG_GAP
    base = base.fuse(wall_prism(side, [(WALL - 0.5, ZB), (d + LUG_T, ZB), (d + LUG_T, LUG_TOP), (WALL + FIT + 0.5, LUG_TOP),
                                       (WALL + FIT, LUG_TOP - 0.5), (WALL + FIT, LIP_Z), (d, LIP_Z), (d, ZS), (WALL - 0.5, ZS)],
                               a0 + 0.3, a1 - 0.3))
for x, y, way in SCREWS:
    dx, dy = ((SLOT_L - SLOT_W) / 2, 0) if way == "x" else (0, (SLOT_L - SLOT_W) / 2)
    slot = box(x - dx - (SLOT_W / 2 if dy else 0), x + dx + (SLOT_W / 2 if dy else 0),
               y - dy - (SLOT_W / 2 if dx else 0), y + dy + (SLOT_W / 2 if dx else 0), ZB - 1, ZS + 1)
    for sx, sy in ((-dx, -dy), (dx, dy)):
        slot = slot.fuse(cyl(x + sx, y + sy, SLOT_W / 2, ZB - 1, ZS + 1))
    base = base.cut(slot)
base = base.removeSplitter()

# --- fit: no part body may share volume with either half. x0, x1, y0, y1 in the board's frame, z0, z1 above its top
BODIES = {"board": (BX0, BX1, 0, BL, -BT, 0),
          "U1 leads": (50.0, 52.2, 18.0, 38.2, -BT - 2.6, -BT), "J1 leads": (51.5, 57.5, 7.4, 9.6, -BT - 2.6, -BT),
          "J4": (8.1, 21.3, -2.8, 10.9, 0, 7.1), "J4 tabs": (6.7, 22.7, 5.6, 10.7, 0, 1.0), "U4": (25.0, 46.0, 1.3, 52.3, 0, 3.7),
          "micro-USB": (31.6, 39.4, -0.2, 6.0, 1.0, 3.8), "J1": (49.45, 59.66, 0.0, 10.85, 0, 9.3),
          "U1": (48.39, 58.15, 17.0, 39.2, 0, 12.0), "C1": (58.8, 65.4, 26.3, 32.9, 0, 7.8),
          "D2": (60.0, 63.6, 9.5, 16.5, 0, 2.5), "F1": (52.4, 58.8, 12.2, 16.2, 0, 1.6),
          "D1 C2": (58.3, 65.4, 35.7, 43.1, 0, 2.5), "Q1 R11 R12": (47.2, 51.5, 0.5, 16.4, 0, 1.3),
          "R5-R10": (5.5, 7.4, 19.0, 43.0, 0, 0.7), "test holes": (29.0, 32.0, 12.0, 42.0, -BT - 0.1, -BT), "left parts": (7.5, 23.8, 13.0, 37.0, 0, 1.8),
          "J3": (2.9, 9.6, 48.5, 56.0, 0, 5.0), "J5": (14.5, 21.2, 48.5, 56.0, 0, 5.0), "J2": (51.9, 61.1, 48.5, 56.0, 0, 5.0),
          "J3 plug": (3.0, 9.5, 51.0, 68.0, 0, 5.2), "J5 plug": (14.6, 21.1, 51.0, 68.0, 0, 5.2),
          "J2 plug": (52.0, 61.0, 51.0, 68.0, 0, 5.2), "J1 plug": (49.5, 59.5, -13.0, 0.5, 0.4, 10.0),
          "USB-A plug": (8.7, 20.7, -5.3, 8.2, 1.0, 5.5), "micro-USB plug": (30.0, 41.0, -9.0, -0.4, -1.2, 5.4),
          "screw heads": (8.0, 16.0, 24.5, 31.5, ZS, ZS + 2.4), "screw head 2": (40.5, 47.5, 24.0, 32.0, ZS, ZS + 2.4)}
for y, name, col in LED:
    BODIES["LED " + name] = (1.3, 5.2, y - 0.7, y + 0.7, 0, 0.9)
board = box(BX0, BX1, 0, BL, -BT, 0)
for part, (x0, x1, y0, y1, z0, z1) in BODIES.items():
    b = box(x0, x1, y0, y1, z0, z1)
    for shape, name in ((top, "top"), (base, "base")):
        if part.startswith("screw") and name == "base":
            continue                                # the heads sit on the plate
        v = shape.common(b).Volume
        assert v < 0.01, "%s meets the %s: %.2f mm3" % (part, name, v)
    if part.startswith("screw") or "leads" in part:
        assert z1 <= -BT + 0.001 and (part.startswith("screw") and -BT - z1 > 1.0 or "leads" in part), part
for p, col in PIPES:      # drawn against its lip: clear of the top all round, and FLOAT above its LED
    assert top.common(p).Volume < 0.01, "a light pipe meets the top: %.2f mm3" % top.common(p).Volume
    assert abs(p.BoundBox.ZMin - 0.9 - FLOAT) < 0.01 and FLOAT - 0.3 > 0, "a light pipe has no play over its LED"
v = top.common(base).Volume
assert v < 0.01, "top meets base: %.2f mm3" % v
held = top.common(box(BX0, BX1, 0, BL, -BT - 2.5, -BT - 0.1)).Volume          # the hooks' barbs under the board
assert held > 3.0, "the hooks do not reach under the board"
lat = sum(base.common(wall_box(side, a0, a1, WALL, WALL + BARB, -3.0, -2.0)).Volume for side, a0, a1 in LATCH)
assert lat > 2.0, "the lugs do not stand over the latch barbs"
strain = lambda defl, length: 150 * TAB_T * defl / length ** 2
print("fit: %d bodies clear of top and base; hooks bend %.1f mm, strain %.1f %%; latches bend %.1f mm, strain %.1f %%"
      % (len(BODIES), CATCH + GAP, strain(CATCH + GAP, HOOK_ROOT + BT + 1), BARB, strain(BARB, LATCH_ROOT + 3.9)))

for shape, name in ((base, "airmaster-base"), (top, "airmaster-top")):
    assert shape.isValid() and len(shape.Solids) == 1, name
    shape.exportStep(os.path.join(OUT, name + ".step"))
    MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.03, AngularDeflection=0.35).write(os.path.join(OUT, name + ".stl"))
    b = shape.BoundBox
    print("%s: %.1f x %.1f x %.1f mm, %.1f cm3" % (name, b.XLength, b.YLength, b.ZLength, shape.Volume / 1000))
print("closed: %.1f x %.1f x %.1f mm, %.1f across the lugs" % (2 * EX, 2 * EY, ZT - ZB, 2 * (EX + LUG_GAP + LUG_T)))

# --- the review drawing: plans, elevations and three sections on one sheet
def view_matrix(u, v, w):
    return App.Matrix(u[0], u[1], u[2], 0, v[0], v[1], v[2], 0, w[0], w[1], w[2], 0, 0, 0, 0, 1)
VIEWS = {"plan": ((1, 0, 0), (0, 1, 0), (0, 0, 1)), "under": ((1, 0, 0), (0, -1, 0), (0, 0, -1)),
         "left": ((0, -1, 0), (0, 0, 1), (-1, 0, 0)), "power": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
         "sensor": ((1, 0, 0), (0, 0, 1), (0, -1, 0))}
def poly(edge):
    return [(p.x, p.y) for p in edge.discretize(Deflection=0.03)]
class View:
    """One view on the sheet: its lines and fills in sheet millimetres, y down."""
    def __init__(self, kind, title, note=""):
        self.m, self.title, self.note, self.items, self.calls = view_matrix(*VIEWS[kind]), title, note, [], []
        self.box = [1e9, 1e9, -1e9, -1e9]
    def _grow(self, pts):
        for x, y in pts:
            self.box = [min(self.box[0], x), min(self.box[1], y), max(self.box[2], x), max(self.box[3], y)]
    def outline(self, shape, stroke="#111", width=0.18):
        vis = TechDraw.project(shape.transformGeometry(self.m), V(0, 0, 1))[0]
        for e in vis.Edges:
            p = poly(e); self._grow(p); self.items.append(("line", p, stroke, width))
    def cut(self, shape, at, fill):
        """The faces a plane cuts through shape: at is the cut's position along the view axis, in view coordinates."""
        t = shape.transformGeometry(self.m)
        b = t.BoundBox
        sl = t.common(Part.makeBox(b.XLength + 2, b.YLength + 2, 0.04, V(b.XMin - 1, b.YMin - 1, at - 0.02)))
        for f in sl.Faces:
            if abs(f.normalAt(*f.Surface.parameter(f.CenterOfMass)).z) > 0.99 and f.CenterOfMass.z > at:
                loops = [[(p.x, p.y) for p in w.discretize(Deflection=0.03)] for w in f.Wires]
                for l in loops:
                    self._grow(l)
                self.items.append(("fill", loops, fill))
    def rect(self, x0, y0, x1, y1, fill="#fff", stroke="#111"):
        """A rectangle on the face, in the board's frame; drawn over the outline."""
        self.items.append(("rect", self.at(x0, y0, 0), self.at(x1, y1, 0), fill, stroke))
    def text(self, x, y, s, size, weight="normal", anchor="start", fill="#111", font=""):
        """Printed text on the face, in the board's frame; size is the font size in millimetres."""
        self.items.append(("text", self.at(x, y, 0), s, size, weight, anchor, fill, font))
    def tri(self, x, y, way):
        """A pointer on the label with its tip at x, y: up, down or left on the page."""
        d = {"up": ((-0.9, 1.3), (0.9, 1.3)), "down": ((-0.9, -1.3), (0.9, -1.3)), "left": ((1.3, -0.9), (1.3, 0.9))}[way]
        self.items.append(("fill", [[self.at(x, y, 0)] + [self.at(x + a, y + b, 0) for a, b in d]], "#111"))
    def at(self, x, y, z):
        """A board-frame point in this view's coordinates."""
        p = self.m.multVec(V(X(x), Y(y), z)); return p.x, p.y
    def call(self, x, y, z, text, dx, dy):
        self.calls.append((self.at(x, y, z), text, dx, dy))
    def svg(self, ox, oy, scale=1.0):
        """Placed with its box's top left at ox, oy."""
        x0, y0, x1, y1 = self.box
        T = lambda p: (ox + (p[0] - x0) * scale, oy + (y1 - p[1]) * scale)
        d = lambda pts: "M" + " L".join("%.2f %.2f" % T(p) for p in pts)
        out = ['<text x="%.1f" y="%.1f" font-size="3.4" font-weight="bold">%s</text>' % (ox, oy - 6.2, self.title),
               '<text x="%.1f" y="%.1f" font-size="2.5" fill="#444">%s</text>' % (ox, oy - 2.4, self.note)]
        for it in self.items:                    # fills, rectangles and text in the order given, then the lines
            if it[0] == "fill":
                out.append('<path d="%s" fill="%s" fill-rule="evenodd" stroke="#111" stroke-width="0.12"/>'
                           % (" ".join(d(l) + " Z" for l in it[1]), it[2]))
            if it[0] == "rect":
                a, b = T(it[1]), T(it[2])
                out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="%s" stroke-width="0.12"/>'
                           % (min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]), abs(b[1] - a[1]), it[3], it[4]))
            if it[0] == "raw":
                a = T(it[1])
                out.append('<g transform="translate(%.2f %.2f) scale(%.3f)">%s</g>' % (a[0], a[1], it[2] * scale, it[3]))
            if it[0] == "text":
                a = T(it[1])
                out.append('<text x="%.2f" y="%.2f" font-size="%.2f" font-weight="%s" text-anchor="%s" fill="%s"%s>%s</text>'
                           % (a[0], a[1], it[3] * scale, it[4], it[5], it[6], ' font-family="%s"' % it[7] if it[7] else "", it[2]))
        for it in self.items:
            if it[0] == "line":
                out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%.2f"/>' % (d(it[1]), it[2], it[3]))
        for p, text, dx, dy in self.calls:
            a = T(p); b = (a[0] + dx, a[1] + dy)
            out.append('<path d="M%.2f %.2f L%.2f %.2f" stroke="#c00" stroke-width="0.15" fill="none"/>' % (a + b))
            out.append('<circle cx="%.2f" cy="%.2f" r="0.45" fill="#c00"/>' % a)
            out.append('<text x="%.2f" y="%.2f" font-size="2.4" fill="#c00" text-anchor="%s">%s</text>'
                       % (b[0] + (0.8 if dx >= 0 else -0.8), b[1] + 0.8, "start" if dx >= 0 else "end", text))
        return "\n".join(out), (x1 - x0) * scale, (y1 - y0) * scale

PARTS = {k: v for k, v in BODIES.items() if "plug" not in k and not k.startswith("screw")}
def parts_shape(keys=None):
    return [box(*PARTS[k]) for k in (keys or PARTS) if k != "board"]
GREY, DARK, PCB, TAN = "#d9dadb", "#9fa3a8", "#3f8f5a", "#c9a36a"
LEDCOL = {"ledG": "#2fbf4f", "ledY": "#e8c020", "ledB": "#3060e0", "ledR": "#d83030"}
CLEAR = "#bfe6f5"
def section(v, at, clip=None):
    """Every body the plane cuts, each in its colour; clip is a box that bounds the view."""
    k = (lambda s: s.common(clip)) if clip else (lambda s: s)
    v.cut(k(top), at, GREY); v.cut(k(base), at, DARK); v.cut(k(board), at, PCB)
    for name, b in PARTS.items():
        if name != "board":
            col = TAN
            for y, led, c in LED:
                if name == "LED " + led:
                    col = LEDCOL[c]
            body = k(box(*b))
            if body.Volume > 0.001:
                v.cut(body, at, col)
    for p, col in PIPES:
        if not clip:
            v.cut(p, at, CLEAR)

closed = top.fuse(base)
v1 = View("plan", "1. Closed, from above, with its printed label", "Twice size. 71.0 x 61.6 mm, 77.4 across the lugs. Power end up. Sample values on the label.")
v1.outline(closed)
for y, name, col in LED:                          # where each LED shows through the skin
    c = v1.at(LED_X, y, 0)
    v1.items.append(("fill", [[(c[0] + APERTURE / 2 * math.cos(a * math.pi / 18), c[1] + APERTURE / 2 * math.sin(a * math.pi / 18)) for a in range(36)]], LEDCOL[col]))
# the printed label, as proposed: the AirMaster label of Arduino AirMaster/factory/label.py, laid out for this face.
# One rectangle: each port named at its notch with its pin letters at their true positions, the LED names down the
# left edge beside the windows, the title block, and the unit's setup details.
import random
lx0, lx1, ly0, ly1 = LABEL[0] + 0.3, LABEL[1] - 0.3, LABEL[2] + 0.3, LABEL[3] - 0.3
BLUE, LGREY = "#062d60", "#777777"
v1.rect(lx0, ly0, lx1, ly1)
for xc, name, sub in ((14.7, "UNICO", "USB"), (35.5, "PROG", "24 VAC off"), (54.5, "24 VAC", "")):
    v1.tri(xc, ly0 + 0.25, "up")
    v1.text(xc, ly0 + 4.6, name, 2.5, "bold", "middle")
    if sub:
        v1.text(xc, ly0 + 7.3, sub, 2.1, "normal", "middle")
for x, c in ((52.6, "C"), (56.4, "R")):           # J1's pins
    v1.text(x, ly0 + 7.3, c, 2.2, "normal", "middle")
for xc, name, anchor in ((8.6, "SUP", "start"), (17.85, "RET", "middle"), (56.5, "1-WIRE", "middle")):
    v1.tri(xc, ly1 - 0.25, "down")
    v1.text(lx0 + 0.7 if anchor == "start" else xc, ly1 - 5.0, name, 2.5, "bold", anchor)
for x, c in ((54.0, "G"), (56.5, "D"), (59.0, "V")):                   # J2's pins
    v1.text(x, ly1 - 2.6, c, 2.2, "normal", "middle")
v1.text(11.2, ly1 - 2.6, "NTC", 2.0, "normal", "middle"); v1.text(17.85, ly1 - 2.6, "NTC", 2.0, "normal", "middle")
for y, name, col in LED:
    v1.tri(lx0 + 0.3, y, "left")
    v1.text(lx0 + 2.4, y + 0.85, name, 2.3, "bold")
# title block: the board's monogram in the mask's blue, the name, the tag line under it
MONO = ('<circle r="4.775" fill="%s" stroke="%s" stroke-width="0.35"/><circle r="4.425" fill="none" stroke="#fff" stroke-width="0.35"/>'
        '<g fill="#fff"><path d="M -2.35 1.01 L -2.35 -2.51 A 0.24 0.24 0 0 1 -2.11 -2.75 L -1.55 -2.75 A 2 2 0 0 1 -1.55 1.25 L -2.11 1.25 '
        'A 0.24 0.24 0 0 1 -2.35 1.01 Z M -1.55 -1.95 L -1.55 0.45 A 1.2 1.2 0 0 0 -1.55 -1.95 Z" fill-rule="evenodd"/>'
        '<path d="M 0.8 -1.23 A 0.24 0.24 0 0 1 1.04 -1.47 L 1.36 -1.47 A 0.24 0.24 0 0 1 1.6 -1.23 L 1.6 1.59 A 0.14 0.14 0 0 0 1.74 1.73 '
        'L 2.793 1.73 A 0.24 0.24 0 0 1 3.033 1.97 L 3.033 2.29 A 0.24 0.24 0 0 1 2.793 2.53 L 1.04 2.53 A 0.24 0.24 0 0 1 0.8 2.29 Z"/></g>' % (BLUE, BLUE))
# the monogram just below the centre of the name's capitals, and the tag line under the name
MY = 15.6 - 0.716 * 5.6 / 2 + 0.5; MR = (4.775 + 0.175) * 0.95       # 0.5 mm below the capitals' centre, by eye
# the three keep their spacing and stand centred between the label's side margins. Widths are Helvetica's: the name
# is 4.612 em in bold and the tag line 13.837 em in regular
TW = max(6.0 + 4.612 * 5.6, 6.2 + 13.837 * 1.9) + MR      # from the ring's left edge to the longer line's end
TXO = (lx0 + lx1) / 2 - TW / 2 + MR                        # the monogram's centre
v1.items.append(("raw", v1.at(TXO, MY, 0), 0.95, MONO))
v1.text(TXO + 6.0, 15.6, "AirMaster", 5.6, "bold")
v1.text(TXO + 6.2, MY + MR - 0.5, "for the Unico SMART controller", 1.9)        # 0.5 mm above the ring's foot, nearer the name
# the setup block: one line of instruction, then the code beside three key and value groups of one style, the code
# as tall as the three groups together
GX, GP = 20.5, 6.3                             # the block's left edge and the groups' pitch
# the block runs from the instruction's capitals (4.8 above the first key's baseline) to the code's foot (2 * GP + 3.2
# below it), and stands midway between the ring's foot and the tops of the plug names along the bottom edge
CAP = 0.716                                    # Helvetica's capital height, as a share of the font size
GY = ((MY + MR) + (ly1 - 5.0 - CAP * 2.5)) / 2 - ((2 * GP + 3.2) - (3.3 + CAP * 2.1)) / 2
v1.text(GX, GY - 3.3, "To set up, scan the code or join the WiFi:", 2.1)
random.seed(6)
qn = 29                                        # a version 3 code, which the WiFi text needs; this pattern is a stand-in
qy = GY - 1.5; qs = (GY + 2 * GP + 3.2) - qy; qm = qs / qn
for r in range(qn):
    for c in range(qn):
        corner = (r < 7 and c < 7) or (r < 7 and c >= qn - 7) or (r >= qn - 7 and c < 7)
        rr, cc = (r if r < 7 else r - (qn - 7)), (c if c < 7 else c - (qn - 7))
        ring = corner and (min(rr, cc) == 0 or max(rr, cc) == 6 or (2 <= rr <= 4 and 2 <= cc <= 4))
        if ring or (not corner and random.random() < 0.48):
            v1.rect(GX + c * qm, qy + r * qm, GX + (c + 1) * qm, qy + (r + 1) * qm, "#111", "none")
tx = GX + qs + 2.2
for i, (key, value, font) in enumerate((("WiFi", "AirMaster-7K2Q", ""), ("Password", "h7k3m9px", "Menlo, Consolas, monospace"),
                                        ("Serial number", "AM-0006", ""))):
    v1.text(tx, GY + i * GP, key, 1.9, "normal", "start", LGREY)
    v1.text(tx, GY + i * GP + 3.2, value, 2.8, "bold", "start", "#111", font)
v1.text(36.0, ly1 - 0.9, "© 2026 David Lewis", 1.5, "normal", "middle", LGREY)
v1.call(LED_X, LED[0][0], ZT, "1.5 mm window over a light pipe, Bivar PLPC2-500", -8, -7)
v1.call(cx0 - 0.4, LED[3][0], ZT, "strip sunk %.1f mm" % SEAT, -8, 0)
v1.call(lx1 - 1.0, 40.0, ZT, "one printed label, 56.8 x 57.6, in a 0.3 mm pocket", 16, 6)
v1.call(WL - WALL, 51.5, 3.0, "latch tab: press", -8, -4)
v1.call(WR + WALL, 5.0, 3.0, "latch tab: press", 4, -9)
v1.call(WL - WALL - 2, 52.5, LUG_TOP, "lug on the base", -6, 7)
v2 = View("under", "2. Top from below, board out", "Three hooks hold the board against four pins.")
v2.outline(top)
for side, a0, a1 in HOOKS:
    p = {"L": (WL, (a0 + a1) / 2), "R": (WR, (a0 + a1) / 2), "S": ((a0 + a1) / 2, WB)}[side]
    v2.call(p[0], p[1], -BT - 1, "board hook", {"L": -7, "R": 6, "S": 4}[side], {"L": -7, "R": 9, "S": 8}[side])
for i, (x, y) in enumerate(PINS):
    v2.call(x, y, 0.1, "pin", 5 if x < 40 else -5, -4 if i % 2 else 4)
v2.call(LED_X, LED[2][0], 1.2, "pipe shafts", -9, 0)
v3 = View("plan", "3. Base, from above", "Tape under the plate, or two #6 pan heads in the slots.")
v3.outline(base)
v3.call(SCREWS[0][0], SCREWS[0][1], ZS, "slot 4 x 10", 3, 14)
v3.call(SCREWS[1][0], SCREWS[1][1], ZS, "slot 4 x 10", -3, 16)
v3.call(30.0, WT + 1.0, RIM_TOP, "rim, stands inside the top", 5, 9)
v3.call(WL - WALL - 2, 51.5, LUG_TOP, "lug", -4, 6)
v3.call(WR + WALL + 2, 5.0, LUG_TOP, "lug", 3, -6)
v4 = View("left", "4. Left side, closed", "22.1 mm high. Power end at the left.")
v4.outline(closed)
v4.call(51.5, 51.5, 3.5, "latch tab", 6, -16)
v4.call(51.5, 51.5, -2.0, "lug", 8, 8)
v4.call(6.0, 6.0, -3.0, "board hook", 5, 13)
v5 = View("power", "5. Power end, closed", "24 VAC, PGM and USB notches, left to right.")
v5.outline(closed)
v6 = View("sensor", "6. Sensor end, closed", "SUP, RET and 1-WIRE notches, left to right.")
v6.outline(closed)
v6.call(36.0, WB + WALL, -3.0, "board hook", 5, 13)
va = View("left", "A. Section along the LED column, x 3.2", "Twice size. A loose light pipe over each LED, trapped between the lip and the board.")
section(va, -X(LED_X))
va.call(LED_X, LED[1][0], ZT - SEAT - 6.0, "light pipe, 12.7 mm", 36, 6)
va.call(LED_X, LED[4][0], ZT - SEAT - LIP / 2, "0.8 mm lip, 1.5 mm window", 22, -9)
va.call(LED_X + 0.0, LED[5][0] + 1.1, 5.0, "wide shaft", 14, 10)
va.call(LED_X, LED[2][0], 1.1, "0.4 mm of play over the LED", 12, 16)
va.call(LED_X, LED[1][0], 0.5, "LED", -12, 16)
vb = View("sensor", "B. Section across at y 33, through LED Y2 and the right hook", "Twice size.")
section(vb, -Y(33.0))
vb.call(LED_X, 33.0, ZT - SEAT - 0.3, "lip and window", -6, 5)
vb.call(LED_X, 33.0, 7.0, "light pipe", -9, 2)
vb.call(15.0, 33.0, ZT - 0.2, "label pocket", 3, 9)
vb.call(35.0, 33.0, 3.0, "Pico W", 4, -8)
vb.call(53.0, 33.0, 8.0, "U1", 5, -5)
vb.call(WR - 0.6, 33.0, -BT - 0.6, "hook under the board", -8, 12)
vb.call(44.0, 33.0, ZS - 1.0, "screw slot", -6, 8)
vb.call(20.0, 33.0, ZS - 1.0, "base plate", -4, 8)
vc = View("sensor", "C. Section at y 51.5, the left latch", "Four times size.")
section(vc, -Y(51.5), box(WL - WALL - LUG_GAP - LUG_T - 1, WL + 9, 40, 56, ZB - 1, ZT + 1))
vc.call(WL - WALL - 0.4, 51.5, -3.6, "barb under the lug's lip", -6, 10)
vc.call(WL - WALL + 0.5, 51.5, 5.0, "tab: press here", -8, -4)
vc.call(WL - 1.2, 51.5, RIM_TOP - 0.5, "rim gap", 8, 6)

sheet, y = [], 14.0
for row in (((v1, 2), (vc, 4)), ((v2, 1), (v3, 1), (v4, 1)), ((v5, 1), (v6, 1)), ((va, 2), (vb, 2))):
    x, hmax = 48.0, 0
    for v, k in row:
        g, w, h = v.svg(x, y + 8, k)
        sheet.append(g); x += w + 44; hmax = max(hmax, h)
    y += hmax + 34
    width = max(x, locals().get("width", 0))
svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="100%%" height="100%%" viewBox="0 0 %.0f %.0f" '
       'font-family="Helvetica, Arial, sans-serif">\n<rect width="100%%" height="100%%" fill="#fff"/>\n'
       '<text x="48" y="9" font-size="4.6" font-weight="bold">AirMaster carrier Rev D: case, base and top</text>\n%s\n</svg>\n'
       % (width, y, "\n".join(sheet)))
open(os.path.join(DOCS, "air-handler-pico-revd-case.svg"), "w").write(svg)
print("wrote docs/airmaster/rev-d/air-handler-pico-revd-case.svg")

# --- models for the render
if MODELS:
    os.makedirs(MODELS, exist_ok=True)
    def cbox(x0, x1, y0, y1, z0, z1):
        return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
    def ccyl(x, y, r, z0, z1):
        return Part.makeCylinder(r, z1 - z0, V(x, y, z0))
    COL = {"tray": (.74, .75, .76), "cap": (.80, .81, .82), "black": (.07, .07, .08), "metal": (.50, .50, .52),
           "head": (.42, .42, .44), "plugW": (.80, .80, .78), "plugG": (.05, .42, .20), "wireR": (.75, .10, .10),
           "wireK": (.05, .05, .05), "wireW": (.9, .9, .9), "wireY": (.85, .75, .15), "cable": (.13, .13, .14),
           "ledG": (.15, .85, .25), "ledY": (.95, .80, .10), "ledB": (.15, .35, .95), "ledR": (.90, .12, .10)}
    def wrl(name, parts):
        with open(os.path.join(MODELS, name), "w") as f:
            f.write("#VRML V2.0 utf8\n")
            for shape, col in parts:
                c = COL[col]
                verts, tris = shape.tessellate(0.05)
                f.write("Shape {\n appearance Appearance { material Material { diffuseColor %.3f %.3f %.3f "
                        "ambientIntensity 0.3 %sspecularColor 0.2 0.2 0.2 shininess 0.2 } }\n" % (c + (("emissiveColor %.3f %.3f %.3f " % c) if col.startswith("led") else "",)))
                f.write(" geometry IndexedFaceSet { creaseAngle 0.5 coord Coordinate { point [\n")
                f.write(",".join("%.3f %.3f %.3f" % (v.x, v.y, v.z) for v in verts))
                f.write("] }\n coordIndex [\n")
                f.write(",".join("%d,%d,%d,-1" % t for t in tris))
                f.write("] }\n}\n")
    def ptsm(n, xc):
        hw = (n - 1) * 1.25 + 2.1
        b = cbox(X(xc) - hw, X(xc) + hw, -HY, -HY + 7.5, 0, 5.0)
        return b.cut(cbox(X(xc) - hw + 0.6, X(xc) + hw - 0.6, -HY - 1, -HY + 4.5, 0.8, 4.2))
    jx = X(14.7)
    jack = cbox(jx - 6.58, jx + 6.58, HY - 10.9, HY + 2.8, 0, 7.1).cut(cbox(jx - 6.1, jx + 6.1, HY - 9.4, HY + 3.8, 0.9, 6.2))
    jack = jack.fuse(cbox(jx - 5.8, jx + 5.8, HY - 8.2, HY + 2.3, 3.0, 4.6))
    parts = [(ptsm(2, 6.25), "black"), (ptsm(2, 17.85), "black"), (ptsm(3, 56.5), "black"), (jack, "metal"),
             (cbox(X(48.49), X(58.09), Y(39.1), Y(17.1), 0, 12.0), "black")]
    for y, name, col in LED:
        parts.append((cbox(X(LED_X) - 1.0, X(LED_X) + 1.0, Y(y) - 0.625, Y(y) + 0.625, 0, 0.8), col))
    wrl("parts.wrl", parts)
    wrl("tray.wrl", [(base, "tray")])
    lit = [(Part.makeCylinder(APERTURE / 2, 0.05, V(X(LED_X), Y(y), ZT - SEAT)), col) for y, name, col in LED]
    wrl("cap.wrl", [(top, "cap")] + lit)
    def wire(x, y0, y1, z, col, r=0.75):
        return (Part.makeCylinder(r, abs(y1 - y0), V(x, min(y0, y1), z), V(0, 1, 0)), col)
    pl = []
    for xc, n, cols in ((6.25, 2, ("wireW", "wireW")), (17.85, 2, ("wireW", "wireW")), (56.5, 3, ("wireR", "wireY", "wireK"))):
        a = (n - 1) * 2.5
        hw = a / 2 + 2.0
        pl.append((cbox(X(xc) - hw, X(xc) + hw, -HY - 11.4, -HY + 4.4, 0.9, 4.1).fuse(cbox(X(xc) - hw, X(xc) + hw, -HY - 11.4, -HY - 0.5, 0, 5.2)), "plugW"))
        for i, c in enumerate(cols):
            pl.append(wire(X(xc) - a / 2 + i * 2.5, -HY - 34, -HY - 11, 2.6, c, 0.7))
    xc = X(54.5)
    pl.append((cbox(xc - 5.0, xc + 5.0, HY - 0.5, HY + 13, 0.4, 9.5), "plugG"))
    for dx, c in ((1.905, "wireR"), (-1.905, "wireK")):
        pl.append((ccyl(xc + dx, HY + 8.5, 1.3, 9.5, 10.0), "metal"))
        pl.append(wire(xc + dx, HY + 12.5, HY + 36, 4.0, c, 0.95))
    pl.append((cbox(jx - 6.0, jx + 6.0, HY - 8.2, HY + 5.3, 1.0, 5.5), "metal"))
    pl.append((cbox(jx - 8.0, jx + 8.0, HY + 5.3, HY + 27.5, -0.75, 7.25), "cable"))
    pl.append(wire(jx, HY + 27, HY + 48, 3.25, "cable", 2.3))
    wrl("plugs.wrl", pl)
    print("wrote models to", MODELS)
