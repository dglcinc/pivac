#!/bin/sh
# Generate, route, pour and check the Pico W carrier, then export its gerbers. Freerouting is not
# deterministic, so the board is regenerated and routed again until DRC reports no error and nothing
# unconnected, up to eight attempts. Needs KiCad 10 in ~/Applications and Freerouting 1.9.0.
set -e
cd "$(dirname "$0")"
PY=~/Applications/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
CLI=~/Applications/KiCad.app/Contents/MacOS/kicad-cli
P=ahp-board/ahp-board.kicad_pcb
for attempt in 1 2 3 4 5 6 7 8; do
  $PY gen-ah-pico.py >/dev/null 2>&1
  $PY route.py $P ${1:-100} 2>&1 | grep -E "routed|failed" || true
  $PY ahp-pour.py $P 2>/dev/null
  $CLI pcb drc --output ahp-board/ahp-board-drc.json --format json --severity-error $P >/dev/null 2>&1
  if python3 -c "import json,sys; d=json.load(open('ahp-board/ahp-board-drc.json')); print(len(d['violations']),'errors',len(d.get('unconnected_items',[])),'open'); sys.exit(0 if not d['violations'] and not d.get('unconnected_items') else 1)"; then
    echo "clean on attempt $attempt"
    rm -rf ahp-board/gerbers; mkdir -p ahp-board/gerbers
    $CLI pcb export gerbers --output ahp-board/gerbers/ --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts --no-x2 --subtract-soldermask $P >/dev/null 2>&1
    $CLI pcb export drill --output ahp-board/gerbers/ --format excellon --excellon-units mm --generate-map --map-format gerberx2 $P >/dev/null 2>&1
    (cd ahp-board && rm -f ahp-board-gerbers.zip && zip -q -j ahp-board-gerbers.zip gerbers/*)
    exit 0
  fi
  echo "attempt $attempt not clean"
done
exit 1
