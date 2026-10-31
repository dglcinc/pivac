#!/usr/bin/env python3
"""VRML models of the Hammond 1593K and the carrier's unmodelled parts, for gen-ah-pico.py's render.

Run with FreeCAD's command-line Python: freecadcmd ahp-box-models.py -- OUTDIR. Frame: origin at the
board's centre, x right, y toward the top panel, z 0 on the board's top face, millimetres; the
footprint scales by 1/2.54 into VRML units. Box dimensions are Hammond's 1593K drawing; the height of
the board-mount posts is not on that drawing and is taken as 5 mm above the floor.
"""
import os, sys
import FreeCAD as App
import Part
V = App.Vector
OUT = os.environ.get("AHP_OUT") or sys.argv[-1]
os.makedirs(OUT, exist_ok=True)

BX, BY, BH = 66.22, 67.22, 28.0   # outside
FLOOR = 3.0
POST = 5.0                        # assumed
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
                    "ambientIntensity 0.3 specularColor 0.2 0.2 0.2 shininess 0.2 } }\n" % c)
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
J2X, J3X = 9.6 - 28.5, 48.5 - 28.5
JX = 8.0 - 28.5
MX = 47.5 - 28.5
jack = box(JX - 7.25, JX + 7.25, 14, 28, 0, 6.9).cut(box(JX - 6.25, JX + 6.25, 15.5, 29, 0.9, 6.0))
jack = jack.fuse(box(JX - 6.0, JX + 6.0, 17, 27.5, 3.0, 4.6))
parts = [(ptsm(3, J2X), "black"), (ptsm(4, J3X), "black"), (jack, "metal"),
         (box(40.5 - 28.5, 49.7 - 28.5, 28 - 39.14, 28 - 17.05, 0, 11.2), "black")]
for x, y in ((14, 14), (-14, -14), (14, -14)):
    parts.append((cyl(x, y, 2.8, 0, 1.9), "head"))
# status LEDs, 1206 on the board's back, under 3 mm holes in the base's floor
LED = ((33.5, 22.5, "ledG"), (33.5, 27.5, "ledY"), (28.5, 22.5, "ledB"), (28.5, 27.5, "ledB"), (23.5, 22.5, "ledR"), (23.5, 27.5, "ledR"))
for x, y, col in LED:
    parts.append((box(x - 28.5 - 0.8, x - 28.5 + 0.8, 28 - y - 1.6, 28 - y + 1.6, -2.7, -1.6), col))
wrl("parts.wrl", parts)

# --- base: floor, walls, posts, end panels with their notches
base = half(ZB, ZS, True)
for x, y in ((14, 14), (-14, 14), (-14, -14), (14, -14)):
    base = base.fuse(cyl(x, y, 2.5, ZB + FLOOR, -1.6))
for x in (-25, 25):
    base = base.fuse(cyl(x, 7.3, 2.86, ZB + FLOOR, ZS))
PZ0 = ZB + FLOOR - 0.35
def panel(y_inner, sgn, notches):
    p = box(-PANEL_W / 2, PANEL_W / 2, min(y_inner, y_inner + sgn * PANEL_T), max(y_inner, y_inner + sgn * PANEL_T), PZ0, PZ0 + PANEL_H)
    for xc, hw, ztop in notches:
        p = p.cut(box(xc - hw, xc + hw, y_inner - 3, y_inner + 3, PZ0 - 1, ztop))
    return p
top = panel(PY0, 1, ((JX, 8.0, 7.6), (0, 6.2, 5.0), (MX, 6.0, 10.5)))
bot = panel(-PY0, -1, ((J2X, 7.4, 6.0), (J3X, 8.6, 6.0)))
for x, y, _ in LED:
    base = base.cut(cyl(x - 28.5, 28 - y, 1.5, ZB - 1, ZB + FLOOR + 1))
wrl("base.wrl", [(base, "base"), (top, "panel"), (bot, "panel")])

# --- lid: shell, posts, the recessed inlay on top
lid = half(ZS, ZB + BH, False)
for x in (-25, 25):
    lid = lid.fuse(cyl(x, 7.3, 2.86, ZS, ZB + BH - FLOOR))
lid = lid.cut(box(-27.5, 27.5, -27.5, 27.5, ZB + BH - 1.0, ZB + BH + 1))
wrl("lid.wrl", [(lid, "lid")])

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
pl.append((box(JX - 6.0, JX + 6.0, 17, 30.5, 1.0, 5.5), "metal"))
pl.append((box(JX - 8.0, JX + 8.0, 30.5, 54, -0.75, 7.25), "cable"))
pl.append(wire(JX, 54, 76, 3.25, "cable", 2.3))
wrl("plugs.wrl", pl)
print("wrote", OUT)
