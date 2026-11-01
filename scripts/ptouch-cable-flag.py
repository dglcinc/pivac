#!/usr/bin/env python3
"""Print cable-flag labels on a Brother PT-E550W over USB (raster mode, no driver).

A cable flag is two identical text blocks with a blank wrap zone between them; folded round the cable the
two blocks face outward. Each block has two centred lines. Usage:

    ptouch-cable-flag.py [--gap MM] [--dry PNG] "line one" "line two" ["line one" "line two" ...]

Pairs of lines make one label each. --dry renders the first label to a PNG instead of printing.
Tape width and type come from the printer's status; 12, 18 and 24 mm laminated tapes are handled.
"""
import argparse, sys, time
from PIL import Image, ImageDraw, ImageFont

VID, PID = 0x04f9, 0x205f          # PT-E550W enumerates as PT-E500
DPI = 180
PX_PER_MM = DPI / 25.4
PINS = 128                         # print head
# printable pins per tape and the first pin used (PT-P750W / PT-E550W raster reference)
TAPE = {6: (32, 48), 9: (50, 39), 12: (70, 29), 18: (112, 8), 24: (128, 0)}
FONT = '/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf'


def mm(v): return int(round(v * PX_PER_MM))


def fit_font(text, max_h, max_w=None):
    size = max_h
    while size > 6:
        f = ImageFont.truetype(FONT, size)
        l, t, r, b = f.getbbox(text)
        if (b - t) <= max_h and (max_w is None or (r - l) <= max_w):
            return f
        size -= 1
    return ImageFont.truetype(FONT, 6)


def render(line1, line2, height_px, gap_mm, pad_mm=1.5, block_mm=None):
    """One label as a 1-bit image: block, gap, block. Returns PIL image (mode '1'), white background."""
    line_h = int(height_px * 0.46)
    f1 = fit_font(line1, line_h); f2 = fit_font(line2, line_h)
    w1 = f1.getbbox(line1)[2] - f1.getbbox(line1)[0]; w2 = f2.getbbox(line2)[2] - f2.getbbox(line2)[0]
    block_w = max(w1, w2) + 2 * mm(pad_mm)
    if block_mm: block_w = max(block_w, mm(block_mm))
    gap = mm(gap_mm)
    W = block_w * 2 + gap
    im = Image.new('1', (W, height_px), 1)
    d = ImageDraw.Draw(im)
    for x0 in (0, block_w + gap):
        for text, f, row in ((line1, f1, 0), (line2, f2, 1)):
            l, t, r, b = f.getbbox(text)
            tw, th = r - l, b - t
            y = int(height_px * (0.26 if row == 0 else 0.74) - th / 2 - t)
            d.text((x0 + (block_w - tw) // 2 - l, y), text, font=f, fill=0)
    return im


def rasterize(im, first_pin):
    """Columns of the image become raster lines; pixel (x, y) lands on pin first_pin + y."""
    W, H = im.size
    px = im.load()
    lines = []
    for x in range(W):
        bits = bytearray(PINS // 8)
        for y in range(H):
            if px[x, y] == 0:
                pin = first_pin + y
                bits[pin // 8] |= 0x80 >> (pin % 8)
        lines.append(bytes(bits))
    return lines


def job(labels_lines, width_mm, media_type, feed_mm=2.0):
    out = bytearray()
    out += b'\x00' * 100                       # invalidate
    out += b'\x1b@'                            # initialize
    out += b'\x1bia\x01'                       # raster mode
    n = len(labels_lines)
    for i, lines in enumerate(labels_lines):
        count = len(lines)
        out += b'\x1biz' + bytes([0x86, media_type, width_mm, 0]) + count.to_bytes(4, 'little') + bytes([0 if i == 0 else 1, 0])
        out += b'\x1biM\x40'                   # auto cut
        out += b'\x1biA\x01'                   # cut every label
        out += b'\x1biK\x0c'                   # half cut, no chain printing
        out += b'\x1bid' + mm(feed_mm).to_bytes(2, 'little')  # margin
        out += b'M\x00'                        # no compression
        for ln in lines:
            out += (b'Z' if not any(ln) else b'G' + (PINS // 8).to_bytes(2, 'little') + ln)
        out += b'\x1a' if i == n - 1 else b'\x0c'
    return bytes(out)


def printer():
    import usb.core, usb.util
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None: sys.exit('no PT-E550W on USB')
    usb.util.claim_interface(dev, 0)
    intf = dev.get_active_configuration()[(0, 0)]
    ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
    ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
    return dev, ep_out, ep_in


def status(ep_out, ep_in):
    ep_out.write(b'\x00' * 100); ep_out.write(b'\x1b@'); ep_out.write(b'\x1biS')
    time.sleep(0.3)
    st = bytes(ep_in.read(32, timeout=3000))
    return {'width': st[10], 'type': st[11], 'err': (st[8], st[9]), 'phase': st[19], 'status': st[18]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gap', type=float, default=14.0, help='wrap zone between the two blocks, mm')
    ap.add_argument('--block', type=float, default=None, help='minimum block length, mm')
    ap.add_argument('--dry', metavar='PNG', help='render the first label to this PNG and exit')
    ap.add_argument('--width', type=int, default=None, help='tape width mm for --dry (else from the printer)')
    ap.add_argument('text', nargs='+')
    a = ap.parse_args()
    if len(a.text) % 2: sys.exit('lines come in pairs')
    pairs = list(zip(a.text[0::2], a.text[1::2]))
    if a.dry:
        w = a.width or 12
        h, _ = TAPE[w]
        im = render(pairs[0][0], pairs[0][1], h, a.gap, block_mm=a.block)
        im.save(a.dry); print('%s: %d x %d px, %.0f mm long' % (a.dry, im.size[0], im.size[1], im.size[0] / PX_PER_MM)); return
    import usb.util
    dev, ep_out, ep_in = printer()
    try:
        st = status(ep_out, ep_in)
        if st['err'] != (0, 0) or st['width'] not in TAPE: sys.exit('printer status: %r' % st)
        h, first = TAPE[st['width']]
        labels = []
        for l1, l2 in pairs:
            im = render(l1, l2, h, a.gap, block_mm=a.block)
            labels.append(rasterize(im, first))
            print('%s | %s: %.0f mm' % (l1, l2, im.size[0] / PX_PER_MM))
        data = job(labels, st['width'], st['type'])
        for i in range(0, len(data), 4096):
            ep_out.write(data[i:i + 4096], timeout=10000)
        # wait for the printer to finish
        t0 = time.time()
        while time.time() - t0 < 60 + 10 * len(labels):
            try:
                r = bytes(ep_in.read(32, timeout=2000))
            except Exception:
                continue
            if len(r) == 32 and r[18] == 0x01: print('printed')
            if len(r) == 32 and r[18] == 0x02: sys.exit('printer error: %02x %02x' % (r[8], r[9]))
            if len(r) == 32 and r[18] == 0x06 and r[19] == 0x00: break   # phase change back to receiving
    finally:
        usb.util.release_interface(dev, 0)


if __name__ == '__main__':
    main()
