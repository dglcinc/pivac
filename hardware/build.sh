#!/bin/sh
# Regenerate, route, check, render and export both boards. Needs KiCad 10 in ~/Applications and
# Freerouting 1.9.0 in ~/Applications/freerouting (see docs/rpi-io-boards-pcb-plan.md §6).
# Freerouting is not deterministic and sometimes leaves a connection open or crosses two tracks,
# so each board is regenerated and routed again until DRC reports no violation and nothing
# unconnected, up to six attempts.
set -e
cd "$(dirname "$0")"
PY=~/Applications/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
CLI=~/Applications/KiCad.app/Contents/MacOS/kicad-cli
$PY gen-boards.py "$@"
rm -f pivac.kicad_sym; python3 gen-schematics.py; $PY bom.py
for b in ${*:-int ext}; do
  for attempt in 1 2 3 4 5 6; do
    [ $attempt -gt 1 ] && $PY gen-boards.py $b
    $PY route.py $b-board/$b-board.kicad_pcb 300
    $CLI pcb drc --output $b-board/$b-board-drc.json --format json --severity-error $b-board/$b-board.kicad_pcb
    if python3 -c "import json,sys; d=json.load(open('$b-board/$b-board-drc.json')); sys.exit(0 if not d['violations'] and not d.get('unconnected_items') else 1)"; then
      echo "$b: clean on attempt $attempt"; break
    fi
    echo "$b: attempt $attempt not clean"
    [ $attempt -eq 6 ] && { echo "$b: giving up"; exit 1; }
  done
  for side in top bottom; do
    $CLI pcb render --output $b-board/$b-board-$side.png --side $side --width 1600 --height 2300 \
      --quality basic --background opaque --zoom 1.0 $b-board/$b-board.kicad_pcb
  done
  rm -rf $b-board/gerbers; mkdir -p $b-board/gerbers
  $CLI pcb export gerbers --output $b-board/gerbers/ --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
      --no-x2 --subtract-soldermask $b-board/$b-board.kicad_pcb
  $CLI pcb export drill --output $b-board/gerbers/ --format excellon --excellon-units mm --generate-map --map-format gerberx2 $b-board/$b-board.kicad_pcb
  (cd $b-board && rm -f $b-board-gerbers.zip && zip -q -j $b-board-gerbers.zip gerbers/*)
done 2>&1 | grep -viE "wxApp|image handler|pass #"
