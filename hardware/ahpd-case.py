#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""The printed case of the AirMaster carrier Rev D: a tray and a cap (docs/air-handler-pico-revd-plan.md).

Run with FreeCAD's command-line Python:  freecadcmd ahpd-case.py
Writes ahpd-case/airmaster-tray.{step,stl} and ahpd-case/airmaster-cap.{step,stl} beside this script, and with
AHPD_MODELS set, the VRML models of ahpd-render.sh in that folder (tray.wrl, cap.wrl, parts.wrl, plugs.wrl).

The board lies in the tray on posts, located by the tray's walls, and four pins under the cap press it down on
four of those posts; the board has no holes. The seam is the board's top face, so every connector stands in a
notch in the cap's end walls and the cap lifts off with the plugs in place. Two #4 x 1/4 thread-forming screws
through the cap's ears into the tray's ears close it. The tray's floor goes to the air handler with VHB tape.

Positions are given in the board's own frame, as gen-ah-pico-d.py leaves it (x 0.3-65.7, y 0-56 from the top
edge, millimetres) and converted here: origin at the board's centre, x right, y toward the top edge, z 0 on the
board's top face.
"""
import os, sys
import FreeCAD as App
import Part
import MeshPart
V = App.Vector
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ahpd-case")
MODELS = os.environ.get("AHPD_MODELS")
FONT = os.environ.get("AHPD_FONT", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")
os.makedirs(OUT, exist_ok=True)

BX0, BX1, BL, BT = 0.3, 65.7, 56.0, 1.6           # the board
OX, OY = (BX0 + BX1) / 2, BL / 2
X = lambda x: x - OX
Y = lambda y: OY - y
HX, HY = (BX1 - BX0) / 2, BL / 2                  # board half sizes

GAP = 0.3              # board to wall, each side
WALL = 2.4
FLOOR = 2.0
STAND = 3.5            # tray posts: the through-hole leads stand up to 2.5 mm below the board
ROOM = 13.0            # above the board: U1 is 12.0 tall
TOP = 2.0
IX, IY = HX + GAP, HY + GAP                       # cavity half sizes
EX, EY = IX + WALL, IY + WALL                     # outside half sizes
ZB = -BT - STAND - FLOOR                          # outside bottom
ZT = ROOM + TOP                                   # outside top
LAP = 2.0              # the tray's side walls stand this far into the cap, at half thickness
FIT = 0.15

# where the cap's pins press the board on to the tray's posts (gen-ah-pico-d.py PINS, moved 7 mm right)
PINS = [(2.4, 14.5), (62.6, 7.6), (2.4, 44.1), (49.5, 42.0)]
# posts that only support: under the jack, the Pico's middle and the two ends of the sensor edge
POSTS = [(15.7, 3.0), (35.5, 28.0), (9.0, 51.0), (56.5, 51.0)]
# notches in the cap's end walls: centre x, half width, height above the board
TOP_NOTCH = (("USB", 15.7, 7.7, 7.4), ("PGM", 35.5, 6.3, 5.6), ("24 VAC", 54.5, 5.3, 10.6))
BOT_NOTCH = (("SUP", 6.25, 3.9, 6.0), ("RET", 17.85, 3.9, 6.0), ("1-WIRE", 56.5, 5.1, 6.0))
PGM_DIP = 2.2          # the tray's wall dips this far under the micro-USB, for the plug's overmould
# status LEDs: one column, a bore in the cap over each
LED_X = 3.2
LED = ((21.0, "PWR", "ledG"), (25.0, "FAN", "ledY"), (29.0, "Y1", "ledB"), (33.0, "Y2", "ledB"),
       (37.0, "W1", "ledR"), (41.0, "W2", "ledR"))
BLOCK = (0.0, 5.1, 18.6, 43.4)                    # the light block: x0, x1, y0, y1, down to 1.8 above the board
BLOCK_Z = 1.8
BORE = (1.0, 1.6)      # bore radius at the LED and at the cap's face
# ears: one each side at mid length
EAR_R, EAR_OUT = 4.0, 3.0
EAR_TAB = 3.0          # the cap ear's thickness under the screw head
PILOT, CLEAR = 2.5, 3.4


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
def cyl(x, y, r, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0))
def cone(x, y, r0, r1, z0, z1):
    return Part.makeCone(r0, r1, z1 - z0, V(x, y, z0))
def rounded(hx, hy, z0, z1, r):
    b = box(-hx, hx, -hy, hy, z0, z1)
    return b.makeFillet(r, [e for e in b.Edges if abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1])
def legend(s, size, x, y, depth=0.5, rot=0):
    """Text cut into the cap's top face, centred on board position x, y."""
    faces = [Part.makeFace(ch, "Part::FaceMakerBullseye") for ch in
             Part.makeWireString(s, os.path.dirname(FONT) + "/", os.path.basename(FONT), size, 0) if ch]
    t = Part.makeCompound(faces)
    c = t.BoundBox.Center
    t.translate(V(-c.x, -c.y, 0))
    if rot:
        t.rotate(V(0, 0, 0), V(0, 0, 1), rot)
    t.translate(V(X(x), Y(y), ZT - depth))
    return t.extrude(V(0, 0, depth + 0.1))
def ear(z0, z1):
    e = None
    for sgn in (-1, 1):
        x = sgn * (EX + EAR_OUT)
        s = cyl(x, 0, EAR_R, z0, z1).fuse(box(min(x, sgn * (EX - 0.5)), max(x, sgn * (EX - 0.5)), -EAR_R, EAR_R, z0, z1))
        e = s if e is None else e.fuse(s)
    return e

# --- tray
tray = rounded(EX, EY, ZB, 0, 3.0).cut(rounded(IX, IY, ZB + FLOOR, 1, 1.0))
for sgn in (-1, 1):                               # the lap: the inner half of each side wall stands into the cap
    x0, x1 = sorted((sgn * IX, sgn * (IX + WALL / 2)))
    tray = tray.fuse(box(x0, x1, -HY + 2, HY - 2, 0, LAP))
for x, y in PINS + POSTS:
    tray = tray.fuse(cyl(X(x), Y(y), 2.0, ZB + FLOOR - 0.1, -BT))
tray = tray.fuse(ear(ZB, 0))
for sgn in (-1, 1):
    tray = tray.cut(cyl(sgn * (EX + EAR_OUT), 0, PILOT / 2, ZB + 1.0, 1))
name, xc, hw, h = TOP_NOTCH[1]
tray = tray.cut(box(X(xc) - hw, X(xc) + hw, IY - 0.1, EY + 1, -PGM_DIP, 1))
tray = tray.removeSplitter()

# --- cap
cap = rounded(EX, EY, 0, ZT, 3.0).cut(rounded(IX, IY, -1, ROOM, 1.0))
bx0, bx1, by0, by1 = BLOCK
cap = cap.fuse(box(X(bx0) - GAP - 0.1, X(bx1), Y(by1), Y(by0), BLOCK_Z, ROOM + 0.1))
for x, y in PINS:
    cap = cap.fuse(cone(X(x), Y(y), 1.2, 2.6, 0.1, ROOM + 0.1))
cap = cap.fuse(ear(0, EAR_TAB))
for sgn in (-1, 1):
    cap = cap.cut(cyl(sgn * (EX + EAR_OUT), 0, CLEAR / 2, -1, EAR_TAB + 1))
    x0, x1 = sorted((sgn * (IX - FIT), sgn * (IX + WALL / 2 + FIT)))        # the rabbet the tray's lap enters
    cap = cap.cut(box(x0, x1, -HY + 2 - FIT, HY - 2 + FIT, -1, LAP + 0.2))
for notches, sgn in ((TOP_NOTCH, 1), (BOT_NOTCH, -1)):
    for name, xc, hw, h in notches:
        y0, y1 = sorted((sgn * (IY - 0.1), sgn * (EY + 1)))
        cap = cap.cut(box(X(xc) - hw, X(xc) + hw, y0, y1, -1, h))
        cap = cap.cut(legend(name, 2.6, xc, 3.6 if sgn > 0 else BL - 3.6))
for y, name, col in LED:
    cap = cap.cut(cone(X(LED_X), Y(y), BORE[0], BORE[1], BLOCK_Z - 0.1, ZT + 0.1))
    t = legend(name, 2.4, 0, y)
    t.translate(V(X(LED_X) + 2.6 + t.BoundBox.XLength / 2 - (t.BoundBox.Center.x - X(0)) - X(0), 0, 0))
    cap = cap.cut(t)
cap = cap.removeSplitter()

# --- fit: no part body may share volume with either half. x0, x1, y0, y1 in the board's frame, z0, z1 above its top
BODIES = {"board": (BX0, BX1, 0, BL, -BT, 0), "leads": (8.0, 23.5, 6.5, 13.0, -BT - 3.0, -BT),
          "U1 leads": (50.0, 52.2, 18.0, 38.2, -BT - 2.6, -BT), "J1 leads": (51.5, 57.5, 7.4, 9.6, -BT - 2.6, -BT),
          "J4": (8.45, 22.95, -1.5, 12.5, 0, 6.9), "U4": (25.0, 46.0, 1.3, 52.3, 0, 3.7),
          "micro-USB": (31.6, 39.4, -0.2, 6.0, 1.0, 3.8), "J1": (49.45, 59.66, 0.0, 10.85, 0, 9.3),
          "U1": (48.39, 58.15, 17.0, 39.2, 0, 12.0), "C1": (58.8, 65.4, 26.3, 32.9, 0, 7.8),
          "D2": (60.0, 63.6, 9.5, 16.5, 0, 2.5), "F1": (52.4, 58.8, 12.2, 16.2, 0, 1.6),
          "D1 C2": (58.3, 65.4, 35.7, 43.1, 0, 2.5), "Q1 R11 R12": (47.2, 51.5, 0.5, 16.4, 0, 1.3),
          "LEDs": (1.3, 5.2, 19.9, 42.1, 0, 0.9), "R5-R10": (5.3, 7.4, 19.0, 43.0, 0, 0.7), "left parts": (7.5, 23.8, 13.0, 37.0, 0, 1.8),
          "J3": (2.9, 9.6, 48.5, 56.0, 0, 5.0), "J5": (14.5, 21.2, 48.5, 56.0, 0, 5.0), "J2": (51.9, 61.1, 48.5, 56.0, 0, 5.0),
          "J3 plug": (3.0, 9.5, 51.0, 68.0, 0, 5.2), "J5 plug": (14.6, 21.1, 51.0, 68.0, 0, 5.2),
          "J2 plug": (52.0, 61.0, 51.0, 68.0, 0, 5.2), "J1 plug": (49.5, 59.5, -13.0, 0.5, 0.4, 10.0),
          "USB-A plug": (9.7, 21.7, -4.0, 9.5, 1.0, 5.5), "micro-USB plug": (30.0, 41.0, -9.0, -0.4, -1.2, 5.4)}
for part, (x0, x1, y0, y1, z0, z1) in BODIES.items():
    b = box(X(x0), X(x1), Y(y1), Y(y0), z0, z1)
    for shape, name in ((tray, "tray"), (cap, "cap")):
        if part == "board" and name == "tray":
            continue                                # the board rests on the posts
        v = shape.common(b).Volume
        assert v < 0.01, "%s meets the %s: %.2f mm3" % (part, name, v)
print("fit: %d bodies clear of tray and cap" % len(BODIES))

for shape, name in ((tray, "airmaster-tray"), (cap, "airmaster-cap")):
    assert shape.isValid() and len(shape.Solids) == 1, name
    shape.exportStep(os.path.join(OUT, name + ".step"))
    MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.03, AngularDeflection=0.35).write(os.path.join(OUT, name + ".stl"))
    b = shape.BoundBox
    print("%s: %.1f x %.1f x %.1f mm, %.1f cm3" % (name, b.XLength, b.YLength, b.ZLength, shape.Volume / 1000))
print("closed: %.1f x %.1f x %.1f mm, %.1f across the ears" % (2 * EX, 2 * EY, ZT - ZB, 2 * (EX + EAR_OUT + EAR_R)))

# --- models for the render
if MODELS:
    os.makedirs(MODELS, exist_ok=True)
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
        b = box(X(xc) - hw, X(xc) + hw, -HY, -HY + 7.5, 0, 5.0)
        return b.cut(box(X(xc) - hw + 0.6, X(xc) + hw - 0.6, -HY - 1, -HY + 4.5, 0.8, 4.2))
    jx = X(15.7)
    jack = box(jx - 7.25, jx + 7.25, HY - 12.5, HY + 1.5, 0, 6.9).cut(box(jx - 6.25, jx + 6.25, HY - 11, HY + 2.5, 0.9, 6.0))
    jack = jack.fuse(box(jx - 6.0, jx + 6.0, HY - 9.5, HY + 1.0, 3.0, 4.6))
    parts = [(ptsm(2, 6.25), "black"), (ptsm(2, 17.85), "black"), (ptsm(3, 56.5), "black"), (jack, "metal"),
             (box(X(48.49), X(58.09), Y(39.1), Y(17.1), 0, 12.0), "black")]
    for y, name, col in LED:
        parts.append((box(X(LED_X) - 1.0, X(LED_X) + 1.0, Y(y) - 0.625, Y(y) + 0.625, 0, 0.8), col))
    wrl("parts.wrl", parts)
    wrl("tray.wrl", [(tray, "tray")])
    lit = [(cyl(X(LED_X), Y(y), BORE[1] - 0.05, ZT - 0.6, ZT - 0.3), col) for y, name, col in LED]
    wrl("cap.wrl", [(cap, "cap")] + lit + [(cyl(sgn * (EX + EAR_OUT), 0, 2.8, EAR_TAB, EAR_TAB + 1.9), "head") for sgn in (-1, 1)])
    def wire(x, y0, y1, z, col, r=0.75):
        return (Part.makeCylinder(r, abs(y1 - y0), V(x, min(y0, y1), z), V(0, 1, 0)), col)
    pl = []
    for xc, n, cols in ((6.25, 2, ("wireW", "wireW")), (17.85, 2, ("wireW", "wireW")), (56.5, 3, ("wireR", "wireY", "wireK"))):
        a = (n - 1) * 2.5
        hw = a / 2 + 2.0
        pl.append((box(X(xc) - hw, X(xc) + hw, -HY - 11.4, -HY + 4.4, 0.9, 4.1).fuse(box(X(xc) - hw, X(xc) + hw, -HY - 11.4, -HY - 0.5, 0, 5.2)), "plugW"))
        for i, c in enumerate(cols):
            pl.append(wire(X(xc) - a / 2 + i * 2.5, -HY - 34, -HY - 11, 2.6, c, 0.7))
    xc = X(54.5)
    pl.append((box(xc - 5.0, xc + 5.0, HY - 0.5, HY + 13, 0.4, 9.5), "plugG"))
    for dx, c in ((1.905, "wireR"), (-1.905, "wireK")):
        pl.append((cyl(xc + dx, HY + 8.5, 1.3, 9.5, 10.0), "metal"))
        pl.append(wire(xc + dx, HY + 12.5, HY + 36, 4.0, c, 0.95))
    pl.append((box(jx - 6.0, jx + 6.0, HY - 9.5, HY + 4.0, 1.0, 5.5), "metal"))
    pl.append((box(jx - 8.0, jx + 8.0, HY + 4.0, HY + 27.5, -0.75, 7.25), "cable"))
    pl.append(wire(jx, HY + 27, HY + 48, 3.25, "cable", 2.3))
    wrl("plugs.wrl", pl)
    print("wrote models to", MODELS)
