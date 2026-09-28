#!/usr/bin/env python3
"""Lay Phoenix's STEP models of the PTSM headers on the rev C EXT board's footprints.

Two steps, because KiCad's Python has no STEP reader and the STEP reader has no pcbnew:

    <kicad python> hardware/fit-check.py --pads > /tmp/pads.json
    <python with cadquery-ocp> hardware/fit-check.py /tmp/pads.json

The first writes the pads of H1, H2, J3 and J4 from hardware/extc-board/extc-board.kicad_pcb.
The second reads the models in hardware/vendor/, finds each solder foot (the part of a lead or
anchor within 0.3 mm of the board) and each locating peg, puts them on the board the way the
generator places the footprint, and prints the margin of every foot inside its pad and the
play of every peg in its hole. It exits 1 if a foot leaves its pad or a peg misses its hole.

Each connector is checked against the model of the part fitted there. The HH0 header has no
locating pegs, so the holes its footprint carries for them stay empty under it; the same
footprint takes the HH header, which has them.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, "extc-board", "extc-board.kicad_pcb")
VENDOR = os.path.join(HERE, "vendor")
# the parts David is fitting (2026-09-27), each checked against its own model
MODEL = {"H1": "pxc_1808200_01_01_PTSM-0-5-3-HH0-2-5-SMD-R32_3D.stp",
         "H2": "pxc_1808200_01_01_PTSM-0-5-3-HH0-2-5-SMD-R32_3D.stp",
         "J3": "pxc_1778764_02_01_PTSM-0-5-2-HH-2-5-SMD-R32_3D.stp",
         "J4": "pxc_1778696_02_00_PTSM-0-5-2-HV-2-5-SMD-WH-R24_3D.stp"}
REFS = ("H1", "H2", "J3", "J4")


def write_pads():
    import pcbnew
    board = pcbnew.LoadBoard(BOARD)
    out = {}
    for ref in REFS:
        rows = []
        for p in board.FindFootprintByReference(ref).Pads():
            bb = p.GetBoundingBox()
            rows.append(dict(num=p.GetNumber(), npth=p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH,
                             x0=pcbnew.ToMM(bb.GetLeft()), x1=pcbnew.ToMM(bb.GetRight()),
                             y0=pcbnew.ToMM(bb.GetTop()), y1=pcbnew.ToMM(bb.GetBottom()),
                             cx=pcbnew.ToMM(p.GetPosition().x), cy=pcbnew.ToMM(p.GetPosition().y),
                             drill=pcbnew.ToMM(p.GetDrillSize().x)))
        out[ref] = rows
    json.dump(out, sys.stdout)


def solids(path):
    """Vertices of each solid's tessellation, as an (n, 3) array per solid."""
    import numpy as np
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS
    r = STEPControl_Reader()
    r.ReadFile(path)
    r.TransferRoots()
    out = []
    e = TopExp_Explorer(r.OneShape(), TopAbs_SOLID)
    while e.More():
        s = TopoDS.Solid(e.Current())
        BRepMesh_IncrementalMesh(s, 0.03, False, 0.3, True)
        pts = []
        f = TopExp_Explorer(s, TopAbs_FACE)
        while f.More():
            loc = TopLoc_Location()
            tri = BRep_Tool.Triangulation_s(TopoDS.Face(f.Current()), loc)
            if tri is not None:
                tr = loc.Transformation()
                for k in range(1, tri.NbNodes() + 1):
                    p = tri.Node(k).Transformed(tr)
                    pts.append((p.X(), p.Y(), p.Z()))
            f.Next()
        out.append(np.array(pts))
        e.Next()
    return out


def features(path):
    """(kind, end, x0, x1, y0, y1) for the feet and pegs at each end of a header, x measured
    from that end's outer pin. The housing is the largest solid; the leads are 0.6 wide."""
    S = solids(path)
    housing = max(range(len(S)), key=lambda i: len(S[i]))
    leads = sorted((s[:, 0].min() + s[:, 0].max()) / 2 for i, s in enumerate(S)
                   if i != housing and s[:, 0].max() - s[:, 0].min() < 1.0)
    first, last = leads[0], leads[-1]
    mid = (first + last) / 2
    out = []
    for i, s in enumerate(S):
        if i == housing:
            pegs = s[s[:, 2] < -0.3]
            for part in (pegs[pegs[:, 0] < mid], pegs[pegs[:, 0] > mid]):
                if len(part):
                    out.append(("peg", part))
            continue
        foot = s[s[:, 2] < 0.31]
        cx = (s[:, 0].min() + s[:, 0].max()) / 2
        if s[:, 0].max() - s[:, 0].min() < 1.0 and min(abs(cx - first), abs(cx - last)) > 0.4:
            continue                      # an inner lead of the 4-way model
        out.append(("foot", foot))
    rows = []
    for kind, pts in out:
        cx = (pts[:, 0].min() + pts[:, 0].max()) / 2
        end, ref = ("first", first) if cx < mid else ("last", last)
        rows.append((kind, end, pts[:, 0].min() - ref, pts[:, 0].max() - ref,
                     pts[:, 1].min(), pts[:, 1].max()))
    return rows


def check(ref, pads, name, model, place):
    sig = sorted((p for p in pads if p["num"].isdigit()), key=lambda p: int(p["num"]))
    ok = True
    print(ref, "-", name)
    if not any(k == "peg" for k, *_ in model):
        print("  no pegs on this part: the footprint's two peg holes stay empty under it")
    for kind, end, a, b, y0, y1 in model:
        pin = sig[0] if end == "first" else sig[-1]
        pts = [place(pin, x, y) for x in (a, b) for y in (y0, y1)]
        X0, X1 = min(p[0] for p in pts), max(p[0] for p in pts)
        Y0, Y1 = min(p[1] for p in pts), max(p[1] for p in pts)
        cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
        if kind == "peg":
            h = min((p for p in pads if p["npth"]), key=lambda p: (p["cx"] - cx) ** 2 + (p["cy"] - cy) ** 2)
            off = ((h["cx"] - cx) ** 2 + (h["cy"] - cy) ** 2) ** 0.5
            play = (h["drill"] - (X1 - X0)) / 2
            good = off <= play + 1e-6
            print("  peg at %s pin: %.2f peg in a %.2f hole, centres %.2f apart, play %.2f  %s"
                  % (end, X1 - X0, h["drill"], off, play, "ok" if good else "MISSES"))
        else:
            pd = min((p for p in pads if not p["npth"]),
                     key=lambda p: abs((p["x0"] + p["x1"]) / 2 - cx) + abs((p["y0"] + p["y1"]) / 2 - cy))
            m = (X0 - pd["x0"], pd["x1"] - X1, Y0 - pd["y0"], pd["y1"] - Y1)
            good = min(m) >= -1e-6
            print("  %s at %s pin: foot %.2f x %.2f on pad %s %.2f x %.2f, margins %.2f %.2f %.2f %.2f  %s"
                  % ("anchor" if pd["num"] == "MP" else "lead", end, X1 - X0, Y1 - Y0, pd["num"],
                     pd["x1"] - pd["x0"], pd["y1"] - pd["y0"], *m, "ok" if good else "OFF THE PAD"))
        ok = ok and good
    return ok


def main():
    pads = json.load(open(sys.argv[1]))
    part = {ref: (f.split("_3D")[0].split("_", 3)[-1], features(os.path.join(VENDOR, f)))
            for ref, f in MODEL.items()}
    j4x = max(p["x0"] for p in pads["J4"] if p["num"].isdigit()) + 2.0   # the lead-side face
    ok = True
    # H1, H2: entry face on the top edge, model y runs into the board
    for ref in ("H1", "H2"):
        ok &= check(ref, pads[ref], *part[ref], lambda pin, x, y: (pin["cx"] + x, y))
    # J3: turned 180 on the bottom edge
    ok &= check("J3", pads["J3"], *part["J3"], lambda pin, x, y: (pin["cx"] - x, 85.0 - y))
    # J4: pin row along y, the leads toward +x
    ok &= check("J4", pads["J4"], *part["J4"], lambda pin, x, y: (j4x - y, pin["cy"] + x))
    print("every foot on its pad, every peg in its hole" if ok else "FIT CHECK FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if "--pads" in sys.argv:
        write_pads()
    else:
        main()
