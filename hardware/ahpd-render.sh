#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
# Render the routed AirMaster carrier Rev D alone and in its printed case: needs KiCad in ~/Applications and FreeCAD.
# The case models come from ahpd-case.py under FreeCAD, which this runs into a temporary folder.
# Usage: ahpd-render.sh OUT
set -e
cd "$(dirname "$0")"
PY=~/Applications/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
CLI=~/Applications/KiCad.app/Contents/MacOS/kicad-cli
FC=/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd
O=$1; T=$(mktemp -d)
AHPD_MODELS="$T/models" $FC ahpd-case.py >/dev/null 2>&1
for v in "board none" "open open" "closed closed"; do
  set -- $v
  $PY ahp-add-models.py ahpd-board/ahpd-board.kicad_pcb "$T/models" $2 "$T/$1/ahpd-board.kicad_pcb" d >/dev/null 2>&1
done
r() { $CLI pcb render --quality high --background opaque --floor --width 1500 --height 1200 --perspective \
      --rotate "$3" --zoom "$2" --output "$O/$4.png" "$T/$1/ahpd-board.kicad_pcb" >/dev/null 2>&1; }
$CLI pcb render --quality high --background opaque --width 1400 --height 1400 --side top --zoom 1.0 \
  --output "$O/air-handler-pico-revd-board-top.png" "$T/board/ahpd-board.kicad_pcb" >/dev/null 2>&1
$CLI pcb render --quality high --background opaque --width 1400 --height 1400 --side bottom --zoom 1.0 \
  --output "$O/air-handler-pico-revd-board-back.png" "$T/board/ahpd-board.kicad_pcb" >/dev/null 2>&1
r board 1.0 "-40,0,-25" air-handler-pico-revd-board-iso
r open 0.75 "-40,0,-25" air-handler-pico-revd-case-open
r closed 0.5 "-40,0,-25" air-handler-pico-revd-case-closed-sensors
r closed 0.5 "-40,0,155" air-handler-pico-revd-case-closed-power
$CLI pcb render --quality high --background opaque --width 1500 --height 1200 --side top --zoom 0.8 \
  --output "$O/air-handler-pico-revd-case-closed-top.png" "$T/closed/ahpd-board.kicad_pcb" >/dev/null 2>&1
rm -rf "$T"
