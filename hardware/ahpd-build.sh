#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright David Lewis
# Generate, route, pour and check the AirMaster carrier Rev D, then export its gerbers and JLCPCB's assembly
# files. Freerouting is not deterministic, so the board is regenerated and routed again until DRC reports no
# error and nothing unconnected, up to sixteen attempts. Rev D is assembled by the fabricator, so the front paste
# layer is exported: every surface-mount part is on the front and takes paste, the Pico through its own pads.
# NOGERBERS=1 stops at the clean routed board, for review. Needs KiCad 10 in ~/Applications and Freerouting 1.9.0.
set -e
cd "$(dirname "$0")"
rm -rf ahpd-board/gerbers ahpd-board/ahpd-board-gerbers.zip
PY=~/Applications/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
CLI=~/Applications/KiCad.app/Contents/MacOS/kicad-cli
P=ahpd-board/ahpd-board.kicad_pcb
for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16; do
  $PY gen-ah-pico-d.py >/dev/null 2>&1
  $PY route.py $P ${1:-100} 2>&1 | grep -E "routed|failed" || true
  $PY ahp-pour.py $P 7 2>/dev/null
  python3 ahp-paste.py $P >/dev/null
  $CLI pcb drc --output ahpd-board/ahpd-board-drc.json --format json --severity-error $P >/dev/null 2>&1
  if python3 -c "import json,sys; d=json.load(open('ahpd-board/ahpd-board-drc.json')); print(len(d['violations']),'errors',len(d.get('unconnected_items',[])),'open'); sys.exit(0 if not d['violations'] and not d.get('unconnected_items') else 1)"; then
    echo "clean on attempt $attempt"
    [ -n "$NOGERBERS" ] && exit 0
    rm -rf ahpd-board/gerbers; mkdir -p ahpd-board/gerbers
    $CLI pcb export gerbers --output ahpd-board/gerbers/ --layers F.Cu,B.Cu,F.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts --no-x2 --subtract-soldermask $P >/dev/null 2>&1
    $CLI pcb export drill --output ahpd-board/gerbers/ --format excellon --excellon-units mm --generate-map --map-format gerberx2 $P >/dev/null 2>&1
    (cd ahpd-board && zip -q -j ahpd-board-gerbers.zip gerbers/* && rm -rf gerbers ahpd-board.ses)
    python3 ahp-jlc.py d
    exit 0
  fi
  echo "attempt $attempt not clean"
done
exit 1
