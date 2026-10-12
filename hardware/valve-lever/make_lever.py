"""Flat pattern for a 316 stainless replacement lever (A.Y. McDonald ball valve).

Writes valve-lever-316.dxf (cut outline and hole only) and valve-lever-1to1.svg
(print at 100 % with bend lines) beside this script. Needs ezdxf.
See docs/valve-lever-replacement.md.

Seen from the outside (the side away from the valve), grip pointing down (-y),
origin at the stem centre, mm. Lugs bend 90 deg into the page (toward the valve);
the jog steps the grip 15 mm out of the page.
"""
import math, os, ezdxf

HERE = os.path.dirname(os.path.abspath(__file__))

T = 3.05                  # 0.120" 316
BACK = 10.0               # hole centre to back edge of head
HEAD_HALF = 10.0          # head 20 mm wide
BEND1 = -15.0             # hole centre to first jog bend
OFFSET, RAMP_DEG = 15.0, 60.0
GRIP_HALF = 8.0           # grip 16 mm wide
REACH = 100.0             # hole centre to tip, measured parallel to the face
RAMP = OFFSET / math.sin(math.radians(RAMP_DEG))
RAMP_RUN = OFFSET / math.tan(math.radians(RAMP_DEG))
BEND2 = BEND1 - RAMP
TIP = BEND2 - (REACH - abs(BEND1) - RAMP_RUN)
TIPC = TIP + GRIP_HALF

TAB_W, TAB_L = 5.0, 7.0   # stop lugs, flat length beyond the bend line
RW, RD = 1.6, 1.5         # bend relief width and depth
A_X = 4.8                 # lug A centre, offset right on the back edge
B_Y = -3.9                # lug B centre, toward the grip on the left edge

ax0, ax1 = A_X - TAB_W / 2, A_X + TAB_W / 2
by0, by1 = B_Y - TAB_W / 2, B_Y + TAB_W / 2

# outline, counter-clockwise, (x, y, bulge)
pts = [
    (GRIP_HALF, TIPC, 0), (GRIP_HALF, BEND2, 0), (HEAD_HALF, BEND1, 0),
    (HEAD_HALF, BACK, 0),
    (ax1 + RW, BACK, 0), (ax1 + RW, BACK - RD, 0), (ax1, BACK - RD, 0),
    (ax1, BACK + TAB_L, 0), (ax0, BACK + TAB_L, 0),
    (ax0, BACK - RD, 0), (ax0 - RW, BACK - RD, 0), (ax0 - RW, BACK, 0),
    (-HEAD_HALF, BACK, 0),
    (-HEAD_HALF, by1 + RW, 0), (-HEAD_HALF + RD, by1 + RW, 0), (-HEAD_HALF + RD, by1, 0),
    (-HEAD_HALF - TAB_L, by1, 0), (-HEAD_HALF - TAB_L, by0, 0),
    (-HEAD_HALF + RD, by0, 0), (-HEAD_HALF + RD, by0 - RW, 0), (-HEAD_HALF, by0 - RW, 0),
    (-HEAD_HALF, BEND1, 0), (-GRIP_HALF, BEND2, 0), (-GRIP_HALF, TIPC, 1),
]

# double-D hole, 8.1 mm across the round, 5.1 across the flats, flats parallel to the lever
R, F = 8.1 / 2, 5.1 / 2
yf = math.sqrt(R * R - F * F)
half = math.asin(F / R)                      # half-angle of each arc about the y axis
bulge = math.tan((2 * half) / 4)
hole = [(F, -yf, 0), (F, yf, bulge), (-F, yf, 0), (-F, -yf, bulge)]

doc = ezdxf.new("R2010", setup=False)
doc.units = ezdxf.units.MM
msp = doc.modelspace()
msp.add_lwpolyline([(x, y, 0, 0, b) for x, y, b in pts], format="xyseb", close=True)
msp.add_lwpolyline([(x, y, 0, 0, b) for x, y, b in hole], format="xyseb", close=True)
doc.saveas(os.path.join(HERE, "valve-lever-316.dxf"))

# 1:1 SVG with bend lines for printing and overlay check
def path(p):
    d = f"M {p[0][0]:.3f} {-p[0][1]:.3f} "
    for i in range(len(p)):
        x0, y0, b = p[i]
        x1, y1, _ = p[(i + 1) % len(p)]
        if b:
            chord = math.hypot(x1 - x0, y1 - y0)
            r = chord * (1 + b * b) / (4 * abs(b))
            large = 1 if abs(b) > 1 else 0
            sweep = 0 if b > 0 else 1   # y is flipped in SVG
            d += f"A {r:.3f} {r:.3f} 0 {large} {sweep} {x1:.3f} {-y1:.3f} "
        else:
            d += f"L {x1:.3f} {-y1:.3f} "
    return d + "Z"

minx, maxx = -HEAD_HALF - TAB_L - 6, HEAD_HALF + 85
miny, maxy = -(BACK + TAB_L + 6), -TIP + 6
w, h = maxx - minx, maxy - miny
dash = 'stroke-dasharray="2 1.5"'
lines = [
    f'<line x1="{-HEAD_HALF-2}" y1="{-BEND1}" x2="{HEAD_HALF+2}" y2="{-BEND1}" stroke="red" stroke-width="0.25" {dash}/>',
    f'<line x1="{-GRIP_HALF-2}" y1="{-BEND2:.3f}" x2="{GRIP_HALF+2}" y2="{-BEND2:.3f}" stroke="red" stroke-width="0.25" {dash}/>',
    f'<line x1="{ax0-RW}" y1="{-BACK}" x2="{ax1+RW}" y2="{-BACK}" stroke="blue" stroke-width="0.25" {dash}/>',
    f'<line x1="{-HEAD_HALF}" y1="{-(by0-RW)}" x2="{-HEAD_HALF}" y2="{-(by1+RW)}" stroke="blue" stroke-width="0.25" {dash}/>',
]
txt = lambda x, y, s: f'<text x="{x}" y="{y}" font-size="2.6" font-family="Helvetica">{s}</text>'
labels = [
    txt(HEAD_HALF + 4, -BEND1 + 1, f"jog bend 1: grip side out {RAMP_DEG:.0f}°"),
    txt(GRIP_HALF + 4, -BEND2 + 1, f"jog bend 2: back {RAMP_DEG:.0f}°, grip 15 mm off face"),
    txt(HEAD_HALF + 4, -BACK + 1, "lugs (blue): 90° toward the valve"),
    txt(GRIP_HALF + 4, -TIP - 20, "outside face up"),
    txt(GRIP_HALF + 4, -TIP - 15, f"316, {T} mm; flat length {BACK + TAB_L - TIP:.1f} mm"),
    txt(GRIP_HALF + 4, -TIP - 10, "check: 50 mm bar below must print 50 mm"),
    f'<line x1="{GRIP_HALF+4}" y1="{-TIP-6}" x2="{GRIP_HALF+54}" y2="{-TIP-6}" stroke="black" stroke-width="0.4"/>',
]
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w:.1f}mm" height="{h:.1f}mm" viewBox="{minx} {miny} {w:.1f} {h:.1f}">
<path d="{path(pts)}" fill="none" stroke="black" stroke-width="0.25"/>
<path d="{path(hole)}" fill="none" stroke="black" stroke-width="0.25"/>
{chr(10).join(lines + labels)}
</svg>'''
open(os.path.join(HERE, "valve-lever-1to1.svg"), "w").write(svg)
print(f"ramp {RAMP:.1f} mm, bend2 at {BEND2:.1f}, tip at {TIP:.1f}, flat length {BACK + TAB_L - TIP:.1f}")
