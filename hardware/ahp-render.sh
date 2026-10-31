#!/bin/sh
# Render the routed Pico W carrier alone and in the 1593K: needs KiCad in ~/Applications and FreeCAD. The box
# models come from ahp-box-models.py under FreeCAD; pass their folder and an output folder.
# Usage: ahp-render.sh MODELS OUT
set -e
cd "$(dirname "$0")"
PY=~/Applications/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
CLI=~/Applications/KiCad.app/Contents/MacOS/kicad-cli
M=$1; O=$2; T=$(mktemp -d)
for v in "board none" "open open" "closed closed"; do
  set -- $v
  $PY ahp-add-models.py ahp-board/ahp-board.kicad_pcb "$M" $2 "$T/$1/ahp-board.kicad_pcb" >/dev/null 2>&1
done
r() { $CLI pcb render --quality high --background opaque --floor --width 1500 --height 1200 --perspective \
      --rotate "$3" --zoom "$2" --output "$O/$4.png" "$T/$1/ahp-board.kicad_pcb" >/dev/null 2>&1; }
$CLI pcb render --quality high --background opaque --width 1400 --height 1400 --side top --zoom 1.0 \
  --output "$O/air-handler-pico-board-top.png" "$T/board/ahp-board.kicad_pcb" >/dev/null 2>&1
r board 1.0 "-40,0,-25" air-handler-pico-board-iso
$CLI pcb render --quality high --background opaque --width 1400 --height 1400 --side bottom --zoom 1.0 \
  --output "$O/air-handler-pico-board-back.png" "$T/board/ahp-board.kicad_pcb" >/dev/null 2>&1
r open 0.75 "-40,0,-25" air-handler-pico-box-open
r closed 0.45 "-40,0,-25" air-handler-pico-box-closed-sensors
r closed 0.45 "-40,0,155" air-handler-pico-box-closed-power
r closed 0.55 "-85,0,90" air-handler-pico-box-closed-leds
rm -rf "$T"
