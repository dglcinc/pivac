#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""Paste the Pico W's castellated pads through their own copper, in a saved .kicad_pcb.

KiCad's RaspberryPi_Pico_W_SMD_HandSolder footprint prints paste through 40 separate 3.8 x 2.2 mm
apertures, wider than the 1.6 mm pads: at 2.54 mm pitch that leaves a 0.34 mm stencil web, and beside
the pads shortened for the screw heads the paste lands on solder mask. This drops those apertures and
puts F.Paste on U4's numbered SMD pads instead, so the stencil opening is the pad. Copper, mask and
routing are untouched. Plain text, because removing a pad through pcbnew's Python crashes the save.

    ahp-paste.py hardware/ahp-board/ahp-board.kicad_pcb
"""
import re, sys


def blocks(s, start, opener):
    """Yield (begin, end) of every balanced s-expression starting with `opener` from `start`."""
    i = s.find(opener, start)
    while i != -1:
        depth, j = 0, i
        while True:
            c = s[j]
            if c == '"':
                j = s.index('"', j + 1)
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        yield i, j + 1
        i = s.find(opener, j + 1)


def fix(s):
    for a, b in blocks(s, 0, "(footprint "):
        fp = s[a:b]
        if not re.search(r'\(property "Reference" "U4"', fp):
            continue
        out, last, dropped, pasted = [], 0, 0, 0
        for pa, pb in blocks(fp, 0, "(pad "):
            pad = fp[pa:pb]
            layers = re.search(r'\(layers ([^)]*)\)', pad).group(1).split()
            if pad.startswith('(pad "" ') and layers in (['"F.Paste"'], []):
                cut = fp.rfind("\n", last, pa)         # take the pad's own line indent with it
                out.append(fp[last:cut if cut != -1 else pa]); last = pb; dropped += 1
                continue
            if re.match(r'\(pad "\d+" smd ', pad) and '"F.Paste"' not in layers:
                pad = pad.replace('(layers "F.Cu" "F.Mask")', '(layers "F.Cu" "F.Paste" "F.Mask")', 1)
                pasted += 1
            out.append(fp[last:pa]); out.append(pad); last = pb
        out.append(fp[last:])
        return s[:a] + "".join(out) + s[b:], dropped, pasted
    raise SystemExit("no U4 footprint")


if __name__ == "__main__":
    path = sys.argv[1]
    s, dropped, pasted = fix(open(path).read())
    open(path, "w").write(s)
    print(f"U4: dropped {dropped} paste-only apertures, pasted {pasted} pads")
