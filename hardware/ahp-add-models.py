#!/usr/bin/env python3
"""Copy the routed Pico W carrier and add the render's 3D models: parts.wrl always, base.wrl with a box,
lid.wrl and plugs.wrl closed. Usage: ahp-add-models.py ROUTED.kicad_pcb MODELS none|open|closed OUT.kicad_pcb"""
import os, sys
import pcbnew
src, models, box, out = sys.argv[1:5]
b = pcbnew.LoadBoard(src)
m = pcbnew.FOOTPRINT(b); m.SetFPID(pcbnew.LIB_ID("pivac", "render"))
names = ["parts.wrl"] + (["base.wrl"] if box != "none" else []) + (["lid.wrl", "plugs.wrl"] if box == "closed" else [])
for n in names:
    md = pcbnew.FP_3DMODEL(); md.m_Filename = os.path.join(models, n)
    md.m_Scale = pcbnew.VECTOR3D(1 / 2.54, 1 / 2.54, 1 / 2.54)
    m.Models().push_back(md)
m.SetReference("MDL"); m.Reference().SetVisible(False); m.Value().SetVisible(False)
b.Add(m); m.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(28.5), pcbnew.FromMM(28.0)))
os.makedirs(os.path.dirname(out), exist_ok=True)
b.Save(out)
