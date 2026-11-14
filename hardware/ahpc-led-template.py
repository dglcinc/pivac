#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""Write a 1:1 drill template for the six Rev C status-LED holes in the 1593K base's floor, as a letter-size PDF.

    python3 hardware/ahpc-led-template.py hardware/ahpc-board/ahpc-led-drill-template.pdf

The holes come from the geometry hardware/ahp-box-models.py drills in its render: the LEDs sit on the board's back at
board x 3.5, under the USB-A side's cover screw, at board y 26.5 ... 46.5 mm, and the board's centre is the box's
centre (board 28.5, 28). Seen from outside the floor with the top panel (J1, micro-USB, J4) up, the board is mirrored,
so the column stands at x +25, straight below the right-hand cover screw, whose recess is a 6 mm circle at
(+/-25, 7.33) (Hammond's STEP). The template registers on those two recesses, not on the box's rounded outline, which
is drawn for orientation only. Print at 100 % (actual size) and check the 50 mm bar before cutting.
"""
import sys

MM = 72 / 25.4
BW, BH, BR = 66.22, 67.22, 5.0                 # base outline across, top to bottom, corner radius (orientation only)
SX, SY, SR = 25.0, 7.33, 3.0                   # cover-screw recesses at (+/-SX, SY), radius SR
HX, D = 25.0, 3.0                              # hole column x, hole diameter
LEDS = [("PWR", "green", 26.5), ("FAN", "yellow", 30.5), ("Y1", "blue", 34.5),
        ("Y2", "blue", 38.5), ("W1", "red", 42.5), ("W2", "red", 46.5)]

ops = []
def mv(x, y): ops.append(f"{x * MM:.2f} {y * MM:.2f} m")
def ln(x, y): ops.append(f"{x * MM:.2f} {y * MM:.2f} l")
def stroke(w=0.25, dash=None):
    ops.append(f"{w * MM:.2f} w " + (f"[{dash * MM:.2f}] 0 d " if dash else "[] 0 d ") + "S")
def line(x0, y0, x1, y1, w=0.25, dash=None):
    mv(x0, y0); ln(x1, y1); stroke(w, dash)
def circle(cx, cy, r, w=0.25):
    k = 0.5523 * r
    pts = [(cx + r, cy), (cx + r, cy + k, cx + k, cy + r, cx, cy + r), (cx - k, cy + r, cx - r, cy + k, cx - r, cy),
           (cx - r, cy - k, cx - k, cy - r, cx, cy - r), (cx + k, cy - r, cx + r, cy - k, cx + r, cy)]
    mv(*pts[0])
    for p in pts[1:]:
        ops.append(" ".join(f"{v * MM:.2f}" for v in p) + " c")
    stroke(w)
def text(x, y, s, size=9, bold=False):
    s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    ops.append(f"BT /{'F2' if bold else 'F1'} {size} Tf {x * MM:.2f} {y * MM:.2f} Td ({s}) Tj ET")

PW, PH = 215.9, 279.4
CX0, CY0 = PW / 2, 165.0                       # the box centre on the page; template y is up, as on the page

def P(x, y):
    return CX0 + x, CY0 + y

text(20, 260, "AirMaster Rev C: LED drill template, 1593K base, floor", 13, True)
text(20, 253, "Print at 100 % / Actual size. The bar below must measure 50 mm; if not, do not use the print.", 9)
line(20, 243, 70, 243, 0.4)
for x in (20, 70):
    line(x, 241, x, 245, 0.4)
text(38, 238, "50 mm", 8)

# the base's outline, seen from outside the floor, top panel up
x0, y0 = P(-BW / 2, -BH / 2)
x1, y1 = P(BW / 2, BH / 2)
k = 0.5523 * BR
mv(x0 + BR, y0); ln(x1 - BR, y0)
ops.append(f"{(x1 - BR + k) * MM:.2f} {y0 * MM:.2f} {x1 * MM:.2f} {(y0 + BR - k) * MM:.2f} {x1 * MM:.2f} {(y0 + BR) * MM:.2f} c")
ln(x1, y1 - BR)
ops.append(f"{x1 * MM:.2f} {(y1 - BR + k) * MM:.2f} {(x1 - BR + k) * MM:.2f} {y1 * MM:.2f} {(x1 - BR) * MM:.2f} {y1 * MM:.2f} c")
ln(x0 + BR, y1)
ops.append(f"{(x0 + BR - k) * MM:.2f} {y1 * MM:.2f} {x0 * MM:.2f} {(y1 - BR + k) * MM:.2f} {x0 * MM:.2f} {(y1 - BR) * MM:.2f} c")
ln(x0, y0 + BR)
ops.append(f"{x0 * MM:.2f} {(y0 + BR - k) * MM:.2f} {(x0 + BR - k) * MM:.2f} {y0 * MM:.2f} {(x0 + BR) * MM:.2f} {y0 * MM:.2f} c")
stroke(0.3, 1.0)
cx, cy = P(0, 0)
line(cx, y0 - 3, cx, y1 + 3, 0.15, 1.0)
line(x0 - 3, cy, x1 + 3, cy, 0.15, 1.0)
text(cx - 30, y1 + 4, "TOP PANEL: J1 24 VAC, micro-USB, J4", 8, True)
text(cx - 22, y0 - 7, "BOTTOM PANEL: sensor plugs", 8, True)

# the two cover-screw recesses: cut these out, they seat over the screw heads
for sx in (-SX, SX):
    x, y = P(sx, SY)
    circle(x, y, SR, 0.4)
    line(x - 1, y, x + 1, y, 0.15); line(x, y - 1, x, y + 1, 0.15)
text(P(-SX, SY)[0] - 7, P(0, SY)[1] + 4.5, "cut out", 7)
text(P(SX, SY)[0] - 7, P(0, SY)[1] + 4.5, "cut out", 7)

for name, col, by in LEDS:
    x, y = P(HX, 28.0 - by)
    circle(x, y, D / 2, 0.3)
    line(x - 1.9, y, x + 1.9, y, 0.15)
    line(x, y - 1.9, x, y + 1.9, 0.15)
    text(x - 11.5, y - 1.0, name, 6.5, True)

text(20, 113, "1. Cut out the template along the dashed outline, then cut out the two screw circles.", 9)
text(20, 107, "2. Close the box with its two cover screws. Lay the template on the floor, outside, TOP PANEL toward the end", 9)
text(20, 102.5, "   with J1, the micro-USB and J4, the screw circles seated round the two screw heads. Tape it down.", 9)
text(20, 96, "3. Open the box and take the board out. Centre-punch each cross on the floor, drill 1.5 mm, then 3 mm.", 9)
text(20, 91.5, "   Plastic: low speed, light pressure. Deburr inside, where the LEDs face the holes.", 9)
text(20, 85, "4. The column is 4 mm pitch, straight below the right-hand screw; PWR's centre is 5.83 mm below the screw's.", 9)
text(20, 80.5, "   From the top: PWR green, FAN yellow, Y1 blue, Y2 blue, W1 red, W2 red.", 9)
text(20, 74, "5. Fit the Rev C label afterwards: its right slot runs from that screw to the bottom edge, over the holes.", 9)
text(20, 67, "Generated by hardware/ahpc-led-template.py.", 7)

content = "\n".join(ops).encode()
objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PW * MM:.0f} {PH * MM:.0f}] "
         f"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>").encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream"]
out = bytearray(b"%PDF-1.4\n")
offs = []
for i, o in enumerate(objs, 1):
    offs.append(len(out)); out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
x = len(out)
out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
open(sys.argv[1], "wb").write(out)
print("wrote", sys.argv[1], [(HX, round(28.0 - by, 2)) for _, _, by in LEDS])
