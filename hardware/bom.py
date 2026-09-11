#!/usr/bin/env python3
"""Write a BOM CSV for each generated board from the board file itself.

    <kicad python> hardware/bom.py

Groups footprints by value and footprint, lists references, marks parts that are placed but not
fitted (DNP), and skips the prototyping fields and test pads.
"""
import collections
import csv
import os

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_PREFIX = ("PF", "TP")

for b in ("int", "ext"):
    path = os.path.join(HERE, f"{b}-board", f"{b}-board.kicad_pcb")
    board = pcbnew.LoadBoard(path)
    groups = collections.OrderedDict()
    for fp in sorted(board.GetFootprints(), key=lambda f: (f.GetReference()[0], int("".join(c for c in f.GetReference() if c.isdigit()) or 0))):
        ref = fp.GetReference()
        if ref.startswith(SKIP_PREFIX):
            continue
        key = (fp.GetValue(), fp.GetFPID().GetLibItemName().wx_str(), fp.IsDNP())
        groups.setdefault(key, []).append(ref)
    out = os.path.join(HERE, f"{b}-board", f"{b}-board-bom.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["qty", "value", "footprint", "references", "fitted"])
        for (value, fpname, dnp), refs in groups.items():
            w.writerow([len(refs), value, fpname, " ".join(refs), "no" if dnp else "yes"])
    print("wrote", out)
