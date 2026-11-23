#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""Draw the two faces of the AirMaster carrier Rev D as SVG, for review: pad openings, part outlines, holes and the
silkscreen, each from KiCad's own plot of its layer so every legend shows where the fabricator will print it.

    <kicad python> ahpd-svg.py [board] [out folder]

Writes air-handler-pico-revd-board-front.svg and -back.svg; the back is drawn as seen from the back.
"""
import os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.expanduser("~/Applications/KiCad.app/Contents/MacOS/kicad-cli")
board = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "ahpd-board", "ahpd-board.kicad_pcb")
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "docs", "airmaster", "rev-d")

def layer(name, colour, mirror, tmp):
    """KiCad's plot of one layer, as SVG groups in the given colour, and the plot's view box."""
    f = os.path.join(tmp, name + ".svg")
    cmd = [CLI, "pcb", "export", "svg", "-o", f, "--layers", name + ",Edge.Cuts", "--mode-single", "--black-and-white",
           "--exclude-drawing-sheet", "--page-size-mode", "2", "--drill-shape-opt", "0"] + (["--mirror"] if mirror else []) + [board]
    subprocess.run(cmd, check=True, capture_output=True)
    s = open(f).read()
    box = re.search(r'viewBox="([^"]+)"', s).group(1)
    body = s[s.index(">", s.index("<desc")) + len("</desc>") + 1:] if False else s[s.index("</desc>") + 7:s.rindex("</svg>")]
    return body.replace("#000000", colour), box

FACES = (("front", False, (("F.Mask", "#d9b45a"), ("F.Fab", "#8fd0a8"), ("F.SilkS", "#ffffff"))),
         ("back", True, (("B.Mask", "#d9b45a"), ("B.SilkS", "#ffffff"))))
with tempfile.TemporaryDirectory() as tmp:
    # the fabrication layer gives each part's outline; its texts repeat the references and would read as legends
    plain = os.path.join(tmp, "board.kicad_pcb")
    import pcbnew
    b = pcbnew.LoadBoard(board)
    for fp in b.GetFootprints():
        for g in fp.GraphicalItems():
            if g.GetClass() == "PCB_TEXT" and g.GetLayer() == pcbnew.F_Fab:
                g.SetLayer(pcbnew.Cmts_User)
    b.Save(plain)
    board = plain
    for face, mirror, layers in FACES:
        groups, box = [], None
        for name, colour in layers:
            g, box = layer(name, colour, mirror, tmp)
            groups.append("<g>%s</g>" % g)
        x, y, w, h = (float(v) for v in box.split())
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="100%%" height="100%%" '
               'viewBox="%.3f %.3f %.3f %.3f">\n<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="#1f6b3f"/>\n%s\n</svg>\n'
               % (x - 2, y - 2, w + 4, h + 4, x, y, w, h, "\n".join(groups)))
        p = os.path.join(out, "air-handler-pico-revd-board-%s.svg" % face)
        open(p, "w").write(svg)
        print("wrote", os.path.relpath(p, HERE))
