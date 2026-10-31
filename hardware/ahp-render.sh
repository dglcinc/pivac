#!/bin/sh
# Render the Pico W carrier alone and in the 1593K: needs KiCad in ~/Applications and FreeCAD. The box
# models come from ahp-box-models.py under FreeCAD; pass their folder and an output folder.
# Usage: ahp-render.sh MODELS OUT
set -e
cd "$(dirname "$0")"
PY=~/Applications/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
CLI=~/Applications/KiCad.app/Contents/MacOS/kicad-cli
M=$1; O=$2; T=$(mktemp -d)
$PY gen-ah-pico.py --models "$M" --out "$T/board" >/dev/null 2>&1
$PY gen-ah-pico.py --models "$M" --box open --out "$T/open" >/dev/null 2>&1
$PY gen-ah-pico.py --models "$M" --box closed --out "$T/closed" >/dev/null 2>&1
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
r closed 0.6 "180,0,180" air-handler-pico-box-closed-base
rm -rf "$T"
