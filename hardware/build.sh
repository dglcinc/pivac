#!/bin/sh
# Regenerate, route, check and render both boards. Needs KiCad 10 in ~/Applications and
# Freerouting 1.9.0 in ~/Applications/freerouting (see docs/rpi-io-boards-pcb-plan.md §6).
set -e
cd "$(dirname "$0")"
PY=~/Applications/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
CLI=~/Applications/KiCad.app/Contents/MacOS/kicad-cli
$PY gen-boards.py "$@"
for b in ${*:-int ext}; do
  $PY route.py $b-board/$b-board.kicad_pcb 200
  $CLI pcb drc --output $b-board/$b-board-drc.json --format json --severity-error $b-board/$b-board.kicad_pcb
  for side in top bottom; do
    $CLI pcb render --output $b-board/$b-board-$side.png --side $side --width 1600 --height 2300 \
      --quality basic --background opaque --zoom 1.0 $b-board/$b-board.kicad_pcb
  done
done 2>&1 | grep -viE "wxApp|image handler|pass #"
