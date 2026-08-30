#!/usr/bin/env python3
"""Generate ds18b20-ext-board-layout.svg (into this script's own directory).
RPI-BC EXT-PCB HBUS SET (drawing 00913308/02), TOP view: columns 1-14 left to
right, rows 1-32 top to bottom. Hole (1,1) is the top-left matrix hole."""

import math, os

P = 24.0
MX, MY = 150.0, 96.0

def X(c): return MX + (c-1)*P
def Y(r): return MY + (r-1)*P

ONEW = "#C2622A"   # 1-wire / power distribution (orange)
I2C  = "#4A7FB5"   # incoming link from the Pi board (blue)
ACC  = "#A85F22"

out = []
W_, H_ = 660, 1030
out.append(f'<svg viewBox="0 0 {W_} {H_}" role="img" aria-label="Hole-by-hole placement map of the RPI-BC extension board, component side. Columns 1 to 14 run left to right, rows 1 to 32 top to bottom. The 18-position terminal area sits at columns 13 and 14, rows 12 to 20; the nine column-13 positions carry three 3-pin probe headers with access pads at columns 10 and 11. The DS2482 sits in a DIP-8 socket at columns 5 to 8, rows 12 to 15. The 3-pin push terminal for the 1-wire trunk sits at columns 4 to 6, row 18." xmlns="http://www.w3.org/2000/svg" style="max-width:100%;height:auto">')
out.append('<defs>'
  '<pattern id="hx2" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
  f'<line x1="0" y1="0" x2="0" y2="9" stroke="{ACC}" stroke-width="1.4" opacity=".55"/></pattern>'
  '</defs>')
out.append('<g font-family="IBM Plex Mono, ui-monospace, monospace" font-size="10" fill="currentColor">')
out.append(f'<text x="{MX-130}" y="22" font-size="13" font-weight="600">EXT BOARD, COMPONENT SIDE — hole grid (column,row)</text>')
out.append(f'<text x="{MX-130}" y="38" font-size="10" opacity=".8">TOP view of drawing 00913308/02 · header side = the connector side of the board</text>')

bx0, bx1 = X(1)-28, X(14)+24
by0, by1 = Y(1)-34, Y(32)+24
out.append(f'<rect x="{bx0:.0f}" y="{by0:.0f}" width="{bx1-bx0:.0f}" height="{by1-by0:.0f}" rx="4" fill="none" stroke="currentColor" stroke-width="2"/>')

for c in range(1,15):
    out.append(f'<text x="{X(c):.0f}" y="{by0-6:.0f}" text-anchor="middle" font-size="8.5" opacity=".75">{c}</text>')
for r in range(1,33):
    out.append(f'<text x="{bx0-6:.0f}" y="{Y(r)+3:.0f}" text-anchor="end" font-size="8.5" opacity=".75">{r}</text>')
    out.append(f'<text x="{bx1+8:.0f}" y="{Y(r)+3:.0f}" font-size="8.5" opacity=".75">{r}</text>')

# keep-outs
def hrect(x0,y0,x1,y1):
    out.append(f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1-x0:.0f}" height="{y1-y0:.0f}" fill="url(#hx2)" stroke="{ACC}" stroke-width="1.4"/>')
hrect(bx0+2, Y(7)-P/2, bx1-2, Y(8)+P/2)
hrect(bx0+2, Y(25)+P/4, bx1-2, Y(27)+P/4)
out.append(f'<text x="{X(2):.0f}" y="{Y(7)-P/2-4:.0f}" font-size="9" fill="{ACC}">keep-out band — rows 7–8, full width</text>')
out.append(f'<text x="{X(2):.0f}" y="{Y(27)+P/4+12:.0f}" font-size="9" fill="{ACC}">keep-out band — rows 26–27 (edges graze 25), full width</text>')
# right-edge margin strip (no holes there)
hrect(bx1-8, Y(9), bx1-2, Y(25))

# hole occupancy
def exists(c,r):
    if c==12 and 10<=r<=22: return False
    if c in (13,14) and r in (10,11,21,22): return False
    return True
for r in range(1,33):
    for c in range(1,15):
        if not exists(c,r): continue
        if c in (10,11) and 12<=r<=20:
            out.append(f'<circle cx="{X(c):.0f}" cy="{Y(r):.0f}" r="3.4" fill="{ONEW}" opacity=".5"/>')
        else:
            out.append(f'<circle cx="{X(c):.0f}" cy="{Y(r):.0f}" r="2.6" fill="currentColor" opacity=".22"/>')

# terminal area: col 13 pins (used) + col 14 pins (unused) + fan lines to access pads
for r in range(12,21):
    out.append(f'<rect x="{X(13)-3.5:.0f}" y="{Y(r)-3.5:.0f}" width="7" height="7" fill="{ACC}"/>')
    out.append(f'<rect x="{X(14)-3.5:.0f}" y="{Y(r)-3.5:.0f}" width="7" height="7" fill="none" stroke="currentColor" stroke-width="1.1" opacity=".55"/>')
    out.append(f'<line x1="{X(13)-5:.0f}" y1="{Y(r):.0f}" x2="{X(11)+5:.0f}" y2="{Y(r):.0f}" stroke="{ACC}" stroke-width="1" opacity=".7"/>')
    out.append(f'<line x1="{X(11):.0f}" y1="{Y(r):.0f}" x2="{X(10):.0f}" y2="{Y(r):.0f}" stroke="{ACC}" stroke-width="1" opacity=".7"/>')
# header outlines around col-13 groups
for j,(r0,name) in enumerate(((12,'H1'),(15,'H2'),(18,'H3'))):
    out.append(f'<rect x="{X(13)-11:.0f}" y="{Y(r0)-11:.0f}" width="22" height="{2*P+22:.0f}" rx="3" fill="none" stroke="{ACC}" stroke-width="1.6"/>')
    out.append(f'<text x="{X(13):.0f}" y="{Y(r0)+P/2+3:.0f}" text-anchor="middle" font-size="8" font-weight="700" fill="{ACC}">{name}</text>')


# col-14 access pad groups (top/bottom), lightly marked
for (c,r) in ((11,8),(11,9),(12,8),(12,9),(13,8),(13,9),(14,8),(14,9),(10,10),(11,10),
              (11,23),(11,24),(12,23),(12,24),(13,23),(13,24),(14,23),(14,24),(10,22),(11,22)):
    out.append(f'<circle cx="{X(c):.0f}" cy="{Y(r):.0f}" r="4.2" fill="none" stroke="currentColor" stroke-width="1" opacity=".45"/>')
out.append(f'<text x="{X(9)-4:.0f}" y="{Y(9)+3:.0f}" text-anchor="end" font-size="8" opacity=".7">col-14 access pads →</text>')
out.append(f'<text x="{X(11):.0f}" y="{Y(21)+10:.0f}" text-anchor="middle" font-size="8" fill="{ACC}">each header: VCC · DATA · GND, top→bottom</text>')

# DS2482 socket: vertical DIP-8, cols 5-8, rows 12-15, notch DOWN, pin1 at (8,15)
x0,x1 = X(5)-P/2+4, X(8)+P/2-4
y0,y1 = Y(12)-P/2+4, Y(15)+P/2-4
out.append(f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1-x0:.0f}" height="{y1-y0:.0f}" rx="3" fill="none" stroke="currentColor" stroke-width="1.7"/>')
out.append(f'<path d="M{(x0+x1)/2-8:.0f},{y1:.0f} a8,8 0 0,0 16,0" fill="none" stroke="currentColor" stroke-width="1.7"/>')
out.append(f'<text x="{(x0+x1)/2:.0f}" y="{(y0+y1)/2-2:.0f}" text-anchor="middle" font-size="9.5" font-weight="600">DS2482</text>')
out.append(f'<text x="{(x0+x1)/2:.0f}" y="{(y0+y1)/2+11:.0f}" text-anchor="middle" font-size="8">notch DOWN</text>')
lpin = {12:'SDA',13:'PCTLZ',14:'AD1',15:'AD0'}
rpin = {12:'SCL',13:'GND',14:'IO',15:'VCC'}
for r,l in lpin.items():
    out.append(f'<rect x="{X(5)-3:.0f}" y="{Y(r)-4:.0f}" width="6" height="8" fill="currentColor"/>')
    out.append(f'<text x="{X(5)-7:.0f}" y="{Y(r)+3:.0f}" text-anchor="end" font-size="7.5">{l}</text>')
for r,l in rpin.items():
    out.append(f'<rect x="{X(8)-3:.0f}" y="{Y(r)-4:.0f}" width="6" height="8" fill="currentColor"/>')
    out.append(f'<text x="{X(8)+8:.0f}" y="{Y(r)+3:.0f}" font-size="7.5">{l}</text>')
out.append(f'<circle cx="{X(8)+9:.0f}" cy="{Y(15)+9:.0f}" r="2.2" fill="currentColor"/>')

# push terminal: cols 4-6, row 18
tx0,tx1 = X(4)-14, X(6)+14
out.append(f'<rect x="{tx0:.0f}" y="{Y(18)-16:.0f}" width="{tx1-tx0:.0f}" height="32" rx="3" fill="none" stroke="{ACC}" stroke-width="1.8"/>')
for c,l in ((4,'V'),(5,'D'),(6,'G')):
    out.append(f'<circle cx="{X(c):.0f}" cy="{Y(18):.0f}" r="5" fill="none" stroke="{ACC}" stroke-width="1.4"/>')
    out.append(f'<text x="{X(c):.0f}" y="{Y(18)+2.5:.0f}" text-anchor="middle" font-size="7.5" fill="{ACC}">{l}</text>')
out.append(f'<text x="{(tx0+tx1)/2:.0f}" y="{Y(18)+28:.0f}" text-anchor="middle" font-size="9" font-weight="600" fill="{ACC}">trunk plugs in — VCC · DATA · GND</text>')

# capacitor between (11,12) and (11,14)
out.append(f'<polyline points="{X(11):.0f},{Y(12):.0f} {X(12):.0f},{Y(12)+8:.0f} {X(12):.0f},{Y(14)-8:.0f} {X(11):.0f},{Y(14):.0f}" fill="none" stroke="{ONEW}" stroke-width="1.3"/>')
out.append(f'<rect x="{X(12)-5:.0f}" y="{(Y(12)+Y(14))/2-9:.0f}" width="10" height="18" rx="2" fill="none" stroke="{ONEW}" stroke-width="1.5"/>')
out.append(f'<text x="{X(12):.0f}" y="{Y(12)-4:.0f}" text-anchor="middle" font-size="7.5" fill="{ONEW}">100n</text>')

def wire(pts, col, wdt=1.5):
    d = ' '.join(f'{x:.0f},{y:.0f}' for x,y in pts)
    out.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{wdt}"/>')

# incoming link (blue), arrows from left edge
inc = [ ('3V3', (8,16)), ('SDA', (4,12)), ('SCL', (8,11)), ('GND', (10,14)) ]
iy = {'3V3': Y(16), 'SDA': Y(12)-6, 'SCL': Y(11)-6, 'GND': Y(14)-8}
wire([(bx0-26,Y(16)+10),(X(8)-6,Y(16)+10),(X(8),Y(16))], I2C)          # 3V3 in
out.append(f'<text x="{bx0-30:.0f}" y="{Y(16)+13:.0f}" text-anchor="end" font-size="8.5" fill="{I2C}">3V3 in</text>')
wire([(bx0-26,Y(12)-8),(X(4)-6,Y(12)-8),(X(4),Y(12))], I2C)            # SDA in
out.append(f'<text x="{bx0-30:.0f}" y="{Y(12)-5:.0f}" text-anchor="end" font-size="8.5" fill="{I2C}">SDA in</text>')
wire([(bx0-26,Y(11)-8),(X(8)-6,Y(11)-8),(X(8),Y(11))], I2C)            # SCL in
out.append(f'<text x="{bx0-30:.0f}" y="{Y(11)-5:.0f}" text-anchor="end" font-size="8.5" fill="{I2C}">SCL in</text>')
wire([(bx0-26,Y(10)+8),(X(10)-8,Y(10)+8),(X(10),Y(14)-8),(X(10),Y(14))], I2C)  # GND in
out.append(f'<text x="{bx0-30:.0f}" y="{Y(10)+11:.0f}" text-anchor="end" font-size="8.5" fill="{I2C}">GND in</text>')
# links (short blue)
wire([(X(8),Y(16)),(X(8),Y(15))], I2C)     # 3V3 link
wire([(X(4),Y(12)),(X(5),Y(12))], I2C)     # SDA link
wire([(X(8),Y(11)),(X(8),Y(12))], I2C)     # SCL link

# VCC chain (orange)
wire([(X(8)+4,Y(16)),(X(9),Y(16)-6),(X(9),Y(12)+8),(X(10),Y(12))], ONEW)   # W1 ring(8,16)->(10,12)
wire([(X(11),Y(12)),(X(11)+9,Y(12)+7),(X(11)+9,Y(15)-7),(X(10),Y(15))], ONEW) # W2 (11,12)->(10,15)
wire([(X(11),Y(15)),(X(11)+9,Y(15)+7),(X(11)+9,Y(18)-7),(X(10),Y(18))], ONEW) # W3 (11,15)->(10,18)
wire([(X(11),Y(18)),(X(11),Y(18)+9),(X(4)+6,Y(18)+9),(X(4)+3,Y(18)+4)], ONEW) # W4 ->ring(4,18)
# DATA chain
wire([(X(8),Y(14)),(X(10),Y(13))], ONEW)                                    # W5
wire([(X(11),Y(13)),(X(10)-9,Y(13)+8),(X(10)-9,Y(16)-8),(X(10),Y(16))], ONEW) # W6
wire([(X(11),Y(16)),(X(10)-9,Y(16)+8),(X(10)-9,Y(19)-8),(X(10),Y(19))], ONEW) # W7
wire([(X(11),Y(19)),(X(11)-4,Y(19)+6),(X(5)+6,Y(19)+6),(X(5)+3,Y(18)+5)], ONEW) # W8 ->ring(5,18)
# GND chain
wire([(X(11),Y(14)),(X(12)+4,Y(14)+8),(X(12)+4,Y(17)-8),(X(10),Y(17))], ONEW) # W9
wire([(X(11),Y(17)),(X(12)+4,Y(17)+8),(X(12)+4,Y(20)-8),(X(10),Y(20))], ONEW) # W10
wire([(X(11),Y(20)),(X(11)-4,Y(20)+7),(X(6)+6,Y(20)+7),(X(6)+3,Y(18)+5)], ONEW) # W11 ->ring(6,18)
wire([(X(8)+4,Y(13)),(X(10)-5,Y(13.8)),(X(10),Y(14))], ONEW)                # W12 GND pin tie
wire([(X(5),Y(14)),(X(5),Y(15))], ONEW)                                     # AD link (bare)
wire([(X(5)-4,Y(15)+4),(X(5)-4,Y(16)+6),(X(9)+4,Y(16)+6),(X(10)-4,Y(17)+3)], ONEW) # W13 AD->ring(10,17)

# legend
ly = Y(32)+38
out.append(f'<line x1="{MX-120}" y1="{ly:.0f}" x2="{MX-80}" y2="{ly:.0f}" stroke="{I2C}" stroke-width="1.5"/>')
out.append(f'<text x="{MX-72}" y="{ly+3:.0f}" font-size="9">link from the Pi board (4 wires, soldered)</text>')
out.append(f'<line x1="{MX+230}" y1="{ly:.0f}" x2="{MX+270}" y2="{ly:.0f}" stroke="{ONEW}" stroke-width="1.5"/>')
out.append(f'<text x="{MX+278}" y="{ly+3:.0f}" font-size="9">1-wire / power distribution</text>')
ly2 = ly+16
out.append(f'<circle cx="{MX-100}" cy="{ly2:.0f}" r="3.4" fill="{ONEW}" opacity=".5"/>')
out.append(f'<text x="{MX-90}" y="{ly2+3:.0f}" font-size="9">access pads of the col-13 header positions ((10,r) and (11,r))</text>')
ly3 = ly2+16
out.append(f'<rect x="{MX-104}" y="{ly3-6:.0f}" width="26" height="12" fill="url(#hx2)" stroke="{ACC}" stroke-width="1"/>')
out.append(f'<text x="{MX-70}" y="{ly3+3:.0f}" font-size="9">keep-out (solder side) · V/D/G = VCC / DATA / GND, top to bottom in each header</text>')
ly4 = ly3+16
out.append(f'<rect x="{MX-104}" y="{ly4-6:.0f}" width="7" height="7" fill="none" stroke="currentColor" stroke-width="1.1" opacity=".55"/>')
out.append(f'<text x="{MX-90}" y="{ly4+3:.0f}" font-size="9">column-14 header positions — unused in this build; ring out their pad groups before use</text>')

out.append('</g></svg>')
open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'ds18b20-ext-board-layout.svg'),'w').write('\n'.join(out)+'\n')
print('wrote', len(out), 'elements')
