#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
"""Pour GND on the back of the routed Pico W carrier, behind the Pico only: the routed tracks join every GND
pad, the left side's tracks would cut a wider pour into islands, and the antenna's keep-out stays bare.
Run after route.py."""
import sys
import pcbnew
from pcbnew import FromMM, VECTOR2I
b = pcbnew.LoadBoard(sys.argv[1])
for old in [o for o in b.Zones() if not o.GetIsRuleArea()]:
    b.Remove(old)
z = pcbnew.ZONE(b)
z.SetNet(b.FindNet("GND")); z.SetLayer(pcbnew.B_Cu)
z.SetLocalClearance(FromMM(0.3)); z.SetMinThickness(FromMM(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
c = pcbnew.SHAPE_LINE_CHAIN()
for x, y in ((16.7, 0), (40, 0), (40, 43.7), (16.7, 43.7)):
    c.Append(VECTOR2I(FromMM(x), FromMM(y)))
c.SetClosed(True); z.Outline().AddOutline(c); b.Add(z)
b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(sys.argv[1])
