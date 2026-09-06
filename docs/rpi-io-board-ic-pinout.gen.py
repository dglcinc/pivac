#!/usr/bin/env python3
"""Generate rpi-io-board-ic-pinout.svg — per-pin destination reference for the three
LTV-847 optocouplers on the RPI-BC INT-PCB input board. No traces: each pin carries only
its number, its leg letter, its hole, and what it connects to.

Two complete views. Screen position is derived from the hole coordinate, never hand-mirrored:
  component side (front)  x rises with column   (col 7 left  ... col 14 right)
  solder side    (back)   x falls with column   (col 14 left ... col 7  right)
Rows are unchanged by a left-right flip, so the smaller row number is the upper pin row in
both views. Hole labels stay in the document's canonical component-side numbering throughout.
Data source: docs/rpi-io-board-design.md sections 2.1, 5.1, 5.3 and 5.4.
"""
import os

PP   = 96.0                     # px per pin position
ML   = 62.0                     # left margin to the body's left edge
BW   = 8 * PP                   # body width
POWER, FIELD, PI, GND, NONE = "#B03030", "#C2622A", "#4A7FB5", "#555555", "#9AA0A6"

# (pin, leg, col, row, kind, line1, line2)
IC = {
 "IC-A": dict(notch_col=14, rows=(8, 11), sub="channels 1-4 = CHIL · BLR · DHW · ZV", pins=[
  ( 1,"A1",14, 8,"pwr","+14 V","feeder ← rail (18,8)"),
  ( 2,"K1",13, 8,"fld","CHIL","4k7 → J2.1"),
  ( 3,"A2",12, 8,"pwr","+14 V","hop ← pin 1"),
  ( 4,"K2",11, 8,"fld","BLR","4k7 → J1.3"),
  ( 5,"A3",10, 8,"pwr","+14 V","hop ← pin 3"),
  ( 6,"K3", 9, 8,"fld","DHW","4k7 → J1.2"),
  ( 7,"A4", 8, 8,"pwr","+14 V","hop ← pin 5"),
  ( 8,"K4", 7, 8,"fld","ZV","4k7 → J1.1"),
  ( 9,"E4", 7,11,"gnd","Pi GND","rail A (row 12)"),
  (10,"C4", 8,11,"pi","ZV","Pi 11 · BCM 17"),
  (11,"E3", 9,11,"gnd","Pi GND","rail A (row 12)"),
  (12,"C3",10,11,"pi","DHW","Pi 13 · BCM 27"),
  (13,"E2",11,11,"gnd","Pi GND","rail A (row 12)"),
  (14,"C2",12,11,"pi","BLR","Pi 15 · BCM 22"),
  (15,"E1",13,11,"gnd","Pi GND","rail A (row 12)"),
  (16,"C1",14,11,"pi","CHIL","Pi 22 · BCM 25")]),
 "IC-B": dict(notch_col=14, rows=(13, 16), sub="channels 1-3 = DEHUM · BOS2 · BOS1 · ch4 dark", pins=[
  ( 1,"A1",14,13,"pwr","+14 V","feeder ← rail (18,13)"),
  ( 2,"K1",13,13,"fld","DEHUM","4k7 → J3.1"),
  ( 3,"A2",12,13,"pwr","+14 V","hop ← pin 1"),
  ( 4,"K2",11,13,"fld","BOS2","4k7 → J2.3"),
  ( 5,"A3",10,13,"pwr","+14 V","hop ← pin 3"),
  ( 6,"K3", 9,13,"fld","BOS1","4k7 → J2.2"),
  ( 7,"A4", 8,13,"pwr","+14 V","hop ← pin 5"),
  ( 8,"K4", 7,13,"non","—","dark ch: no wire"),
  ( 9,"E4", 7,16,"gnd","Pi GND","rail B·C (row 17)"),
  (10,"C4", 8,16,"non","—","dark ch: no wire"),
  (11,"E3", 9,16,"gnd","Pi GND","rail B·C (row 17)"),
  (12,"C3",10,16,"pi","BOS1","Pi 31 · BCM 6"),
  (13,"E2",11,16,"gnd","Pi GND","rail B·C (row 17)"),
  (14,"C2",12,16,"pi","BOS2","Pi 29 · BCM 5"),
  (15,"E1",13,16,"gnd","Pi GND","rail B·C (row 17)"),
  (16,"C1",14,16,"pi","DEHUM","Pi 32 · BCM 12")]),
 "IC-C": dict(notch_col=7, rows=(18, 21), sub="spares SP-A · SP-B · SP-D · SP-C — NOTCH REVERSED", pins=[
  ( 1,"A1", 7,21,"pwr","+14 V","hop ← pin 3"),
  ( 2,"K1", 8,21,"fld","SP-A","4k7 → J3.2"),
  ( 3,"A2", 9,21,"pwr","+14 V","hop ← pin 5"),
  ( 4,"K2",10,21,"fld","SP-B","4k7 → J3.3"),
  ( 5,"A3",11,21,"pwr","+14 V","hop ← pin 7"),
  ( 6,"K3",12,21,"fld","SP-D","4k7 → J4.3"),
  ( 7,"A4",13,21,"pwr","+14 V","feeder ← rail (18,21)"),
  ( 8,"K4",14,21,"fld","SP-C","4k7 → J4.2"),
  ( 9,"E4",14,18,"gnd","Pi GND","rail B·C (row 17)"),
  (10,"C4",13,18,"pi","SP-C","Pi 33 · BCM 13"),
  (11,"E3",12,18,"gnd","Pi GND","rail B·C (row 17)"),
  (12,"C3",11,18,"pi","SP-D","Pi 35 · BCM 19"),
  (13,"E2",10,18,"gnd","Pi GND","rail B·C (row 17)"),
  (14,"C2", 9,18,"pi","SP-B","Pi 18 · BCM 24"),
  (15,"E1", 8,18,"gnd","Pi GND","rail B·C (row 17)"),
  (16,"C1", 7,18,"pi","SP-A","Pi 16 · BCM 23")]),
}
COL = {"pwr":POWER, "fld":FIELD, "pi":PI, "gnd":GND, "non":NONE}
LEG = {"A":"A  LED +", "K":"K  LED −", "C":"C  to Pi pin", "E":"E  to Pi GND"}

out = []

def esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def rank(col, view):
    """Screen slot 0..7 for a socket column, derived from the hole, never mirrored by hand."""
    return (col - 7) if view == "front" else (14 - col)

def draw_ic(name, base, view):
    d = IC[name]; r_top = min(d["rows"]); r_bot = max(d["rows"])
    bt, bb = base + 104, base + 176
    out.append(f'<rect x="{ML-30}" y="{base:.0f}" width="{BW+60}" height="20" rx="3" fill="#f0f0ee"/>')
    out.append(f'<text x="{ML-22}" y="{base+14:.0f}" font-size="13" font-weight="700">{name}'
               f'<tspan font-weight="400" font-size="10" opacity=".8">   rows {r_top} &amp; {r_bot}'
               f'  ·  {esc(d["sub"])}</tspan></text>')
    out.append(f'<rect x="{ML}" y="{bt}" width="{BW}" height="{bb-bt}" rx="5" '
               f'fill="#f7f7f5" stroke="#1a1a1a" stroke-width="1.8"/>')
    # notch at the package end whose column sits at that side of the screen
    nx = ML if rank(d["notch_col"], view) == 0 else ML + BW
    out.append(f'<path d="M {nx} {(bt+bb)/2-13:.0f} A 13 13 0 0 {1 if nx==ML else 0} {nx} {(bt+bb)/2+13:.0f} Z" '
               f'fill="#ffffff" stroke="#1a1a1a" stroke-width="1.8"/>')
    side = "left" if nx == ML else "right"
    out.append(f'<text x="{nx + (40 if side=="left" else -40):.0f}" y="{(bt+bb)/2+4:.0f}" '
               f'text-anchor="middle" font-size="9" font-weight="700" opacity=".8">notch</text>')
    for pin, leg, col, row, kind, l1, l2 in d["pins"]:
        cx = ML + (rank(col, view) + 0.5) * PP
        top = (row == r_top)
        c = COL[kind]
        y_stub_a, y_stub_b = (bt - 13, bt) if top else (bb, bb + 13)
        out.append(f'<rect x="{cx-6:.0f}" y="{y_stub_a:.0f}" width="12" height="13" '
                   f'fill="#d8d8d4" stroke="#1a1a1a" stroke-width="1"/>')
        out.append(f'<text x="{cx:.0f}" y="{(bt+16) if top else (bb-6):.0f}" text-anchor="middle" '
                   f'font-size="12" font-weight="700">{pin}</text>')
        ys = ([bt-20, bt-33, bt-47, bt-59] if top else [bb+25, bb+38, bb+52, bb+64])
        out.append(f'<text x="{cx:.0f}" y="{ys[0]:.0f}" text-anchor="middle" font-size="10.5" '
                   f'font-weight="700" fill="{c}">{esc(leg[0])}·{leg[1]}</text>')
        out.append(f'<text x="{cx:.0f}" y="{ys[1]:.0f}" text-anchor="middle" font-size="9" '
                   f'opacity=".72">({col},{row})</text>')
        out.append(f'<text x="{cx:.0f}" y="{ys[2]:.0f}" text-anchor="middle" font-size="10" '
                   f'font-weight="700" fill="{c}">{esc(l1)}</text>')
        out.append(f'<text x="{cx:.0f}" y="{ys[3]:.0f}" text-anchor="middle" font-size="8.6" '
                   f'fill="{c}" opacity=".95">{esc(l2)}</text>')
    if name == "IC-C":
        out.append(f'<text x="{ML+BW/2:.0f}" y="{(bt+bb)/2+4:.0f}" text-anchor="middle" '
                   f'font-size="10" font-weight="700" fill="{POWER}">IC-C IS ROTATED 180° '
                   f'— its C/E row faces the row-17 ground rail</text>')
    else:
        out.append(f'<text x="{ML+BW/2:.0f}" y="{(bt+bb)/2+4:.0f}" text-anchor="middle" '
                   f'font-size="10" opacity=".45">LTV-847 · 4 channels</text>')
    return base + 266

def draw_view(view, base):
    front = view == "front"
    title = "COMPONENT SIDE (front)" if front else "SOLDER SIDE (back)"
    how = ("chips facing you, Pi header columns on the LEFT, plug edge away from you"
           if front else
           "board flipped LEFT-to-RIGHT about its vertical axis, top edge still up; "
           "Pi header columns now on the RIGHT")
    order = ("columns run 7→14 left to right" if front
             else "columns run 14→7 left to right — every socket is mirrored")
    out.append(f'<rect x="{ML-30}" y="{base-30}" width="{BW+60}" height="26" rx="4" '
               f'fill="{"#eef3f8" if front else "#f6efe8"}"/>')
    out.append(f'<text x="{ML-20}" y="{base-12:.0f}" font-size="14" font-weight="700">{title}'
               f'<tspan font-weight="400" font-size="10">   — {esc(how)}</tspan></text>')
    out.append(f'<text x="{ML-20}" y="{base+6:.0f}" font-size="9.5" opacity=".8">{esc(order)}.</text>')
    b = base + 26
    for n in ("IC-A", "IC-B", "IC-C"):
        b = draw_ic(n, b, view)
    return b + 34

W_, H_ = 900, 1094

def build(view):
    global out
    out = []
    front = view == "front"
    out.append(f'<svg viewBox="0 0 {W_} {H_}" role="img" aria-label="Pin destination reference '
               f'for the three LTV-847 optocouplers on the RPI-BC input board, seen from the '
               f'{"component" if front else "solder"} side. Each of the sixteen pins per chip is '
               f'labelled with its pin number, leg letter, matrix hole and the point it connects '
               f'to. No traces are drawn." xmlns="http://www.w3.org/2000/svg" '
               f'style="max-width:100%;height:auto">')
    out.append(f'<rect x="0" y="0" width="{W_}" height="{H_}" fill="#ffffff"/>')
    out.append('<g font-family="IBM Plex Mono, ui-monospace, monospace" fill="#1a1a1a">')
    out.append(f'<text x="{ML-30}" y="26" font-size="15" font-weight="700">'
               f'RPi I/O board — optocoupler pin destinations, '
               f'{"COMPONENT side" if front else "SOLDER side"} (no traces)</text>')
    out.append(f'<text x="{ML-30}" y="43" font-size="9.5" opacity=".8">Three LTV-847 DIP-16. '
               f'{"Chips and sockets sit on this face; nothing is wired here."if front else "All rails and wires are on this face — this is the sheet to work from."}'
               f'  Sheet {"1" if front else "2"} of 2.</text>')
    y = draw_view(view, 90)
    ly = y + 6
    for i, (k, txt) in enumerate([("pwr","A = LED anode → +14 V rail (column 18)"),
                                  ("fld","K = LED cathode → 4.7 kΩ resistor → plug pin (field side)"),
                                  ("pi","C = collector → Pi GPIO access pad"),
                                  ("gnd","E = emitter → Pi ground rail"),
                                  ("non","unused (channel built, no plug position behind it)")]):
        out.append(f'<rect x="{ML-24}" y="{ly+i*16-8:.0f}" width="11" height="11" fill="{COL[k]}"/>')
        out.append(f'<text x="{ML-8}" y="{ly+i*16+1:.0f}" font-size="9.5">{esc(txt)}</text>')
    out.append(f'<text x="{ML-24}" y="{ly+5*16+10:.0f}" font-size="9.5" font-weight="700" '
               f'fill="{POWER}">IC-C is notch-opposite to IC-A and IC-B. Check its notch before '
               f'inserting the chip — reversing it is the likeliest assembly mistake on this board.'
               f'</text>')
    out.append(f'<text x="{ML-24}" y="{ly+5*16+28:.0f}" font-size="9.5"><tspan font-weight="700">'
               f'Pi nn</tspan> = physical header position (1-40).  <tspan font-weight="700">BCM nn'
               f'</tspan> = the Broadcom GPIO number — the same line, and the number config.yml '
               f'keys its inputs by (numbering: "bcm").</text>')
    out.append(f'<text x="{ML-24}" y="{ly+5*16+46:.0f}" font-size="9.5">Holes are the canonical '
               f'component-side (column,row) on both sheets, so a hole label means the same '
               f'physical hole in either view — only its screen position mirrors.</text>')
    out.append('</g></svg>')
    d = os.path.dirname(os.path.abspath(__file__))
    f = os.path.join(d, f'rpi-io-board-ic-pinout-{view}.svg')
    open(f, 'w').write('\n'.join(out) + '\n')
    print('wrote', os.path.basename(f), len(out), 'elements')

build("front")
build("back")
