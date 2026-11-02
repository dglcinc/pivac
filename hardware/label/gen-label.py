#!/usr/bin/env python3
"""The AirMaster label for the base of the Hammond 1593K, full size. Writes airmaster-label.svg, a one-label PDF for a
sticker maker, a Letter sheet of labels for paper, and PNG previews. Needs Chrome for the PDFs and PNGs.

Coordinates are millimetres from the box's centre, seen from outside the base with the top panel up, y up. The base
mirrors the board: a part at board x stands at label x = 28.5 - x. Hammond's model gives the flat face as +/-28.67 by
+/-30.13 and the cover-screw recesses as 6 mm circles at (+/-25, 7.33). Every pointer and pin letter sits at its part's
true position, so the label also works as a drilling and notch check."""
import os, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HW, HH = 28.0, 29.5                # label half width and height
SY, NH, NX = 7.33, 3.7, 21.3       # screw height, notch half height, notch inner x
INK, GREY = "#111111", "#777777"
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"
LEDS = (("PWR", 1.5, "#18a848"), ("FAN", -2.5, "#e8b400"), ("Y1", -6.5, "#1f5fd8"), ("Y2", -10.5, "#1f5fd8"),
        ("W1", -14.5, "#d8261c"), ("W2", -18.5, "#d8261c"))

def X(x): return x + HW
def Y(y): return HH - y

def text(x, y, s, size, weight="normal", anchor="middle", fill=INK):
    return f'<text x="{X(x):.2f}" y="{Y(y):.2f}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}" font-family="{FONT}">{s}</text>'

def tri(x, y, d):
    s = 0.9
    p = {"up": [(x - s, y - 1.3), (x + s, y - 1.3), (x, y)], "down": [(x - s, y + 1.3), (x + s, y + 1.3), (x, y)],
         "right": [(x - 1.3, y - s), (x - 1.3, y + s), (x, y)]}[d]
    return '<polygon points="%s" fill="%s"/>' % (" ".join(f"{X(a):.2f},{Y(b):.2f}" for a, b in p), INK)

def outline():
    r, n = 3.0, 1.2
    top, bot = SY + NH, SY - NH
    p = [f"M {X(-HW + r):.2f} {Y(HH):.2f}", f"L {X(HW - r):.2f} {Y(HH):.2f}", f"A {r} {r} 0 0 1 {X(HW):.2f} {Y(HH - r):.2f}",
         f"L {X(HW):.2f} {Y(top):.2f}", f"L {X(NX + n):.2f} {Y(top):.2f}", f"A {n} {n} 0 0 0 {X(NX):.2f} {Y(top - n):.2f}",
         f"L {X(NX):.2f} {Y(bot + n):.2f}", f"A {n} {n} 0 0 0 {X(NX + n):.2f} {Y(bot):.2f}", f"L {X(HW):.2f} {Y(bot):.2f}",
         f"L {X(HW):.2f} {Y(-HH + r):.2f}", f"A {r} {r} 0 0 1 {X(HW - r):.2f} {Y(-HH):.2f}", f"L {X(-HW + r):.2f} {Y(-HH):.2f}",
         f"A {r} {r} 0 0 1 {X(-HW):.2f} {Y(-HH + r):.2f}", f"L {X(-HW):.2f} {Y(bot):.2f}", f"L {X(-NX - n):.2f} {Y(bot):.2f}",
         f"A {n} {n} 0 0 0 {X(-NX):.2f} {Y(bot + n):.2f}", f"L {X(-NX):.2f} {Y(top - n):.2f}", f"A {n} {n} 0 0 0 {X(-NX - n):.2f} {Y(top):.2f}",
         f"L {X(-HW):.2f} {Y(top):.2f}", f"L {X(-HW):.2f} {Y(HH - r):.2f}", f"A {r} {r} 0 0 1 {X(-HW + r):.2f} {Y(HH):.2f}", "Z"]
    return " ".join(p)

def monogram(cx, cy, scale):
    """hardware/dl-monogram.svg, ring and letters, without its white square."""
    return (f'<g transform="translate({X(cx):.2f} {Y(cy):.2f}) scale({scale})" fill="{INK}">'
            f'<circle r="4.425" fill="none" stroke="{INK}" stroke-width="0.35"/>'
            '<path d="M -2.35 1.01 L -2.35 -2.51 A 0.24 0.24 0 0 1 -2.11 -2.75 L -1.55 -2.75 A 2 2 0 0 1 -1.55 1.25 L -2.11 1.25 A 0.24 0.24 0 0 1 -2.35 1.01 Z M -1.55 -1.95 L -1.55 0.45 A 1.2 1.2 0 0 0 -1.55 -1.95 Z"/>'
            '<path d="M 0.8 -1.23 A 0.24 0.24 0 0 1 1.04 -1.47 L 1.36 -1.47 A 0.24 0.24 0 0 1 1.6 -1.23 L 1.6 1.59 A 0.14 0.14 0 0 0 1.74 1.73 L 2.793 1.73 A 0.24 0.24 0 0 1 3.033 1.97 L 3.033 2.29 A 0.24 0.24 0 0 1 2.793 2.53 L 1.04 2.53 A 0.24 0.24 0 0 1 0.8 2.29 Z"/></g>')

def art():
    a = [f'<path d="{outline()}" fill="#ffffff"/>']
    # title block
    a += [monogram(-5.5, 9.0, 1.45)]
    a += [text(-5.5, -6.2, "AirMaster", 8.4, "bold"), text(-5.5, -11.0, "for Unico SMART controller", 2.75)]
    # top panel: 24 VAC with its true pin positions, the Pico's port, the Unico's USB
    a += [tri(-19.0, HH - 0.25, "up"), text(-19.0, 24.9, "24 VAC", 2.5, "bold"), text(-20.91, 22.2, "R", 2.2), text(-17.09, 22.2, "C", 2.2)]
    a += [tri(0, HH - 0.25, "up"), text(0, 24.9, "PROG", 2.5, "bold"), text(0, 22.2, "24 VAC off", 2.0)]
    a += [tri(19.8, HH - 0.25, "up"), text(19.8, 24.9, "UNICO", 2.5, "bold"), text(19.8, 22.2, "USB", 2.2)]
    # bottom panel: sensor plugs, pin letters at the true 2.5 mm pitch
    a += [tri(-20.0, -HH + 0.25, "down"), text(-20.0, -22.9, "AIR NTC", 2.5, "bold")]
    for x, s in ((-23.75, "S"), (-21.25, "&#8211;"), (-18.75, "R"), (-16.25, "&#8211;")):
        a.append(text(x, -25.8, s, 2.2))
    a += [tri(18.9, -HH + 0.25, "down"), text(18.9, -22.9, "1-WIRE", 2.5, "bold")]
    for x, s in ((16.4, "V"), (18.9, "D"), (21.4, "G")):
        a.append(text(x, -25.8, s, 2.2))
    # LEDs on the side wall
    for name, y, col in LEDS:
        a.append(tri(HW - 0.25, y, "right"))
        a.append(f'<circle cx="{X(24.4):.2f}" cy="{Y(y):.2f}" r="1.05" fill="{col}"/>')
        a.append(text(22.5, y - 0.8, name, 2.3, "bold", "end"))
    return "\n".join(a)

def svg(cut=True):
    w, h = 2 * HW, 2 * HH
    c = f'<path d="{outline()}" fill="none" stroke="{GREY}" stroke-width="0.1"/>' if cut else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">{art()}{c}</svg>'

def chrome(html, pdf=None, png=None, size=None):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
    args = [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--force-device-scale-factor=4"]
    if pdf:
        args.append("--print-to-pdf=" + pdf)
    if png:
        args += ["--screenshot=" + png, "--window-size=%d,%d" % size]
    subprocess.run(args + ["file://" + f.name], check=True, capture_output=True, timeout=120)
    os.unlink(f.name)

def page(w, h, body):
    return f'<!doctype html><html><head><style>@page{{size:{w} {h};margin:0}}html,body{{margin:0;padding:0;background:#fff}}svg{{display:block}}</style></head><body>{body}</body></html>'

def main():
    w, h = 2 * HW, 2 * HH
    with open(os.path.join(HERE, "airmaster-label.svg"), "w") as f:
        f.write(svg())
    chrome(page(f"{w}mm", f"{h}mm", svg()), pdf=os.path.join(HERE, "airmaster-label.pdf"))
    # a Letter sheet: four labels and a scale check
    cells = "".join(f'<div style="position:absolute;left:{x}mm;top:{y}mm">{svg()}</div>' for x, y in ((22, 22), (22 + w + 20, 22), (22, 22 + h + 20), (22 + w + 20, 22 + h + 20)))
    bar = ('<div style="position:absolute;left:22mm;top:190mm;font:10pt Helvetica,Arial,sans-serif">'
           '<div style="width:50mm;height:2mm;background:#111"></div><div style="margin-top:2mm">Print at 100 %. This bar must measure 50 mm.</div>'
           '<div>Cut on the grey line, including the two side notches, which clear the cover screws.</div></div>')
    chrome(page("8.5in", "11in", f'<div style="position:relative;width:8.5in;height:11in">{cells}{bar}</div>'), pdf=os.path.join(HERE, "airmaster-label-letter.pdf"))
    k = 10    # px per mm in the previews
    big = f'<div style="padding:{k*2}px;background:#fff">' + svg().replace(f'width="{w}mm" height="{h}mm"', f'width="{w*k}" height="{h*k}"') + '</div>'
    chrome(page("auto", "auto", big), png=os.path.join(HERE, "airmaster-label.png"), size=(int(w * k + 4 * k), int(h * k + 4 * k)))
    # on the box: the base's outline, its cover screws, panels and the plugs
    bw, bh = 66.22, 67.22
    m = 14
    def bx(x): return (x + bw / 2 + m) * k
    def by(y): return (bh / 2 + m - y) * k
    box = [f'<rect x="{bx(-bw/2)}" y="{by(bh/2)}" width="{bw*k}" height="{bh*k}" rx="{5*k}" fill="#c9cbce" stroke="#888" stroke-width="2"/>']
    for sx in (-25, 25):
        box.append(f'<circle cx="{bx(sx)}" cy="{by(SY)}" r="{3*k}" fill="#8d8f92"/><circle cx="{bx(sx)}" cy="{by(SY)}" r="{1.5*k}" fill="#444"/>')
    box.append(f'<g transform="translate({bx(-HW)} {by(HH)}) scale({k})">{art()}</g>')
    for x, hw, col, ln in ((19.8, 7.25, "#3a3a3e", 9), (-19.0, 5.0, "#1e8a4c", 5), (0, 4.0, "#777", 0)):
        if ln: box.append(f'<rect x="{bx(x-hw)}" y="{by(bh/2+ln)}" width="{2*hw*k}" height="{ln*k}" fill="{col}"/>')
    for x, hw in ((-20.0, 5.75), (18.9, 4.5)):
        box.append(f'<rect x="{bx(x-hw)}" y="{by(-bh/2)}" width="{2*hw*k}" height="{7*k}" fill="#e8e6df" stroke="#999"/>')
    for name, y, col in LEDS:
        box.append(f'<circle cx="{bx(bw/2)+6}" cy="{by(y)}" r="{1.5*k/1.6}" fill="{col}"/>')
    W, H = int((bw + 2 * m) * k), int((bh + 2 * m) * k)
    chrome(page("auto", "auto", f'<svg width="{W}" height="{H}" style="background:#eef0f4">{"".join(box)}</svg>'), png=os.path.join(HERE, "airmaster-label-on-box.png"), size=(W, H))

if __name__ == "__main__":
    main()
