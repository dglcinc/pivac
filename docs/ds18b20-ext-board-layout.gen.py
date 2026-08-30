#!/usr/bin/env python3
"""Generate ds18b20-ext-board-layout.svg (into this script's own directory).

RPI-BC EXT-PCB HBUS SET, from Phoenix drawing 00913308/02, in BUILD orientation:
component side up, the close-margin end at the top (row 1), the power-riser
field on the left (columns 1-2). Columns 1-14 left to right, rows 1-32 top to
bottom. This is the drawing's TOP view turned 180 degrees in the plane."""

import os

P = 24.0
MX, MY = 152.0, 150.0

def X(c): return MX + (c-1)*P
def Y(r): return MY + (r-1)*P

ONEW = "#C2622A"   # 1-wire nets (orange)
I2C  = "#4A7FB5"   # link to the Pi board (blue)
ACC  = "#A85F22"

out = []
W_, H_ = 660, 1090
out.append(f'<svg viewBox="0 0 {W_} {H_}" role="img" aria-label="Hole-by-hole placement map of the RPI-BC extension board, component side, close-margin end at the top. Three 3-position probe sockets have their pins in row 2 with entries facing the row-1 edge and the enclosure opening. Three bare rails on rows 3, 4 and 5 bus VCC, DATA and GND. Three component-side bridges at columns 6, 10 and 12 carry those nets over the keep-out band at rows 8 and 9 into the lower field, where the DS2482 sits in columns 8 and 11, rows 12 to 15, and a 4-position link terminal to the Pi board sits in row 18, columns 8 to 11. The power-riser field at columns 1 to 5, rows 11 to 23, is unused." xmlns="http://www.w3.org/2000/svg" style="max-width:100%;height:auto">')
out.append('<defs>'
  '<pattern id="hx2" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
  f'<line x1="0" y1="0" x2="0" y2="9" stroke="{ACC}" stroke-width="1.4" opacity=".55"/></pattern>'
  '</defs>')
out.append('<g font-family="IBM Plex Mono, ui-monospace, monospace" font-size="10" fill="currentColor">')
out.append(f'<text x="{MX-140}" y="22" font-size="13" font-weight="600">EXT BOARD, COMPONENT SIDE — hole grid (column,row)</text>')
out.append(f'<text x="{MX-140}" y="38" font-size="10" opacity=".82">row 1 = the end whose holes sit CLOSEST to the board edge · column 1 = the power-riser side</text>')

# outline: unequal end margins, as on the real board
bx0, bx1 = X(1)-1.1*P, X(14)+1.1*P
by0, by1 = Y(1)-1.0*P, Y(32)+1.45*P
out.append(f'<rect x="{bx0:.0f}" y="{by0:.0f}" width="{bx1-bx0:.0f}" height="{by1-by0:.0f}" rx="4" fill="none" stroke="currentColor" stroke-width="2"/>')
out.append(f'<text x="{(bx0+bx1)/2:.0f}" y="{by0-24:.0f}" text-anchor="middle" font-size="9.5" font-weight="600">▲ SHORT-END OPENING — probe plugs enter here ▲</text>')
out.append(f'<text x="{(bx0+bx1)/2:.0f}" y="{by0-11:.0f}" text-anchor="middle" font-size="8.5" opacity=".8">row 1 is the narrow end margin — this is how you tell the two ends apart</text>')
out.append(f'<text x="{(bx0+bx1)/2:.0f}" y="{by1+15:.0f}" text-anchor="middle" font-size="9" opacity=".85">▼ second short-end opening (spare) ▼</text>')

for c in range(1,15):
    out.append(f'<text x="{X(c):.0f}" y="{by1+31:.0f}" text-anchor="middle" font-size="8.5" opacity=".75">{c}</text>')
for r in range(1,33):
    out.append(f'<text x="{bx0-6:.0f}" y="{Y(r)+3:.0f}" text-anchor="end" font-size="8.5" opacity=".75">{r}</text>')
    out.append(f'<text x="{bx1+7:.0f}" y="{Y(r)+3:.0f}" font-size="8.5" opacity=".75">{r}</text>')

# long-side annotations
out.append(f'<text x="{bx0-30:.0f}" y="{Y(27):.0f}" text-anchor="middle" font-size="9" font-weight="600" fill="{ACC}" transform="rotate(-90 {bx0-30:.0f} {Y(27):.0f})">riser side — enclosure wall</text>')
out.append(f'<text x="{bx1+34:.0f}" y="{Y(27):.0f}" text-anchor="middle" font-size="9" font-weight="600" fill="{I2C}" transform="rotate(90 {bx1+34:.0f} {Y(27):.0f})">opening to the Pi board</text>')

# keep-out bands
def hrect(x0,y0,x1,y1):
    out.append(f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1-x0:.0f}" height="{y1-y0:.0f}" fill="url(#hx2)" stroke="{ACC}" stroke-width="1.4"/>')
hrect(bx0+2, Y(8)-P/2, bx1-2, Y(9)+P/2)
hrect(bx0+2, Y(25)-P/2, bx1-2, Y(26)+P/2)
out.append(f'<text x="{X(1)-4:.0f}" y="{Y(8)-P/2-4:.0f}" font-size="9" fill="{ACC}">keep-out — rows 8–9</text>')
out.append(f'<text x="{X(1)-4:.0f}" y="{Y(26)+P/2+12:.0f}" font-size="9" fill="{ACC}">keep-out — rows 25–26</text>')

# riser field, unused
out.append(f'<rect x="{X(1)-13:.0f}" y="{Y(11)-13:.0f}" width="{X(5)-X(1)+26:.0f}" height="{Y(23)-Y(11)+26:.0f}" rx="4" fill="none" stroke="currentColor" stroke-width="1.3" stroke-dasharray="5 4" opacity=".65"/>')
out.append(f'<text x="{X(3):.0f}" y="{Y(17)+3:.0f}" text-anchor="middle" font-size="9" font-weight="600" opacity=".8" transform="rotate(-90 {X(3):.0f} {Y(17):.0f})">POWER RISER — UNUSED</text>')

# holes
def exists(c,r):
    if c==3 and 11<=r<=23: return False
    if c in (1,2) and r in (11,12,22,23): return False
    return True
for r in range(1,33):
    for c in range(1,15):
        if exists(c,r):
            out.append(f'<circle cx="{X(c):.0f}" cy="{Y(r):.0f}" r="2.6" fill="currentColor" opacity=".22"/>')
for r in range(13,22):
    for c in (1,2):
        out.append(f'<rect x="{X(c)-3:.0f}" y="{Y(r)-3:.0f}" width="6" height="6" fill="none" stroke="currentColor" stroke-width="1" opacity=".5"/>')
    for c in (4,5):
        out.append(f'<circle cx="{X(c):.0f}" cy="{Y(r):.0f}" r="4" fill="none" stroke="currentColor" stroke-width=".9" opacity=".4"/>')

def wire(pts, col, dash=None, wdt=1.5):
    d = ' '.join(f'{x:.0f},{y:.0f}' for x,y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ''
    out.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{wdt}"{da}/>')

# three probe sockets, pins in row 2, bodies overhanging toward the row-1 edge
for name, c0 in (('H1',2), ('H2',7), ('H3',12)):
    x0, x1 = X(c0)-15, X(c0+2)+15
    out.append(f'<rect x="{x0:.0f}" y="{by0+3:.0f}" width="{x1-x0:.0f}" height="{Y(2)-by0-8:.0f}" rx="3" fill="none" stroke="{ACC}" stroke-width="1.8"/>')
    out.append(f'<text x="{(x0+x1)/2:.0f}" y="{Y(1)+4:.0f}" text-anchor="middle" font-size="10" font-weight="700" fill="{ACC}">{name}</text>')
    for k,lab in enumerate(('V','D','G')):
        out.append(f'<circle cx="{X(c0+k):.0f}" cy="{Y(2):.0f}" r="5.5" fill="none" stroke="{ACC}" stroke-width="1.5"/>')
        out.append(f'<text x="{X(c0+k):.0f}" y="{Y(2)+3:.0f}" text-anchor="middle" font-size="7.5" fill="{ACC}">{lab}</text>')

# rails rows 3 / 4 / 5
out.append(f'<line x1="{X(2):.0f}" y1="{Y(3):.0f}" x2="{X(12):.0f}" y2="{Y(3):.0f}" stroke="currentColor" stroke-width="2.8"/>')
out.append(f'<line x1="{X(3):.0f}" y1="{Y(4):.0f}" x2="{X(13):.0f}" y2="{Y(4):.0f}" stroke="currentColor" stroke-width="2.8"/>')
out.append(f'<line x1="{X(4):.0f}" y1="{Y(5):.0f}" x2="{X(14):.0f}" y2="{Y(5):.0f}" stroke="currentColor" stroke-width="2.8"/>')
out.append(f'<text x="{MX-140}" y="54" font-size="10" opacity=".82">bus rails, solder side: row 3 = VCC · row 4 = DATA · row 5 = GND</text>')
for c in (2,7,12):                                    # V: bare stub
    out.append(f'<line x1="{X(c):.0f}" y1="{Y(2):.0f}" x2="{X(c):.0f}" y2="{Y(3):.0f}" stroke="currentColor" stroke-width="1.7"/>')
for c in (3,8,13):                                    # D: insulated jumper over the VCC rail
    wire([(X(c),Y(2)),(X(c),Y(4))], ONEW)
for c in (4,9,14):                                    # G: insulated jumper over both rails
    wire([(X(c),Y(2)),(X(c),Y(5))], ONEW)

# component-side bridges over the rows 8-9 band
for c, r0, lab in ((6,3,'V'), (10,4,'D'), (12,5,'G')):
    wire([(X(c),Y(r0)),(X(c),Y(10))], ONEW, dash='5 4', wdt=2.1)
    out.append(f'<text x="{X(c)+7:.0f}" y="{Y(8)+14:.0f}" font-size="8" font-weight="600" fill="{ONEW}">{lab}</text>')

# lower-field rails
out.append(f'<line x1="{X(6):.0f}" y1="{Y(10):.0f}" x2="{X(6):.0f}" y2="{Y(18):.0f}" stroke="currentColor" stroke-width="2.8"/>')
out.append(f'<line x1="{X(12):.0f}" y1="{Y(10):.0f}" x2="{X(12):.0f}" y2="{Y(18):.0f}" stroke="currentColor" stroke-width="2.8"/>')
out.append(f'<text x="{X(6):.0f}" y="{Y(10)-8:.0f}" text-anchor="middle" font-size="8.5" font-weight="600">VCC</text>')
out.append(f'<text x="{X(12):.0f}" y="{Y(10)-8:.0f}" text-anchor="middle" font-size="8.5" font-weight="600">GND</text>')

# DS2482 socket, cols 8 & 11, rows 12-15, notch toward row 11
x0,x1 = X(8)-3, X(11)+3
y0,y1 = Y(12)-P/2+3, Y(15)+P/2-3
out.append(f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1-x0:.0f}" height="{y1-y0:.0f}" rx="3" fill="none" stroke="currentColor" stroke-width="1.7"/>')
out.append(f'<path d="M{(x0+x1)/2-8:.0f},{y0:.0f} a8,8 0 0,1 16,0" fill="none" stroke="currentColor" stroke-width="1.7"/>')
out.append(f'<text x="{(x0+x1)/2:.0f}" y="{Y(11)-4:.0f}" text-anchor="middle" font-size="9.5" font-weight="600">DS2482 — notch UP</text>')
for r,l in {12:'VCC',13:'IO',14:'GND',15:'SCL'}.items():
    out.append(f'<rect x="{X(8)-3:.0f}" y="{Y(r)-4:.0f}" width="6" height="8" fill="currentColor"/>')
    out.append(f'<text x="{X(8)+7:.0f}" y="{Y(r)+3:.0f}" font-size="7">{l}</text>')
for r,l in {12:'AD0',13:'AD1',14:'n/c',15:'SDA'}.items():
    out.append(f'<rect x="{X(11)-3:.0f}" y="{Y(r)-4:.0f}" width="6" height="8" fill="currentColor"/>')
    out.append(f'<text x="{X(11)-7:.0f}" y="{Y(r)+3:.0f}" text-anchor="end" font-size="7">{l}</text>')
out.append(f'<circle cx="{X(8)-8:.0f}" cy="{Y(12)-9:.0f}" r="2.3" fill="currentColor"/>')
out.append(f'<text x="{X(8)-13:.0f}" y="{Y(12)-6:.0f}" text-anchor="end" font-size="7">pin1</text>')

# 100 nF at (9,16)-(10,16)
out.append(f'<line x1="{X(9):.0f}" y1="{Y(16):.0f}" x2="{X(10):.0f}" y2="{Y(16):.0f}" stroke="{ONEW}" stroke-width="1.3"/>')
out.append(f'<rect x="{(X(9)+X(10))/2-9:.0f}" y="{Y(16)-5:.0f}" width="18" height="10" rx="2" fill="none" stroke="{ONEW}" stroke-width="1.5"/>')
out.append(f'<text x="{(X(9)+X(10))/2:.0f}" y="{Y(16)-9:.0f}" text-anchor="middle" font-size="7.5" fill="{ONEW}">100n</text>')

# 4-position link terminal, pins row 18 cols 8-11, body toward row 19
tx0,tx1 = X(8)-15, X(11)+15
out.append(f'<rect x="{tx0:.0f}" y="{Y(18)-13:.0f}" width="{tx1-tx0:.0f}" height="{Y(21)-Y(18)+13:.0f}" rx="3" fill="none" stroke="{I2C}" stroke-width="1.9"/>')
for c,l in ((8,'C'),(9,'V'),(10,'G'),(11,'D')):
    out.append(f'<circle cx="{X(c):.0f}" cy="{Y(18):.0f}" r="5.5" fill="none" stroke="{I2C}" stroke-width="1.5"/>')
    out.append(f'<text x="{X(c):.0f}" y="{Y(18)+3:.0f}" text-anchor="middle" font-size="7.5" fill="{I2C}">{l}</text>')
out.append(f'<text x="{(tx0+tx1)/2:.0f}" y="{Y(20)+2:.0f}" text-anchor="middle" font-size="9" font-weight="700" fill="{I2C}">LINK TO THE Pi BOARD</text>')
out.append(f'<text x="{(tx0+tx1)/2:.0f}" y="{Y(20)+14:.0f}" text-anchor="middle" font-size="8" fill="{I2C}">SCL · 3V3 · GND · SDA</text>')
out.append(f'<text x="{(tx0+tx1)/2:.0f}" y="{Y(21)+8:.0f}" text-anchor="middle" font-size="8" fill="{I2C}">pull this plug + the probe plugs</text>')
out.append(f'<text x="{(tx0+tx1)/2:.0f}" y="{Y(21)+19:.0f}" text-anchor="middle" font-size="8" fill="{I2C}">and the board lifts out</text>')

# lower-field wiring
wire([(X(6),Y(12)),(X(8),Y(12))], ONEW)                       # V1 rail -> VCC pin
wire([(X(6),Y(16)),(X(9),Y(16))], ONEW)                       # V2 rail -> cap
wire([(X(6),Y(18)),(X(9),Y(18))], ONEW)                       # V3 rail -> 3V3 pin
out.append(f'<line x1="{X(12):.0f}" y1="{Y(12):.0f}" x2="{X(11):.0f}" y2="{Y(12):.0f}" stroke="currentColor" stroke-width="1.7"/>')  # AD0 stub
out.append(f'<line x1="{X(12):.0f}" y1="{Y(13):.0f}" x2="{X(11):.0f}" y2="{Y(13):.0f}" stroke="currentColor" stroke-width="1.7"/>')  # AD1 stub
wire([(X(12),Y(14)),(X(8),Y(14))], ONEW)                      # G1 rail -> GND pin
wire([(X(12),Y(16)),(X(10),Y(16))], ONEW)                     # G2 rail -> cap
wire([(X(12),Y(18)),(X(10),Y(18))], ONEW)                     # G3 rail -> GND pin
wire([(X(10),Y(10)),(X(10),Y(10)+7),(X(7),Y(10)+7),(X(7),Y(13)),(X(8),Y(13))], ONEW)  # D1 -> IO
wire([(X(8),Y(15)),(X(8)-6,Y(16)),(X(8)-6,Y(17)),(X(8),Y(18))], I2C)     # S1 SCL
wire([(X(11),Y(15)),(X(11)+6,Y(16)),(X(11)+6,Y(17)),(X(11),Y(18))], I2C) # S2 SDA

# legend
ly = Y(32)+52
out.append(f'<line x1="{MX-110}" y1="{ly:.0f}" x2="{MX-72}" y2="{ly:.0f}" stroke="currentColor" stroke-width="2.8"/>')
out.append(f'<text x="{MX-64}" y="{ly+3:.0f}" font-size="9">bare rail or 1-hole stub, solder side</text>')
out.append(f'<line x1="{MX+180}" y1="{ly:.0f}" x2="{MX+218}" y2="{ly:.0f}" stroke="{ONEW}" stroke-width="1.5"/>')
out.append(f'<text x="{MX+226}" y="{ly+3:.0f}" font-size="9">insulated wire, solder side</text>')
ly2 = ly+16
out.append(f'<line x1="{MX-110}" y1="{ly2:.0f}" x2="{MX-72}" y2="{ly2:.0f}" stroke="{ONEW}" stroke-width="2.1" stroke-dasharray="5 4"/>')
out.append(f'<text x="{MX-64}" y="{ly2+3:.0f}" font-size="9">bridge on the COMPONENT side — the only legal way across a band</text>')
ly3 = ly2+16
out.append(f'<line x1="{MX-110}" y1="{ly3:.0f}" x2="{MX-72}" y2="{ly3:.0f}" stroke="{I2C}" stroke-width="1.5"/>')
out.append(f'<text x="{MX-64}" y="{ly3+3:.0f}" font-size="9">I²C · V/D/G = VCC / DATA / GND · C = SCL, D = SDA on the link plug</text>')
ly4 = ly3+16
out.append(f'<rect x="{MX-108}" y="{ly4-6:.0f}" width="26" height="12" fill="url(#hx2)" stroke="{ACC}" stroke-width="1"/>')
out.append(f'<text x="{MX-64}" y="{ly4+3:.0f}" font-size="9">keep-out (solder side) — no rail, wire or joint here</text>')

out.append('</g></svg>')
open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'ds18b20-ext-board-layout.svg'),'w').write('\n'.join(out)+'\n')
print('wrote', len(out), 'elements')
