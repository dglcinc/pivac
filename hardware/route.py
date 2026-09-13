#!/usr/bin/env python3
"""Autoroute a generated board with Freerouting and write the routed .kicad_pcb back.

    <kicad python> hardware/route.py hardware/int-board/int-board.kicad_pcb [passes]

Exports a Specctra DSN, runs ~/Applications/freerouting/freerouting-1.9.0.jar headless, and
imports the session file. Re-running gen-boards.py discards the routing; run this again after.
"""
import os
import subprocess
import sys

import pcbnew

JAVA = "/opt/homebrew/opt/openjdk/bin/java"
JAR = os.path.expanduser("~/Applications/freerouting/freerouting-1.9.0.jar")  # 2.4.1 exits before its save completes

path = os.path.abspath(sys.argv[1])
passes = sys.argv[2] if len(sys.argv) > 2 else "40"
base = path[:-len(".kicad_pcb")]
dsn, ses = base + ".dsn", base + ".ses"
board = pcbnew.LoadBoard(path)
pcbnew.ExportSpecctraDSN(board, dsn)
for attempt in range(3):
    subprocess.run([JAVA, "-jar", JAR, "-de", dsn, "-do", ses, "-mp", passes, "-l", "en"], check=True,
                   timeout=3600)
    if os.path.getsize(ses) > 0:
        break
    print("empty session file, retrying")
board = pcbnew.LoadBoard(path)
if not pcbnew.ImportSpecctraSES(board, ses):
    raise SystemExit("session import failed")
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(path)
os.remove(dsn)
print("routed", path)
