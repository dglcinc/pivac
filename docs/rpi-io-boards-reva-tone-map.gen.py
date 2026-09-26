#!/usr/bin/env python3
"""Generate rpi-io-boards-reva-tone-map.svg: the rev A INT board as a meter reference.

Component side up, the four PTSM plugs along the top edge, the Pi header down the left
edge, the three LTV-847 sockets stacked U1 (top) to U3 (bottom) with their notches to the
left, exactly as the board sits on the bench. Every socket contact, plug position, header
pin, J8 pad and test point carries what it should tone to with the board OFF the Pi, the
chips OUT and the 24 VAC OFF. Not to scale; the topology and the pin order are the board's.

Nets are read from hardware/int-board/int-board.kicad_pcb (rev A as ordered from OSH Park).
"""
import os

VS, FLD, PI, GND, NONE, AC = "#B03030", "#C2622A", "#4A7FB5", "#555555", "#9AA0A6", "#7A4E9E"

# channel: (name, plug position, Pi header pin, BCM)
CH = {
    "U1": [("ZV", "J1.1", 11, 17), ("DHW", "J1.2", 13, 27), ("BLR", "J1.3", 15, 22), ("CHIL", "J2.1", 22, 25)],
    "U2": [("BOS1", "J2.2", 31, 6), ("BOS2", "J2.3", 29, 5), ("DEHUM", "J3.1", 32, 12), ("SCALA", "J3.2", 16, 23)],
    "U3": [("HPHEAT", "J3.3", 18, 24), ("SP-D", "J4.3", 35, 19), ("SP-C", "J8.1", 33, 13), ("SP-E", "J8.2", 36, 16)],
}
# Pi header nets on the board, from the layout file; pins absent here are open on the board.
HDR = {2: "5V", 3: "SDA", 4: "5V", 5: "SCL", 6: "GND", 7: "GPIO4", 9: "GND", 11: "ZV", 12: "GPIO18",
       13: "DHW", 14: "GND", 15: "BLR", 16: "SCALA", 17: "3V3", 18: "HPHEAT", 19: "GPIO10", 20: "GND",
       21: "GPIO9", 22: "CHIL", 23: "GPIO11", 24: "GPIO8", 26: "GPIO7", 29: "BOS2", 30: "GND", 31: "BOS1",
       32: "DEHUM", 33: "SP-C", 34: "GND", 35: "SP-D", 36: "SP-E", 38: "GPIO20", 40: "GPIO21"}
CHAN_PINS = {pin: (name, f"{u} pin {16-2*i}") for u, chs in CH.items() for i, (name, _, pin, _) in enumerate(chs)}

W, H = 1340, 1330
out = []


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=10, weight=400, fill="#1a1a1a", anchor="middle", opacity=1.0, rot=None):
    t = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    out.append(f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
               f'text-anchor="{anchor}" opacity="{opacity}"{t}>{esc(s)}</text>')


def pad(x, y, r=7, fill="#e8c84a", square=False):
    if square:
        out.append(f'<rect x="{x-r:.0f}" y="{y-r:.0f}" width="{2*r}" height="{2*r}" fill="{fill}" '
                   f'stroke="#1a1a1a" stroke-width="1"/>')
    else:
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{fill}" stroke="#1a1a1a" stroke-width="1"/>')
    out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r*0.4:.1f}" fill="#ffffff" stroke="#1a1a1a" stroke-width=".6"/>')


# ---------------------------------------------------------------- plugs J1-J4 (top edge)
def plugs():
    pitch, gap, x0, y = 56, 20, 330, 130
    names = {
        "J1": [("ZV", FLD), ("DHW", FLD), ("BLR", FLD), ("COM", GND)],
        "J2": [("CHIL", FLD), ("BOS1", FLD), ("BOS2", FLD), ("COM", GND)],
        "J3": [("DEHUM", FLD), ("SCALA", FLD), ("HPHEAT", FLD), ("COM", GND)],
        "J4": [("24VAC", AC), ("24VAC", AC), ("SP-D", FLD), ("COM", GND)],
    }
    kpin = {}
    for u, chs in CH.items():
        for i, (name, pos, _, _) in enumerate(chs):
            kpin[pos] = f"{u}.{2*i+2}"
    x = x0
    for j, (plug, poss) in enumerate(names.items()):
        out.append(f'<rect x="{x-30}" y="{y-44}" width="{3*pitch+60}" height="66" rx="3" '
                   f'fill="#f4f4f1" stroke="#1a1a1a" stroke-width="1.2"/>')
        text(x - 22, y - 30, plug, 12, 700, anchor="start")
        for n, (name, col) in enumerate(poss):
            px = x + n * pitch
            pad(px, y, 9, square=(n == 0))
            text(px, y - 16, f".{n+1}", 9, 700, opacity=.8)
            text(px, y + 40, name, 10.5, 700, col)
            pos = f"{plug}.{n+1}"
            if name == "COM":
                l2 = "tone TP2"
            elif name == "24VAC":
                l2 = "AC hot" if n == 0 else "AC return"
            else:
                l2 = f"12k→{kpin[pos]}"
            text(px, y + 53, l2, 8.6, 400, col)
            if plug == "J4" and n == 1:
                text(px, y + 65, "(no silk label)", 8, 400, AC, opacity=.9)
        x += 3 * pitch + 60 + gap


# ---------------------------------------------------------------- Pi header J5 (left edge)
def header():
    xe, xo, y0, pitch = 250, 290, 270, 32
    out.append(f'<rect x="{xe-22}" y="{y0-22}" width="{xo-xe+44}" height="{19*pitch+44}" rx="4" '
               f'fill="#f4f4f1" stroke="#1a1a1a" stroke-width="1.2"/>')
    text((xe+xo)/2, y0 - 32, "J5  Pi header (socket on the solder side)", 10, 700)
    for row in range(20):
        y = y0 + row * pitch
        for pin, x in ((2*row+2, xe), (2*row+1, xo)):
            net = HDR.get(pin)
            col = PI if pin in CHAN_PINS else (GND if net == "GND" else (NONE if net is None else "#1a1a1a"))
            pad(x, y, 8, square=(pin == 1))
            text(x, y + 3, str(pin), 7.5, 700, "#1a1a1a")
            label = net if net else "open"
            if net == "GND":
                label = "GND · tone TP3"
            elif pin in CHAN_PINS:
                label = f"{net} · tone {CHAN_PINS[pin][1]}"
            if x == xe:
                text(xe - 30, y + 3, label, 8.6, 700 if pin in CHAN_PINS else 400, col, anchor="end")
            else:
                text(xo + 14, y + 3, label, 8.6, 700 if pin in CHAN_PINS else 400, col, anchor="start")
    text(xe - 22, y0 + 19 * pitch + 40, "even outer · odd inner · 1 top",
         8.6, 400, anchor="start", opacity=.85)


# ---------------------------------------------------------------- sockets U1-U3
def socket(name, top):
    x0, pp = 460, 64
    bt, bb = top, top + 78
    chs = CH[name]
    out.append(f'<rect x="{x0}" y="{bt}" width="{8*pp}" height="{bb-bt}" rx="5" '
               f'fill="#f7f7f5" stroke="#1a1a1a" stroke-width="1.8"/>')
    out.append(f'<path d="M {x0} {(bt+bb)/2-13:.0f} A 13 13 0 0 1 {x0} {(bt+bb)/2+13:.0f} Z" '
               f'fill="#ffffff" stroke="#1a1a1a" stroke-width="1.8"/>')
    text(x0 + 40, (bt+bb)/2 + 4, "notch", 9, 700, opacity=.8)
    text(x0 + 4*pp, (bt+bb)/2 - 4, name, 14, 700)
    text(x0 + 4*pp, (bt+bb)/2 + 12, "LTV-847 · " + " · ".join(c[0] for c in chs), 9.5, 400, opacity=.7)
    for k in range(8):
        cx = x0 + (k + 0.5) * pp
        ch = chs[k // 2]
        name_, pos, pipin, bcm = ch
        # bottom row: pins 1-8 left to right, A then K per channel
        pin = k + 1
        if k % 2 == 0:
            leg, l1, l2, col = f"A{k//2+1}", "VS", "tone TP1", VS
        else:
            leg, l1, l2, col = f"K{k//2+1}", name_, f"~12 k to {pos}", FLD
        pad(cx, bb + 8, 6, "#d8d8d4", square=(pin == 1))
        text(cx, bb - 6, str(pin), 11, 700)
        text(cx, bb + 30, leg, 10, 700, col)
        text(cx, bb + 43, l1, 10, 700, col)
        text(cx, bb + 56, l2, 8.6, 400, col)
        # top row: pins 16 down to 9 left to right, C then E per channel
        pin = 16 - k
        if k % 2 == 0:
            leg, l1, l2, l2b, col = f"C{k//2+1}", name_, f"tone Pi {pipin}", f"BCM {bcm}", PI
            l3 = "no tone TP3"
        else:
            leg, l1, l2, l2b, col = f"E{k//2+1}", "Pi GND", "tone TP3", "", GND
            l3 = ""
        pad(cx, bt - 8, 6, "#d8d8d4")
        text(cx, bt + 16, str(pin), 11, 700)
        text(cx, bt - 22, l2, 8.6, 400, col)
        if l2b:
            text(cx, bt - 34, l2b, 8.6, 400, col)
        text(cx, bt - 47, l1, 10, 700, col)
        text(cx, bt - 60, leg, 10, 700, col)
        if l3:
            text(cx, bt - 73, l3, 8, 400, col, opacity=.85)


# ---------------------------------------------------------------- right edge and bottom
def rest():
    # J6 link connector, right edge
    x, y0 = 1240, 700
    out.append(f'<rect x="{x-26}" y="{y0-40}" width="52" height="5*34+30" rx="3" fill="#f4f4f1" '
               f'stroke="#1a1a1a" stroke-width="1.2"/>')
    text(x, y0 - 24, "J6", 12, 700)
    for n, (net, tgt) in enumerate([("3V3", "Pi 17"), ("SDA", "Pi 3"), ("SCL", "Pi 5"), ("GPIO4", "Pi 7"), ("GND", "TP3")]):
        y = y0 + n * 34
        pad(x, y, 8, square=(n == 0))
        text(x - 16, y + 3, f".{n+1} {net}", 8.6, 700, "#1a1a1a", anchor="end")
        text(x - 16, y + 14, f"tone {tgt}", 8, 400, "#1a1a1a", anchor="end", opacity=.85)
    # test points and J8
    tx, ty = 960, 1040
    for n, (nm, net, col) in enumerate([("TP1", "VS", VS), ("TP2", "COM", GND), ("TP3", "Pi GND", GND)]):
        pad(tx + n * 70, ty, 9)
        text(tx + n * 70, ty - 18, nm, 11, 700)
        text(tx + n * 70, ty + 26, net, 9.5, 700, col)
    text(tx + 70, ty + 44, "TP2 must NOT tone to TP3", 9, 700, VS)
    jx, jy = 960, 1130
    text(jx - 40, jy + 4, "J8", 12, 700, anchor="end")
    for n, (nm, tgt, col) in enumerate([("SP-C", "12k→U3.6", FLD), ("SP-E", "12k→U3.8", FLD), ("COM", "tone TP2", GND)]):
        pad(jx + n * 70, jy, 8, square=(n == 0))
        text(jx + n * 70, jy - 16, f".{n+1}", 9, 700, opacity=.8)
        text(jx + n * 70, jy + 24, nm, 10.5, 700, col)
        text(jx + n * 70, jy + 37, tgt, 8.4, 400, col)


def legend():
    x, y = 120, 1040
    out.append(f'<rect x="{x-10}" y="{y-24}" width="700" height="170" rx="4" fill="#f4f4f1" stroke="#1a1a1a" stroke-width="1"/>')
    text(x, y - 8, "Meter checks — board OFF the Pi, chips OUT, 24 VAC OFF", 11, 700, anchor="start")
    rows = [
        (VS, "A pins (odd, bottom row) tone TP1: the VS rail"),
        (FLD, "K pins (even, bottom row) read ~12 kΩ to their plug position; no tone to TP1 or TP3"),
        (GND, "E pins (odd, top row, from the right) tone TP3: Pi ground"),
        (PI, "C pins (even, top row) tone their Pi header pin only; never TP3, never the E pin beside them"),
        (GND, "every plug COM (position 4) tones TP2; TP2 never tones TP3"),
        (AC, "J4.1 and J4.2 are the transformer; neither is COM. Powered, chips out: ~35 V DC TP1 to TP2"),
        (NONE, "pin order: bottom row 1→8 left to right; top row 9→16 RIGHT to LEFT, so 16 is beside the notch"),
    ]
    for i, (col, s) in enumerate(rows):
        out.append(f'<rect x="{x}" y="{y+8+i*20}" width="11" height="11" fill="{col}"/>')
        text(x + 18, y + 17 + i * 20, s, 8.8, 400, anchor="start")


def build():
    out.append(f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Rev A INT board tone map: every socket pin, '
               f'plug position, header pin, J8 pad and test point labelled with what it should tone to on the bare board." '
               f'xmlns="http://www.w3.org/2000/svg" style="max-width:100%;height:auto">')
    out.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
    out.append('<g font-family="IBM Plex Mono, ui-monospace, monospace" fill="#1a1a1a">')
    text(40, 34, "pivac INT rev A — tone map, COMPONENT side up, plugs at the top, Pi header at the left", 16, 700, anchor="start")
    text(40, 54, "Not to scale. Pin order and nets are the board's (hardware/int-board/int-board.kicad_pcb). "
                 "Bare board: off the Pi, sockets empty, transformer off.", 9.5, 400, anchor="start", opacity=.8)
    # board outline
    out.append(f'<rect x="70" y="80" width="1220" height="1110" rx="10" fill="none" stroke="#2f5f3a" stroke-width="3"/>')
    plugs()
    header()
    socket("U1", 340)
    socket("U2", 600)
    socket("U3", 860)
    rest()
    legend()
    out.append('</g></svg>')
    d = os.path.dirname(os.path.abspath(__file__))
    f = os.path.join(d, "rpi-io-boards-reva-tone-map.svg")
    open(f, "w").write("\n".join(out) + "\n")
    print("wrote", os.path.basename(f), len(out), "elements")


build()
