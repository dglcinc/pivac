#!/usr/bin/env python3
"""Generate rpi-io-board-layout.svg (into this script's own directory) — grid-accurate placement figure for the
RPI-BC INT-PCB input board. Coordinates: col 1-23 left-to-right, row 1-30 top-to-bottom,
matching drawing 00914691/00 viewed from the component (TOP) side."""

P = 24.0            # pixels per 2.54 mm pitch
MX, MY = 190.0, 150.0  # svg position of hole (1,1)

def X(c): return MX + (c-1)*P
def Y(r): return MY + (r-1)*P

FIELD = "#C2622A"   # field-side wiring (orange)
PI    = "#4A7FB5"   # pi-side wiring (blue)
ACC   = "#A85F22"   # fixed-by-drawing accent

out = []
W_, H_ = 835, 1030
out.append(f'<svg viewBox="0 0 {W_} {H_}" role="img" aria-label="Hole-by-hole placement map of the RPI-BC input board, component side. Columns 1 to 23 run left to right, rows 1 to 30 top to bottom. The Pi header occupies columns 1 and 2; its access pads are columns 3 to 5. The four plugs sit above row 1 and their access pads are row 2, columns 6 to 21. Three optocoupler sockets sit at columns 7 to 14. Eleven resistors bridge the upper keep-out band from row 2 to row 7. Rails: 24V COM on row 3, Pi ground on rows 12 and 17, plus-14V down column 18. A five-position screw terminal at row 25, columns 3 to 7, links to the 1-wire board, fed by five component-side wires from the column-5 access pads." xmlns="http://www.w3.org/2000/svg" style="max-width:100%;height:auto">')
out.append(f'<rect x="0" y="0" width="{W_}" height="{H_}" fill="#ffffff"/>')
out.append('<defs>'
  '<pattern id="hx" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
  f'<line x1="0" y1="0" x2="0" y2="9" stroke="{ACC}" stroke-width="1.4" opacity=".55"/></pattern>'
  '</defs>')
out.append('<g font-family="IBM Plex Mono, ui-monospace, monospace" font-size="10" fill="#1a1a1a">')

out.append(f'<text x="{MX-18}" y="22" font-size="13" font-weight="600">COMPONENT SIDE — hole grid (column,row), TOP view of drawing 00914691/00</text>')


# board outline: edges relative to hole grid (measured from drawing)
bx0, bx1 = X(1)-0.6*P, X(23)+0.6*P
by0, by1 = Y(1)-3.4*P, Y(30)+1.0*P
out.append(f'<rect x="{bx0:.0f}" y="{by0:.0f}" width="{bx1-bx0:.0f}" height="{by1-by0:.0f}" rx="4" fill="none" stroke="#1a1a1a" stroke-width="2"/>')

# column numbers (top, below connector zone: put above board top edge) and row numbers (left+right)
for c in range(1,24):
    out.append(f'<text x="{X(c):.0f}" y="{by0-6:.0f}" text-anchor="middle" font-size="8.5" opacity=".75">{c}</text>')
for r in range(1,31):
    out.append(f'<text x="{bx0-6:.0f}" y="{Y(r)+3:.0f}" text-anchor="end" font-size="8.5" opacity=".75">{r}</text>')
    out.append(f'<text x="{bx1+8:.0f}" y="{Y(r)+3:.0f}" font-size="8.5" opacity=".75">{r}</text>')

# hole occupancy
def holes():
    hs=set()
    for r in range(1,21):
        hs.add((1,r)); hs.add((2,r))
    hs.add((22,1)); hs.add((23,1))
    for r in range(2,22):
        for c in range(3,24): hs.add((c,r))
    for r in range(22,27):
        for c in range(1,24): hs.add((c,r))
    for r in range(27,30):
        for c in range(2,24): hs.add((c,r))
    for c in range(3,24): hs.add((c,30))
    return hs
HS = holes()

# restricted areas first (under the dots)
def hrect(x0,y0,x1,y1):
    out.append(f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1-x0:.0f}" height="{y1-y0:.0f}" fill="url(#hx)" stroke="{ACC}" stroke-width="1.4"/>')
hrect(X(6)-P/2, Y(5)-P/2, bx1, Y(6)+P/2)          # upper band rows 5-6, cols 6..edge
hrect(X(3)-P/2, Y(22)-P/2, bx1, Y(23)+P/2)        # lower band rows 22-23, cols 3..edge
hrect(X(20)-P/2, Y(6)+P/2, X(20)+P/2, Y(22)-P/2)  # strip col 20 between the bands
for r in (8,12,16,20):                             # standoff bulges on the strip
    out.append(f'<circle cx="{X(20)-2:.0f}" cy="{Y(r):.0f}" r="{0.5*P:.0f}" fill="url(#hx)" stroke="{ACC}" stroke-width="1.2"/>')
out.append(f'<text x="{(X(6)+bx1)/2-40:.0f}" y="{Y(5)-P/2-4:.0f}" font-size="9" fill="{ACC}">keep-out band — rows 5–6, cols 6–23</text>')
out.append(f'<text x="{X(9):.0f}" y="{Y(23)+P/2+12:.0f}" font-size="9" fill="{ACC}">keep-out band — rows 22–23, cols 3–23</text>')
out.append(f'<text x="{X(20)+P/2+3:.0f}" y="{Y(14)+3:.0f}" font-size="9" fill="{ACC}" transform="rotate(90 {X(20)+P/2+3:.0f} {Y(14)+3:.0f})">keep-out — col 20, rows 5–23</text>')

# grid dots
for (c,r) in sorted(HS):
    if c in (3,4,5) and 2<=r<=21:
        out.append(f'<circle cx="{X(c):.0f}" cy="{Y(r):.0f}" r="3.4" fill="{PI}" opacity=".42"/>')
    elif r==2 and 6<=c<=21:
        out.append(f'<circle cx="{X(c):.0f}" cy="{Y(r):.0f}" r="3.4" fill="{FIELD}" opacity=".5"/>')
    else:
        out.append(f'<circle cx="{X(c):.0f}" cy="{Y(r):.0f}" r="2.6" fill="#1a1a1a" opacity=".22"/>')

# header pads cols 1-2 rows 1-20
for r in range(1,21):
    for c in (1,2):
        out.append(f'<circle cx="{X(c):.0f}" cy="{Y(r):.0f}" r="5" fill="none" stroke="#1a1a1a" stroke-width="1.4"/>')
out.append(f'<circle cx="{X(2):.0f}" cy="{Y(1):.0f}" r="5" fill="#1a1a1a"/>')
out.append(f'<text x="{X(1)-10:.0f}" y="{Y(1)-34:.0f}" font-size="8.5" font-weight="600">dark pad =</text>')
out.append(f'<text x="{X(1)-10:.0f}" y="{Y(1)-23:.0f}" font-size="8.5" font-weight="600">Pi pin 1</text>')
out.append(f'<text x="{X(1)-10:.0f}" y="{Y(1)-12:.0f}" font-size="8.5" font-weight="600">(confirmed)</text>')
# pin-pair labels every few rows


# Link to the 1-wire board: wires start on the column-5 access pads rows 2-6, run on the
# COMPONENT side (dashed) down the columns 3-4 face and over the lower band, end in the
# row-24 holes; bare one-hole links drop to the screw-terminal pins at row 25, columns 3-7.
LT = {2:'V', 3:'D', 4:'C', 5:'4', 6:'G'}
for r,l in LT.items():
    out.append(f'<circle cx="{X(5):.0f}" cy="{Y(r):.0f}" r="5.5" fill="none" stroke="{PI}" stroke-width="1.5"/>')
    out.append(f'<text x="{X(5):.0f}" y="{Y(r)+3:.0f}" text-anchor="middle" font-size="7.5" fill="{PI}">{l}</text>')
out.append(f'<text x="{MX-146}" y="{Y(2)+3:.0f}" font-size="8.5" font-weight="700" fill="{PI}">LINK PADS (5,2)–(5,6)</text>')
out.append(f'<text x="{MX-146}" y="{Y(3)+3:.0f}" font-size="8.5" fill="{PI}">5 wires, component</text>')
out.append(f'<text x="{MX-146}" y="{Y(4)+3:.0f}" font-size="8.5" fill="{PI}">side, to the terminal</text>')
out.append(f'<text x="{MX-146}" y="{Y(5)+3:.0f}" font-size="8.5" fill="{PI}">at row 25</text>')
out.append(f'<line x1="{MX-24}" y1="{Y(3):.0f}" x2="{X(5)-7:.0f}" y2="{Y(3):.0f}" stroke="{PI}" stroke-width=".8" opacity=".5" stroke-dasharray="2 2"/>')
for i in range(5):
    lane = X(3) - 10 + i*5
    y24 = Y(24) - 4 - i*3
    out.append(f'<polyline points="{X(5):.0f},{Y(2+i):.0f} {lane:.0f},{Y(2+i):.0f} {lane:.0f},{y24:.0f} {X(3+i):.0f},{y24:.0f} {X(3+i):.0f},{Y(24):.0f}" fill="none" stroke="{PI}" stroke-width="1.3" stroke-dasharray="5 4"/>')
    out.append(f'<line x1="{X(3+i):.0f}" y1="{Y(24):.0f}" x2="{X(3+i):.0f}" y2="{Y(25):.0f}" stroke="{PI}" stroke-width="1.6"/>')
out.append(f'<rect x="{X(3)-14:.0f}" y="{Y(25)-13:.0f}" width="{X(7)-X(3)+28:.0f}" height="30" rx="3" fill="none" stroke="{PI}" stroke-width="1.9"/>')
for i,l in enumerate(['V','D','C','4','G']):
    out.append(f'<circle cx="{X(3+i):.0f}" cy="{Y(25):.0f}" r="5.5" fill="none" stroke="{PI}" stroke-width="1.5"/>')
    out.append(f'<text x="{X(3+i):.0f}" y="{Y(25)+3:.0f}" text-anchor="middle" font-size="7.5" fill="{PI}">{l}</text>')
out.append(f'<text x="{MX-146}" y="{Y(25)-8:.0f}" font-size="8.5" font-weight="700" fill="{PI}">LINK → 1-WIRE BOARD</text>')
out.append(f'<text x="{MX-146}" y="{Y(25)+4:.0f}" font-size="8.5" fill="{PI}">screw terminal</text>')
out.append(f'<text x="{MX-146}" y="{Y(25)+16:.0f}" font-size="8.5" fill="{PI}">(3,25)–(7,25)</text>')
out.append(f'<line x1="{MX-24}" y1="{Y(25):.0f}" x2="{X(3)-16:.0f}" y2="{Y(25):.0f}" stroke="{PI}" stroke-width=".8" opacity=".5" stroke-dasharray="2 2"/>')

# connectors above row 1
PX = {i+1: MX + (px-221.0)/61.57*P for i,px in enumerate(
    [408.5,469,530,591,693.5,754,815,875.5,976,1037.5,1098,1159,1261.5,1322,1382.5,1443.5])}
cy = Y(1)-1.9*P
for j,ps in enumerate([(1,4),(5,8),(9,12),(13,16)]):
    x0, x1 = PX[ps[0]]-14, PX[ps[1]]+14
    out.append(f'<rect x="{x0:.0f}" y="{cy-16:.0f}" width="{x1-x0:.0f}" height="32" rx="3" fill="none" stroke="{ACC}" stroke-width="1.6"/>')
    out.append(f'<text x="{(x0+x1)/2:.0f}" y="{cy-22:.0f}" text-anchor="middle" font-size="10" font-weight="600" fill="{ACC}">J{j+1}</text>')
    for k,pn in enumerate(range(ps[0],ps[1]+1)):
        out.append(f'<circle cx="{PX[pn]:.0f}" cy="{cy:.0f}" r="5" fill="none" stroke="{ACC}" stroke-width="1.4"/>')
        out.append(f'<text x="{PX[pn]:.0f}" y="{cy+2.5:.0f}" text-anchor="middle" font-size="7.5" fill="{ACC}">{k+1}</text>')
        # fan-out line to (pn+5, 2)
        out.append(f'<line x1="{PX[pn]:.0f}" y1="{cy+6:.0f}" x2="{X(pn+5):.0f}" y2="{Y(2)-4:.0f}" stroke="{ACC}" stroke-width="1" opacity=".7"/>')
out.append(f'<text x="{PX[13]:.0f}" y="{cy-22:.0f}" text-anchor="middle" font-size="7.5" fill="{ACC}">+14V</text>')
out.append(f'<text x="{PX[16]:.0f}" y="{cy-22:.0f}" text-anchor="middle" font-size="7.5" fill="{ACC}">COM</text>')
for j,ps in enumerate([(4,),(8,),(12,)]):
    out.append(f'<text x="{PX[ps[0]]:.0f}" y="{cy-22:.0f}" text-anchor="middle" font-size="7.5" fill="{ACC}">COM</text>')

# DIP sockets
def dip(name, rtop, notch, chans):
    rbot = rtop+3
    x0,x1 = X(7)-P/2, X(14)+P/2
    y0,y1 = Y(rtop)-P/2+4, Y(rbot)+P/2-4
    out.append(f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1-x0:.0f}" height="{y1-y0:.0f}" rx="3" fill="none" stroke="#1a1a1a" stroke-width="1.7"/>')
    nx = x1 if notch=='right' else x0
    sweep = '0,0' # arc
    out.append(f'<path d="M{nx:.0f},{(y0+y1)/2-8:.0f} a8,8 0 0,{"1" if notch=="right" else "0"} 0,16" fill="none" stroke="#1a1a1a" stroke-width="1.7"/>')
    out.append(f'<text x="{(x0+x1)/2:.0f}" y="{(y0+y1)/2+4:.0f}" text-anchor="middle" font-size="10" font-weight="600">{name} · notch {notch.upper()}</text>')
    # pins + letters
    if notch=='right':
        toppins = {14:'A',13:'K',12:'A',11:'K',10:'A',9:'K',8:'A',7:'K'}
        botpins = {7:'E',8:'C',9:'E',10:'C',11:'E',12:'C',13:'E',14:'C'}
        p1c = 14
    else:
        toppins = {7:'C',8:'E',9:'C',10:'E',11:'C',12:'E',13:'C',14:'E'}
        botpins = {7:'A',8:'K',9:'A',10:'K',11:'A',12:'K',13:'A',14:'K'}
        p1c = 7
    for c,l in toppins.items():
        out.append(f'<rect x="{X(c)-3:.0f}" y="{Y(rtop)-4:.0f}" width="6" height="8" fill="#1a1a1a"/>')
        out.append(f'<text x="{X(c):.0f}" y="{Y(rtop)-8:.0f}" text-anchor="middle" font-size="8">{l}</text>')
    for c,l in botpins.items():
        out.append(f'<rect x="{X(c)-3:.0f}" y="{Y(rbot)-4:.0f}" width="6" height="8" fill="#1a1a1a"/>')
        out.append(f'<text x="{X(c):.0f}" y="{Y(rbot)+15:.0f}" text-anchor="middle" font-size="8">{l}</text>')
    # pin 1 marker
    r1 = rbot if notch=='right' else rbot  # pin1 is on LED row: notch right → LED row is top; pin1 col14 top... careful:
    # notch right: pin1 = top row, col14 ; notch left: pin1 = bottom row? for C (notch left) LED row is bottom, pin1 col7 bottom
    if notch=='right':
        out.append(f'<circle cx="{X(14)+9:.0f}" cy="{Y(rtop):.0f}" r="2.2" fill="#1a1a1a"/>')
    else:
        out.append(f'<circle cx="{X(7)-9:.0f}" cy="{Y(rbot):.0f}" r="2.2" fill="#1a1a1a"/>')

dip('IC-A', 8, 'right', None)
dip('IC-B', 13, 'right', None)
dip('IC-C', 18, 'left', None)

# resistors: (col_top, col_bottom) pairs; label
RES = [(6,6,'ZV'),(7,7,'DHW'),(8,8,'BLR'),(10,10,'CHIL'),(11,11,'BOS1'),(12,12,'BOS2'),
       (14,14,'DEHUM'),(15,15,'SP-A'),(16,16,'SP-B'),(19,19,'SP-C'),(20,21,'SP-D')]
for ct,cb,lab in RES:
    x0,y0 = X(ct), Y(2); x1,y1 = X(cb), Y(7)
    out.append(f'<line x1="{x0:.0f}" y1="{y0:.0f}" x2="{x1:.0f}" y2="{y1:.0f}" stroke="{FIELD}" stroke-width="1.4" stroke-dasharray="4 3"/>')
    mx,my = (x0+x1)/2,(y0+y1)/2
    import math
    ang = math.degrees(math.atan2(y1-y0,x1-x0))-90
    out.append(f'<rect x="{mx-5:.0f}" y="{my-11:.0f}" width="10" height="22" rx="2" fill="none" stroke="{FIELD}" stroke-width="1.5" transform="rotate({ang:.0f} {mx:.0f} {my:.0f})"/>')
    stag = 30 if (ct % 2 == 0) else 16
    out.append(f'<text x="{mx:.0f}" y="{my+stag:.0f}" text-anchor="middle" font-size="7" fill="{FIELD}">{lab}</text>')

# +14V: bridge (dashed, component side) col 18 rows 2..7, then solid rail rows 7..21
out.append(f'<line x1="{X(18):.0f}" y1="{Y(2):.0f}" x2="{X(18):.0f}" y2="{Y(7):.0f}" stroke="{FIELD}" stroke-width="2" stroke-dasharray="5 4"/>')
out.append(f'<line x1="{X(18):.0f}" y1="{Y(7):.0f}" x2="{X(18):.0f}" y2="{Y(21):.0f}" stroke="{FIELD}" stroke-width="2.6"/>')
out.append(f'<text x="{X(18)+6:.0f}" y="{Y(10)+3:.0f}" font-size="9" font-weight="600" fill="{FIELD}" transform="rotate(90 {X(18)+6:.0f} {Y(10):.0f})">+14 V rail (bare)</text>')
# feeders + anode hops
def wire(pts, col, dash=None, wdt=1.4):
    d = ' '.join(f'{x:.0f},{y:.0f}' for x,y in pts)
    da = f' stroke-dasharray="{dash}"' if dash else ''
    out.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{wdt}"{da}/>')
wire([(X(18),Y(8)),(X(14),Y(8))], FIELD)
wire([(X(18),Y(13)),(X(14),Y(13))], FIELD)
wire([(X(18),Y(21)),(X(13),Y(21))], FIELD)
for row,cs in ((8,(14,12,10,8)),(13,(14,12,10,8)),(21,(13,11,9,7))):
    for a,b in zip(cs,cs[1:]):
        out.append(f'<path d="M{X(a):.0f},{Y(row):.0f} Q{(X(a)+X(b))/2:.0f},{Y(row)-10:.0f} {X(b):.0f},{Y(row):.0f}" fill="none" stroke="{FIELD}" stroke-width="1.2"/>')

# COM rail row 3, cols 9-21 + stubs to row 2
out.append(f'<line x1="{X(9):.0f}" y1="{Y(3):.0f}" x2="{X(21):.0f}" y2="{Y(3):.0f}" stroke="#1a1a1a" stroke-width="2.6"/>')
out.append(f'<text x="{X(9)+8:.0f}" y="{Y(3)-7:.0f}" font-size="9" font-weight="600">24V COM rail (bare) — stubs up at cols 9·13·17·21</text>')
for c in (9,13,17,21):
    out.append(f'<line x1="{X(c):.0f}" y1="{Y(3):.0f}" x2="{X(c):.0f}" y2="{Y(2):.0f}" stroke="#1a1a1a" stroke-width="1.6"/>')

# ground rails row 12 (cols 7-13) and row 17 (cols 7-14) + stubs
out.append(f'<line x1="{X(7):.0f}" y1="{Y(12):.0f}" x2="{X(13):.0f}" y2="{Y(12):.0f}" stroke="#1a1a1a" stroke-width="2.6"/>')
for c in (7,9,11,13):
    out.append(f'<line x1="{X(c):.0f}" y1="{Y(12):.0f}" x2="{X(c):.0f}" y2="{Y(11):.0f}" stroke="#1a1a1a" stroke-width="1.6"/>')
out.append(f'<line x1="{X(7):.0f}" y1="{Y(17):.0f}" x2="{X(14):.0f}" y2="{Y(17):.0f}" stroke="#1a1a1a" stroke-width="2.6"/>')
for c in (7,9,11,13):
    out.append(f'<line x1="{X(c):.0f}" y1="{Y(17):.0f}" x2="{X(c):.0f}" y2="{Y(16):.0f}" stroke="#1a1a1a" stroke-width="1.6"/>')
for c in (8,10,12,14):
    out.append(f'<line x1="{X(c):.0f}" y1="{Y(17):.0f}" x2="{X(c):.0f}" y2="{Y(18):.0f}" stroke="#1a1a1a" stroke-width="1.6"/>')
out.append(f'<text x="{X(14)+6:.0f}" y="{Y(12)+3:.0f}" font-size="9" font-weight="600">Pi GND rail A</text>')
out.append(f'<text x="{X(14)+22:.0f}" y="{Y(17)+3:.0f}" font-size="9" font-weight="600">Pi GND rail B·C</text>')
# ground jumpers
wire([(X(7),Y(12)),(X(4)+8,Y(12)),(X(4)+8,Y(11)+5),(X(4),Y(11))], PI)
wire([(X(7),Y(17)),(X(4)+8,Y(17)),(X(4)+8,Y(16)+5),(X(4),Y(16))], PI)

# field cathode links
wire([(X(6),Y(7)),(X(7),Y(8))], FIELD)
wire([(X(7),Y(7)),(X(9),Y(8))], FIELD)
wire([(X(8),Y(7)),(X(11),Y(8))], FIELD)
wire([(X(10),Y(7)),(X(13),Y(8))], FIELD)
wire([(X(14),Y(7)),(X(15)-3,Y(7)),(X(15)-3,Y(13)),(X(13),Y(13))], FIELD)   # DEHUM
wire([(X(12),Y(7)),(X(16)-3,Y(7)),(X(16)-3,Y(13)),(X(11),Y(13))], FIELD)   # BOS2
wire([(X(11),Y(7)),(X(17)-3,Y(7)),(X(17)-3,Y(13)),(X(9),Y(13))], FIELD)    # BOS1
wire([(X(15),Y(7)),(X(15)+3,Y(7)+3),(X(15)+3,Y(21)-6),(X(8),Y(21))], FIELD)   # SP-A -> K(8,21)
wire([(X(16),Y(7)),(X(16)+3,Y(7)+3),(X(16)+3,Y(21)-3),(X(10),Y(21))], FIELD)  # SP-B -> K(10,21)
wire([(X(19),Y(7)),(X(17)+3,Y(7)),(X(17)+3,Y(21)+3),(X(14),Y(21))], FIELD)    # SP-C -> K(14,21)
wire([(X(21),Y(7)),(X(21)+4,Y(7)+6),(X(21)+4,Y(21)-6),(X(12),Y(21))], FIELD)                        # SP-D -> K(12,21)

# pi-side collector runs — one dedicated lane each, no two share a street
# horizontal lanes are offsets below the named row; vertical lanes are offsets from the named col
wire([(X(8),Y(11)),(X(8),Y(11)+8),(X(6)-6,Y(11)+8),(X(6)-6,Y(7)),(X(5),Y(7))], PI)          # ZV
wire([(X(10),Y(11)),(X(10),Y(11)+15),(X(6)+2,Y(11)+15),(X(6)+2,Y(8)),(X(5),Y(8))], PI)      # DHW
wire([(X(12),Y(11)),(X(12),Y(12)+8),(X(6)+9,Y(12)+8),(X(6)+9,Y(9)),(X(5),Y(9))], PI)        # BLR
wire([(X(14),Y(11)),(X(14),Y(12)+13),(X(4),Y(12)+13),(X(4),Y(12))], PI)                     # CHIL
wire([(X(12),Y(16)),(X(12),Y(16)+7),(X(5),Y(16)+7),(X(5),Y(16))], PI)                       # BOS2
wire([(X(10),Y(16)),(X(10),Y(16)+13),(X(6)-6,Y(16)+13),(X(6)-6,Y(17)),(X(5),Y(17))], PI)    # BOS1
wire([(X(14),Y(16)),(X(14),Y(16)+19),(X(4),Y(16)+19),(X(4),Y(17))], PI)                     # DEHUM
wire([(X(13),Y(18)),(X(13),Y(17)+6),(X(5)+8,Y(17)+6),(X(5),Y(18))], PI)                     # SP-C
wire([(X(11),Y(18)),(X(11),Y(17)+11),(X(6)+2,Y(17)+11),(X(6)+2,Y(19)),(X(5),Y(19))], PI)    # SP-D
wire([(X(9),Y(18)),(X(9),Y(17)+16),(X(4)+2,Y(17)+16),(X(4)+2,Y(10)),(X(4),Y(10))], PI)      # SP-B
wire([(X(7),Y(18)),(X(7),Y(17)+21),(X(4)-6,Y(17)+21),(X(4)-6,Y(9)),(X(4),Y(9))], PI)        # SP-A

# landing-pad labels, top to bottom, with leader lines (pin 1 confirmed, so pin numbers are definitive)
LAND = [ (5,7,'11','ZV'), (5,8,'13','DHW'), (5,9,'15','BLR'), (4,9,'16','SP-A'),
         (4,10,'18','SP-B'), (4,11,'20','GND·A'), (4,12,'22','CHIL'),
         (5,16,'29','BOS2'), (4,16,'30','GND·B·C'), (5,17,'31','BOS1'),
         (4,17,'32','DEHUM'), (5,18,'33','SP-C'), (5,19,'35','SP-D') ]
lasty = 0
for c,r,pin,nm in LAND:
    ly_ = max(Y(r)+3, lasty+13)
    lasty = ly_
    out.append(f'<text x="{MX-146}" y="{ly_:.0f}" font-size="8.5" fill="{PI}">pin {pin} · {nm}</text>')
    out.append(f'<text x="{MX-74}" y="{ly_:.0f}" font-size="8.5" fill="{PI}" opacity=".8">({c},{r})</text>')
    out.append(f'<line x1="{MX-24}" y1="{ly_-3:.0f}" x2="{X(c)-6:.0f}" y2="{Y(r):.0f}" stroke="{PI}" stroke-width=".7" opacity=".45" stroke-dasharray="2 2"/>')
    out.append(f'<circle cx="{X(c):.0f}" cy="{Y(r):.0f}" r="4.6" fill="none" stroke="{PI}" stroke-width="1.2"/>')

# GPIO landing labels (left margin)
glabels = [ (5,7,'ZV pin11'), (5,8,'DHW pin13'), (5,9,'BLR pin15'), (4,12,'CHIL pin22'),
            (4,9,'SP pin16'), (4,10,'SP pin18'), (4,11,'GND pin20'), (4,16,'GND pin30'),
            (5,16,'BOS2 pin29'), (5,17,'BOS1 pin31'), (4,17,'DEHUM pin32'), (5,18,'SP pin33'),
            (5,19,'SP pin35'), (5,20,'✕ pin37 dead') ]
for c,r,t in glabels:
    pass  # labels placed in doc tables; figure keeps dots only

# dead pin marker
out.append(f'<text x="{X(5):.0f}" y="{Y(20)+4:.0f}" text-anchor="middle" font-size="11" font-weight="700" fill="{ACC}">✕</text>')

# legend
ly = Y(30)+2.2*P
out.append(f'<line x1="{MX-14}" y1="{ly:.0f}" x2="{MX+26}" y2="{ly:.0f}" stroke="#1a1a1a" stroke-width="2.6"/>')
out.append(f'<text x="{MX+34}" y="{ly+3:.0f}" font-size="9">bare rail (solder side)</text>')
out.append(f'<line x1="{MX+190}" y1="{ly:.0f}" x2="{MX+230}" y2="{ly:.0f}" stroke="{FIELD}" stroke-width="1.5"/>')
out.append(f'<text x="{MX+238}" y="{ly+3:.0f}" font-size="9">field wire (insulated)</text>')
out.append(f'<line x1="{MX+390}" y1="{ly:.0f}" x2="{MX+430}" y2="{ly:.0f}" stroke="{PI}" stroke-width="1.5"/>')
out.append(f'<text x="{MX+438}" y="{ly+3:.0f}" font-size="9">Pi wire (insulated)</text>')
ly2 = ly+18
out.append(f'<line x1="{MX-14}" y1="{ly2:.0f}" x2="{MX+26}" y2="{ly2:.0f}" stroke="{FIELD}" stroke-width="1.5" stroke-dasharray="5 4"/>')
out.append(f'<text x="{MX+34}" y="{ly2+3:.0f}" font-size="9">component-side bridge (resistor body or wire) over a keep-out band</text>')
ly3 = ly2+18
out.append(f'<circle cx="{MX-4}" cy="{ly3:.0f}" r="3.4" fill="{PI}" opacity=".42"/>')
out.append(f'<text x="{MX+8}" y="{ly3+3:.0f}" font-size="9">GPIO access pad (cols 3–5)</text>')
out.append(f'<circle cx="{MX+216}" cy="{ly3:.0f}" r="3.4" fill="{FIELD}" opacity=".5"/>')
out.append(f'<text x="{MX+228}" y="{ly3+3:.0f}" font-size="9">plug access pad (row 2)</text>')
out.append(f'<rect x="{MX+400}" y="{ly3-6:.0f}" width="26" height="12" fill="url(#hx)" stroke="{ACC}" stroke-width="1"/>')
out.append(f'<text x="{MX+434}" y="{ly3+3:.0f}" font-size="9" fill="{ACC}">keep-out (solder side faces the Pi)</text>')

ly4 = ly3+18
out.append(f'<text x="{MX-10}" y="{ly4+3:.0f}" font-size="11" font-weight="700" fill="{ACC}">✕</text>')
out.append(f'<text x="{MX+8}" y="{ly4+3:.0f}" font-size="9">hole (5,20) = Pi pin 37 (GPIO 26, dead) — never use</text>')
out.append(f'<text x="{MX-10}" y="{ly4+21:.0f}" font-size="9">header row k carries Pi pins 2k−1 (col 2) and 2k (col 1); even-pin access pads sit at (3,k+1)+(4,k+1), odd-pin at (5,k+1)</text>')
out.append(f'<text x="{MX-10}" y="{ly4+39:.0f}" font-size="9">each plug pin fans out on a board trace to its row-2 access pad (thin lines at top)</text>')
out.append(f'<text x="{MX-10}" y="{ly4+57:.0f}" font-size="9" fill="{PI}">link: (5,2)–(5,6) → 5 wires (component side) → terminal (3,25)–(7,25); V=3V3 · D=SDA · C=SCL · 4=GPIO4 rollback · G=GND</text>')
out.append('</g></svg>')
import os
open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'rpi-io-board-layout.svg'),'w').write('\n'.join(out)+'\n')
print('wrote', len(out), 'elements')
