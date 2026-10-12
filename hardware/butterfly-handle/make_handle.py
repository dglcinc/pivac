"""Replacement butterfly handle for the red-handled drain ball valves (M6x1 stem nut).

Writes butterfly-handle.step and butterfly-handle.stl (for printing in 316L or PA12)
and butterfly-handle-1to1.svg (underside and side view, print at 100 % and lay the
old base on it) beside this script. Needs cadquery. See docs/valve-lever-replacement.md.

Origin at the stem centre on the face that sits on the valve, z up toward the nut, mm.
The wings and the stop lug lie on +x/-x, the double-D's long axis (its round ends);
the flats are parallel to x.
"""
import os
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))

# Base, copied from the broken original (caliper readings 2026-10-12). It fits over the
# bonnet ring: 19 mm OD, 2 mm wall, 7 mm tall outside, 2 mm deep inside to the packing washer.
BASE_D = 26.42            # outside of the base
BASE_H = 8.20             # base height, valve face to nut face
GROOVE_ID = 13.74         # boss around the stem hole
GROOVE_OD = 19.51         # inside of the skirt; the bonnet rim runs in this groove
GROOVE_DEPTH = 4.3        # measured 3.8 on the worn base; deepened so the rim cannot bottom
BOSS_RECESS = 2.0         # boss face above the skirt face; the ring is 2 mm deep inside, so
                          # the boss reaches the packing washer as the rim enters the groove
LUG_W = 7.93              # stop lug across the groove, tangential width
LUG_H = 1.5               # lug reaches this far down from the groove floor; must clear the
                          # floor of the rim's cutaway (estimated from photos, confirm)
HOLE_FLATS = 7.30         # stem drive 7.16 across the flats, plus clearance
HOLE_ROUND = 9.20         # stem drive 9.08 across the round, plus clearance

# Wings: blades rising from the base so the grip clears the insulation
SPAN = 85.0               # tip to tip
BLADE_T = 10.0            # blade thickness (the face the hand pushes on)
SOCKET_R = 9.0            # clear radius above the nut face for a 10 mm socket
ROOT_Z = 4.0              # blade underside leaves the base at the groove depth
RISE = 0.36               # blade slope, about 20 degrees
BLADE_H = 11.5            # blade height, measured vertically


def handle():
    r = BASE_D / 2
    body = cq.Workplane("XY").circle(r).extrude(BASE_H)

    # Annular groove in the valve face, the boss set back inside it, and the stop lug
    # hanging from the groove floor on +x
    groove = (cq.Workplane("XY").circle(GROOVE_OD / 2).circle(GROOVE_ID / 2)
              .extrude(GROOVE_DEPTH))
    lug = (cq.Workplane("XY").workplane(offset=GROOVE_DEPTH - LUG_H)
           .center(GROOVE_OD / 4 + GROOVE_ID / 4, 0)
           .rect(GROOVE_OD / 2 - GROOVE_ID / 2 + 0.2, LUG_W).extrude(LUG_H))
    recess = cq.Workplane("XY").circle(GROOVE_ID / 2 + 0.01).extrude(BOSS_RECESS)
    body = body.cut(groove.cut(lug)).cut(recess)

    # Two blades in the XZ plane, thickness BLADE_T in y
    tip = SPAN / 2
    for s in (1, -1):
        pts = [(s * r, ROOT_Z),
               (s * tip, ROOT_Z + RISE * (tip - r)),
               (s * tip, ROOT_Z + RISE * (tip - r) + BLADE_H),
               (s * SOCKET_R, ROOT_Z + RISE * (tip - r) + BLADE_H - RISE * (tip - SOCKET_R)),
               (s * SOCKET_R, BASE_H),
               (s * (r - 0.01), BASE_H - 0.01)]
        blade = (cq.Workplane("XZ").polyline(pts).close()
                 .extrude(BLADE_T / 2, both=True))
        blade = blade.edges("|Y and >X" if s > 0 else "|Y and <X").fillet(3.0)
        body = body.union(blade)

    # Double-D stem hole, round ends on x, flats parallel to x
    hole = (cq.Workplane("XY").circle(HOLE_ROUND / 2).extrude(BASE_H + 1)
            .intersect(cq.Workplane("XY").rect(HOLE_ROUND + 1, HOLE_FLATS).extrude(BASE_H + 1)))
    body = body.cut(hole)
    return body


def svg(path):
    """Underside (as seen from the valve, +x to the right) and side view, 1:1 in mm."""
    r, tip = BASE_D / 2, SPAN / 2
    ox, oy, sy = 55.0, 30.0, 80.0          # underside centre, side-view baseline
    hr, hf = HOLE_ROUND / 2, HOLE_FLATS / 2
    import math
    xf = math.sqrt(hr * hr - hf * hf)
    d = []
    d.append(f'<circle cx="{ox}" cy="{oy}" r="{r}"/>')
    d.append(f'<circle cx="{ox}" cy="{oy}" r="{GROOVE_OD/2}" stroke-dasharray="1,0.6"/>')
    d.append(f'<circle cx="{ox}" cy="{oy}" r="{GROOVE_ID/2}" stroke-dasharray="1,0.6"/>')
    d.append(f'<rect x="{ox+GROOVE_ID/2}" y="{oy-LUG_W/2}" width="{(GROOVE_OD-GROOVE_ID)/2}" '
             f'height="{LUG_W}" fill="#bbb"/>')
    d.append(f'<path d="M{ox-xf},{oy-hf} L{ox+xf},{oy-hf} A{hr},{hr} 0 0 1 {ox+xf},{oy+hf} '
             f'L{ox-xf},{oy+hf} A{hr},{hr} 0 0 1 {ox-xf},{oy-hf} Z"/>')
    for s in (1, -1):
        d.append(f'<rect x="{ox + (r if s > 0 else -tip)}" y="{oy-BLADE_T/2}" width="{tip-r}" '
                 f'height="{BLADE_T}" stroke-dasharray="2,1"/>')
    z = lambda v: sy - v
    d.append(f'<rect x="{ox-r}" y="{z(BASE_H)}" width="{BASE_D}" height="{BASE_H}"/>')
    for s in (1, -1):
        pts = [(r, ROOT_Z), (tip, ROOT_Z + RISE * (tip - r)),
               (tip, ROOT_Z + RISE * (tip - r) + BLADE_H),
               (SOCKET_R, ROOT_Z + RISE * (tip - r) + BLADE_H - RISE * (tip - SOCKET_R)),
               (SOCKET_R, BASE_H)]
        d.append('<polyline points="' + " ".join(f"{ox+s*x:.2f},{z(y):.2f}" for x, y in pts) + '"/>')
    d.append(f'<line x1="{ox-tip}" y1="{sy+6}" x2="{ox+10-tip}" y2="{sy+6}" stroke-width="0.5"/>')
    t = lambda x, y, txt: d.append(f'<text x="{x}" y="{y}" font-size="3" font-family="Helvetica" '
                                   f'stroke="none" fill="#000">{txt}</text>')
    t(ox - tip, sy + 11, "10 mm scale. Print at 100 %.")
    t(5, 5, "Underside, seen from the valve. Grey: stop lug. Dashed circles:")
    t(5, 9, f"groove {GROOVE_ID}-{GROOVE_OD} mm, {GROOVE_DEPTH} mm deep; boss set back {BOSS_RECESS} mm;")
    t(5, 13, f"lug {LUG_H} mm deep. Dashed boxes: wings above.")
    t(5, sy - 32, f"Side view. Base {BASE_H} mm, span {SPAN:.0f} mm,")
    t(5, sy - 28, f"hole {HOLE_FLATS} x {HOLE_ROUND} mm double-D.")
    w, h = 2 * ox, sy + 16
    open(path, "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
        f'viewBox="0 0 {w} {h}"><g fill="none" stroke="#000" stroke-width="0.25">'
        + "".join(d) + "</g></svg>\n")


if __name__ == "__main__":
    h = handle()
    cq.exporters.export(h, os.path.join(HERE, "butterfly-handle.step"))
    cq.exporters.export(h, os.path.join(HERE, "butterfly-handle.stl"), tolerance=0.02)
    bb = h.val().BoundingBox()
    svg(os.path.join(HERE, "butterfly-handle-1to1.svg"))
    print(f"bbox {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm, volume {h.val().Volume():.0f} mm3")
