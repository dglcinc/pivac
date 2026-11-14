#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""VRML models of the Hammond 1593K and the carrier's unmodelled parts, for gen-ah-pico.py's render.

Run with FreeCAD's command-line Python: freecadcmd ahp-box-models.py -- OUTDIR. Frame: origin at the
board's centre, x right, y toward the top panel, z 0 on the board's top face, millimetres; the
footprint scales by 1/2.54 into VRML units. The box is Hammond's own 1593K model, hardware/vendor/1593K.stp
(AHP_STEP overrides the path), turned so its cover posts stand 7.33 mm toward the top panel. Its board
plane is z -7 to -5.4, which sets z 0 here.
"""
import os, sys
import FreeCAD as App
import Part
V = App.Vector
OUT = os.environ.get("AHP_OUT") or sys.argv[-1]
os.makedirs(OUT, exist_ok=True)

BX, BY, BH = 66.22, 67.22, 28.0   # outside
FLOOR = 2.5
POST = 4.5                        # Hammond's model
ZB = -1.6 - POST - FLOOR          # outside bottom
ZS = ZB + BH / 2                  # the seam
IX, IY = 59.39, 58.66             # inside
PANEL_W, PANEL_H, PANEL_T = 60.0, 22.7, 1.7
PY0 = 29.4                        # inner face of an end panel

def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
def cyl(x, y, r, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0))
def rounded(x, y, z0, z1, r):
    b = box(-x / 2, x / 2, -y / 2, y / 2, z0, z1)
    return b.makeFillet(r, [e for e in b.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1])

def half(z0, z1, floor_low):
    """A shell from z0 to z1 with its floor at the low or high end and open ends for the panels."""
    outer = rounded(BX, BY, z0, z1, 5.0)
    if floor_low:
        cav = rounded(IX, IY, z0 + FLOOR, z1 + 1, 3.0)
    else:
        cav = rounded(IX, IY, z0 - 1, z1 - FLOOR, 3.0)
    s = outer.cut(cav)
    # end openings: outside the panel the end stands open between the walls
    for sgn in (-1, 1):
        y0, y1 = (PY0 - 0.1, BY) if sgn > 0 else (-BY, -PY0 + 0.1)
        zz = (z0 + FLOOR, z1 + 1) if floor_low else (z0 - 1, z1 - FLOOR)
        s = s.cut(box(-28.6, 28.6, y0, y1, zz[0], zz[1]))
    return s

COL = {"base": (.72, .73, .74), "lid": (.70, .71, .72), "panel": (.60, .61, .62), "black": (.07, .07, .08),
       "metal": (.50, .50, .52), "head": (.42, .42, .44), "plugW": (.80, .80, .78), "plugG": (.05, .42, .20),
       "plugB": (.10, .10, .11), "wireR": (.75, .10, .10), "wireK": (.05, .05, .05), "wireW": (.9, .9, .9),
       "wireB": (.10, .25, .75), "wireY": (.85, .75, .15), "cable": (.13, .13, .14),
       "ledG": (.15, .85, .25), "ledY": (.95, .80, .10), "ledB": (.15, .35, .95), "ledR": (.90, .12, .10)}

def wrl(name, parts):
    with open(os.path.join(OUT, name), "w") as f:
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

# --- the carrier's unmodelled parts
def ptsm(n, xc):
    a = (n - 1) * 2.5
    hw = a / 2 + 2.1
    b = box(xc - hw, xc + hw, -28, -20.5, 0, 5.0)
    return b.cut(box(xc - hw + 0.6, xc + hw - 0.6, -29, -23.5, 0.8, 4.2))
J2X, J3X = 9.6 - 28.5, 48.2 - 28.5
JX = 8.7 - 28.5
JY = 1.5                          # past the board edge
MX = 47.5 - 28.5
jack = box(JX - 7.25, JX + 7.25, 14 + JY, 28 + JY, 0, 6.9).cut(box(JX - 6.25, JX + 6.25, 15.5 + JY, 29 + JY, 0.9, 6.0))
jack = jack.fuse(box(JX - 6.0, JX + 6.0, 17 + JY, 27.5 + JY, 3.0, 4.6))
parts = [(ptsm(3, J2X), "black"), (ptsm(4, J3X), "black"), (jack, "metal"),
         (box(40.5 - 28.5, 49.7 - 28.5, 28 - 39.14, 28 - 17.05, 0, 11.2), "black")]
for x, y in ((14, 14), (-14, -14), (14, -14)):
    parts.append((cyl(x, y, 2.8, 0, 1.9), "head"))
# status LEDs, Rev C: top-view 0805s on the board's back under the USB-A side's cover screw (board x 3.5),
# 2.0 x 1.25 x 0.8, lens toward the floor
LX = 3.5 - 28.5
LED = ((26.5, "ledG"), (30.5, "ledY"), (34.5, "ledB"), (38.5, "ledB"), (42.5, "ledR"), (46.5, "ledR"))
for y, col in LED:
    parts.append((box(LX - 1.0, LX + 1.0, 28 - y - 0.625, 28 - y + 0.625, -2.4, -1.6), col))
wrl("parts.wrl", parts)

# --- the box from Hammond's model: solids 0 base, 1 lid, 2 and 3 the flat end panels
src = Part.Shape(); src.read(os.environ.get("AHP_STEP") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor", "1593K.stp"))
def placed(k):
    t = src.Solids[k].copy(); t.rotate(V(0, 0, 0), V(0, 0, 1), 180); t.translate(V(0, 0, 5.4)); return t
base = placed(0)
for y, _ in LED:     # 3 mm holes drilled through the floor under each LED
    base = base.cut(Part.makeCylinder(1.5, 6, V(LX, 28 - y, ZB - 1), V(0, 0, 1)))
PZ0 = -5.95          # the panels' lower edge
def panel(k, notches):
    p = placed(k)
    for xc, hw, ztop in notches:
        p = p.cut(box(xc - hw, xc + hw, -40, 40, PZ0 - 1, ztop))
    return p
kt = 2 if placed(2).BoundBox.YMin > 0 else 3
top = panel(kt, ((JX, 8.0, 7.6), (0, 6.2, 5.0), (MX, 6.0, 10.5)))
bot = panel(5 - kt, ((J2X, 7.4, 6.0), (J3X, 8.6, 6.0)))
wrl("base.wrl", [(base, "base"), (top, "panel"), (bot, "panel")])
wrl("lid.wrl", [(placed(1), "lid")])

# --- plugs and leads, closed view
def wire(x, y0, y1, z, col, r=0.75):
    return (Part.makeCylinder(r, abs(y1 - y0), V(x, min(y0, y1), z), V(0, 1, 0)), col)
pl = []
for xc, n, cols in ((J2X, 3, ("wireR", "wireY", "wireK")), (J3X, 4, ("wireW", "wireK", "wireB", "wireK"))):
    a = (n - 1) * 2.5
    hw = a / 2 + 2.0
    pl.append((box(xc - hw, xc + hw, -39.4, -23.6, 0.9, 4.1).fuse(box(xc - hw, xc + hw, -39.4, -28.5, 0, 5.2)), "plugW"))
    for i, c in enumerate(cols):
        pl.append(wire(xc - a / 2 + i * 2.5, -62, -39, 2.6, c, 0.7))
# 24 VAC: the 3.81 mm screw plug
xc = MX
pl.append((box(xc - 5.0, xc + 5.0, 27.5, 41, 0.4, 9.5), "plugG"))
for dx, c in ((1.905, "wireR"), (-1.905, "wireK")):
    pl.append((cyl(xc + dx, 36.5, 1.3, 9.5, 10.0), "metal"))
    pl.append(wire(xc + dx, 40.5, 64, 4.0, c, 0.95))
# USB-A plug and cable
pl.append((box(JX - 6.0, JX + 6.0, 17 + JY, 30.5 + JY, 1.0, 5.5), "metal"))
pl.append((box(JX - 8.0, JX + 8.0, 30.5 + JY, 54, -0.75, 7.25), "cable"))
pl.append(wire(JX, 54, 76, 3.25, "cable", 2.3))
wrl("plugs.wrl", pl)
print("wrote", OUT)
