#!/usr/bin/env python3
"""Generate rpi-io-board-schematic.svg (into this script's own directory) — complete schematic
of the twelve-channel optoisolated input board. Each channel is drawn as two separate runs per
side, meeting at the package: field side, the +14 V rail to A and K through the 4.7 k to the
plug ("to relay"); Pi side, C to the BCM pin and E to the Pi ground rail. This matches the
physical build, where the resistor sits in the cathode leg (§5.2 of the build doc)."""

CHANNELS = [
    # (group header or None, plug pos, name, BCM label, y center)
    ('BOILER / DHW', 'J1.1', 'ZV',    'BCM 17', 118),
    (None,           'J1.2', 'DHW',   'BCM 27', 152),
    (None,           'J1.3', 'BLR',   'BCM 22', 187),
    ('COOLING',      'J2.1', 'CHIL',  'BCM 25', 222),
    (None,           'J2.2', 'BOS1',  'BCM 6',  256),
    (None,           'J2.3', 'BOS2',  'BCM 5',  290),
    ('MIXED',        'J3.1', 'DEHUM', 'BCM 12', 325),
    (None,           'J3.2', 'spare', 'BCM 23', 360),
    (None,           'J3.3', 'spare', 'BCM 24', 394),
    ('EXPANSION',    'J4.2', 'spare', 'BCM 13', 428),
    (None,           'J4.3', 'spare', 'BCM 19', 463),
    (None,           '—',    'built, unlanded', '—', 498),
]

INK = '#1a1a1a'
XRAIL, XLED, XPHOTO, XGRAIL = 132, 340, 500, 726

out = []
out.append('<svg viewBox="0 0 820 610" role="img" aria-label="Complete schematic of the '
           'twelve-channel optoisolated input board: on the field side a plus-14-volt rail '
           'runs to each LED anode, and each cathode returns through its 4.7-kilohm resistor '
           'to its plug position and relay; an isolation barrier separates them from twelve '
           'phototransistors whose collectors go to named GPIO pins and whose emitters share '
           'a Pi ground rail." xmlns="http://www.w3.org/2000/svg" '
           'style="max-width:100%;height:auto">')
out.append('<rect x="0" y="0" width="820" height="610" fill="#ffffff"/>')
out.append('<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
           'markerHeight="6" orient="auto-start-reverse">'
           f'<path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>')
out.append(f'<g fill="{INK}" font-family="IBM Plex Mono, ui-monospace, monospace" font-size="11">')

out.append('<text x="60" y="34" font-size="12" font-weight="600">FIELD SIDE — isolated, 14 V</text>')
out.append('<text x="500" y="34" font-size="12" font-weight="600">PI SIDE — 3.3 V logic</text>')
out.append(f'<line x1="420" y1="48" x2="420" y2="564" stroke="{INK}" stroke-width="1.5" stroke-dasharray="7 5" opacity=".85"/>')
out.append('<text x="420" y="62" text-anchor="middle" font-size="10.5" letter-spacing="1.5">ISOLATION BARRIER</text>')
out.append('<text x="420" y="598" text-anchor="middle" font-size="10.5" opacity=".8">no conductor crosses this line</text>')

# the two rails and their feeds
out.append(f'<line x1="{XRAIL}" y1="88" x2="{XRAIL}" y2="511" stroke="{INK}" stroke-width="2.5"/>')
out.append(f'<text x="{XRAIL}" y="80" text-anchor="middle" font-size="11.5" font-weight="600">+14 V rail</text>')
out.append(f'<line x1="46" y1="88" x2="{XRAIL-1}" y2="88" stroke="{INK}" stroke-width="1.6" marker-end="url(#ar)"/>')
out.append('<text x="44" y="84" text-anchor="end" font-size="10.5">J4.1</text>')
out.append(f'<line x1="{XGRAIL}" y1="88" x2="{XGRAIL}" y2="511" stroke="{INK}" stroke-width="2.5"/>')
out.append(f'<text x="{XGRAIL}" y="80" text-anchor="middle" font-size="11.5" font-weight="600">Pi GND rail</text>')
out.append(f'<line x1="{XGRAIL+1}" y1="88" x2="784" y2="88" stroke="{INK}" stroke-width="1.6" marker-end="url(#ar)"/>')
out.append('<text x="788" y="84" font-size="10.5">hdr</text>')

for i, (hdr, jpos, name, bcm, y) in enumerate(CHANNELS):
    dark = (jpos == '—')
    out.append('<g opacity=".42">' if dark else '<g>')
    if hdr:
        out.append(f'<text x="14" y="{y-13}" font-size="10" font-weight="600" letter-spacing=".8">{hdr}</text>')
    out.append(f'<text x="14" y="{y+4}" font-size="10.5">{jpos}</text>')
    out.append(f'<text x="60" y="{y+4}" font-size="11" font-weight="600">{name}</text>')

    # --- field side: two runs meeting at the LED ---
    # anode run: +14 V rail straight to A
    out.append(f'<line x1="{XRAIL}" y1="{y-9}" x2="{XLED}" y2="{y-9}" stroke="{INK}" stroke-width="1.2"/>')
    # the LED, vertical, A up / K down
    out.append(f'<polygon points="{XLED-7},{y-9} {XLED+7},{y-9} {XLED},{y}" fill="{INK}"/>')
    out.append(f'<line x1="{XLED-7}" y1="{y+2}" x2="{XLED+7}" y2="{y+2}" stroke="{INK}" stroke-width="1.8"/>')
    out.append(f'<line x1="{XLED}" y1="{y+2}" x2="{XLED}" y2="{y+9}" stroke="{INK}" stroke-width="1.2"/>')
    # cathode run: K through the 4.7 k to the plug position ("to relay")
    out.append(f'<line x1="{XLED}" y1="{y+9}" x2="296" y2="{y+9}" stroke="{INK}" stroke-width="1.2"/>')
    out.append(f'<rect x="256" y="{y+2.5}" width="40" height="13" rx="1.5" fill="none" stroke="{INK}" stroke-width="1.3"/>')
    out.append(f'<line x1="256" y1="{y+9}" x2="226" y2="{y+9}" stroke="{INK}" stroke-width="1.2" marker-end="url(#ar)"/>')
    out.append(f'<text x="220" y="{y+12}" text-anchor="end" font-size="9.5" opacity=".8">to relay</text>')
    if i == 0:
        out.append(f'<text x="276" y="{y+1}" text-anchor="middle" font-size="9">4.7 k</text>')
        out.append(f'<text x="352" y="{y-11}" font-size="10">A</text>')
        out.append(f'<text x="352" y="{y+13}" font-size="10">K</text>')
        out.append(f'<text x="370" y="{y+2}" font-size="10">LED</text>')

    # --- pi side: two runs meeting at the phototransistor ---
    out.append(f'<circle cx="{XPHOTO}" cy="{y}" r="11" fill="none" stroke="{INK}" stroke-width="1.3"/>')
    out.append(f'<line x1="{XPHOTO-4}" y1="{y-6}" x2="{XPHOTO-4}" y2="{y+6}" stroke="{INK}" stroke-width="1.6"/>')
    out.append(f'<line x1="{XPHOTO-4}" y1="{y-3}" x2="{XPHOTO+8}" y2="{y-8}" stroke="{INK}" stroke-width="1.1"/>')
    out.append(f'<line x1="{XPHOTO-4}" y1="{y+3}" x2="{XPHOTO+8}" y2="{y+8}" stroke="{INK}" stroke-width="1.1"/>')
    if i == 0:
        out.append(f'<text x="{XPHOTO}" y="{y-16}" text-anchor="middle" font-size="10">photo</text>')
    out.append(f'<line x1="{XPHOTO+9}" y1="{y-8}" x2="598" y2="{y-8}" stroke="{INK}" stroke-width="1.2" marker-end="url(#ar)"/>')
    out.append(f'<text x="604" y="{y-4}" font-size="10.5">{bcm}</text>')
    out.append(f'<line x1="{XPHOTO+9}" y1="{y+8}" x2="{XGRAIL}" y2="{y+8}" stroke="{INK}" stroke-width="1.2"/>')
    out.append('</g>')

# 24 V COM rail
out.append(f'<line x1="46" y1="558" x2="380" y2="558" stroke="{INK}" stroke-width="2.5"/>')
out.append('<text x="14" y="562" font-size="10.5">V−</text>')
out.append('<text x="60" y="549" font-size="11" font-weight="600">24 V COM rail — J1.4 · J2.4 · J3.4 · J4.4, and the supply return</text>')
for x, lab in ((150, 'J1.4'), (230, 'J2.4'), (310, 'J3.4'), (390, 'J4.4')):
    out.append(f'<line x1="{x}" y1="558" x2="{x}" y2="569" stroke="{INK}" stroke-width="1.3"/>')
    out.append(f'<text x="{x}" y="580" text-anchor="middle" font-size="9.5">{lab}</text>')

out.append('</g></svg>')

import os
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rpi-io-board-schematic.svg'),
     'w').write('\n'.join(out) + '\n')
print('wrote', len(out), 'elements')
