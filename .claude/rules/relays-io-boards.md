---
paths:
  - "pivac/GPIO.py"
  - "scripts/io-board-test.py"
  - "tests/test_io_board_pinout.py"
  - "hardware/**"
  - "docs/rpi-io-boards-*"
  - "docs/new-pi-cutover.md"
  - "docs/cdp-chiller-rework-plan.md"
---

# Relays, GPIO and the I/O boards

<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright David Lewis -->

Loaded when a file under its `paths:` is read; `CLAUDE.md` says to read it first for any work on a relay input, the Pi's GPIO, the INT and EXT boards or a board design in `hardware/`. Rules here; the measurements and incident history behind them are in the docs named.

## Relays and GPIO (`docs/cdp-chiller-rework-plan.md`, `docs/operational-notes.md`)

- **Inputs (BCM):** ZV 17, DHW 27, BLR 22, BOS2 5, BOS1 6, HPCALL 25, SCALA 23 (J3.2), HPHEAT 24 (J3.3), HPCOOL 13 (J4.1), DHWX 19 (J4.2). Free: BCM 16 (`SP-E`, J4.3, no wire) and BCM 12 (J3.1, the decommissioned dehumidifier's call). **`HPCALL` is the HZ-432's `Y1`, the call for the primary Taco pump, not for the chiller** (history before 2026-09-15 is under `electrical.ac.switch.utility.CHIL`). **`BLR` is `W1`, read upstream of the boiler**, so it reads 1 on a call the boiler refuses during DHW. `DHWX` marks a call bridged to the tank during DHW, with `HPCALL` staying 0. `HPHEAT` = 1 means the panel is in heating mode (`B`), `HPCOOL` = 1 that it is in cooling mode (`O`). `SCALA` = 1 means water under the Scala pump and the pump already cut. The Bosch inputs report the call, never proof the compressor ran. Zone → source in cooling: `HPCALL` serves MASTER_BR, DSTRS_FAM_ROOM (the utility air handler) and KIDS_ROOM; `BOS1` KITCHEN; `BOS2` GREAT_ROOM. In heating all five zones are hydronic. Adding a relay: `restart pivac-gpio`, plus an `order` entry in `~/.signalk/baseDeltas.json` and `restart signalk` for the WilhelmSK tile. Dropping or renaming one: config edit → `restart pivac-gpio` → `restart signalk`; no `.wlyt` change. Relay poles, the DHW bridge, the tile order and the measurements: `docs/operational-notes.md`, Relay inputs and I/O boards in full.
- **Production runs the rev B INT and rev C EXT boards on Pi `88:a2:9e:3c:c3:73` since 2026-10-11.** 24 VAC enters on EXT J3 (black 2-way plug, `R` on pin 1, `C` on pin 2); the Pi is powered from EXT J4 (white 2-way plug), **so the wall adapter must never be connected while J4 is live**. **The 7-way GH link has pin 1 at the bottom end of both headers; a mirrored link puts 35 V on the Pi's SDA.** A PTSM plug with fewer positions enters a larger socket, so handle the 24 VAC plug last, transformer off, and read the legend. **GPIO 26 (pin 37) is dead.** YOFF is retired, not pending; do not move the wire. Make every continuity check on an I/O board off the Pi. A spare production Pi is in inventory and the rev A pair is the rollback. Bench Pis on the `pibench` card: `2c:cf:67:80:55:00` has a dead GPIO2 (no I2C) and runs the guided walk; `dc:a6:32:19:12:ee` has good I2C with BCM 13, 25 and BCM 16's pull-up dead. Read GPIO2 bare under pull-up before trusting any I2C result. Full text: `docs/operational-notes.md`, Relay inputs and I/O boards in full.

## Board designs

**Every new board revision carries `© <year> David Lewis · CC BY-NC 4.0` on F.SilkS beside its title block** (the monogram, name and version from `gen-boards.py` `title_block`, or the hand-placed legend in `gen-ah-pico.py`), added in the generator when that revision is generated; where the front has no room beside the title block, it goes on B.SilkS in open copper, as on AirMaster Rev C (two lines under the Pico); the boards already ordered (INT rev B, EXT rev C, AirMaster Rev B) are left as they are. **A board's paste stencil carries openings only for the parts meant for paste and hot air**: in the generator, remove the paste layer from every part to be hand soldered (the Pico's castellations, PTSM headers and other plastic-bodied connectors, anything through-hole), so the stencil needs no tape; the AirMaster Rev B stencil predates this and is not used (`docs/airmaster/rev-b/air-handler-pico-assembly.md`).

## Reference docs

| Doc | Covers |
|-----|--------|
| `docs/cdp-chiller-rework-plan.md` | Single-chiller conversion: relay hardware, zone → equipment map, label |
| `docs/rpi-io-boards-pcb-plan.md` | Fabricated PCB replacements for the two Phoenix perfboards: dimensions, files to fetch, layout provisions, vendor choice, work plan; Appendix A.3 maps the Pi 4B's connectors under the INT board |
| `docs/rpi-io-boards-revb-plan.md` | Rev B: 24 VAC entry, rectifier and isolated converter on EXT feeding the Pi's USB-C, 7-way GH link, every channel on a plug, title block; component index, parts list, what `hardware/build.sh` produces (it regenerates and reroutes until DRC is clean, then exports the OSH Park gerbers), the path to the order. `docs/rpi-io-boards-pi-power-layout.svg` is its layout drawing |
| `docs/rpi-io-boards-revc-plan.md` | Rev C, EXT only: every edge connector becomes the surface-mount PTSM 0,5/n-HH-2,5-SMD header, flush with the board edge, because the through-hole headers fold at their pins. **From rev C on, every edge connector on EXT is this part.** J4 is the vertical header of the same family, J3 black and J4 white because they take the same plug. Footprints, EXT layout with two probe sockets, plugs and the latch, hand soldering, what `hardware/build.sh extc` produces in `hardware/extc-board` (boards ordered from OSH Park and connectors from Mouser 2026-09-27), the checks behind the order; `hardware/fit-check.py` lays Phoenix's STEP models (`hardware/vendor/`) on the generated footprints. `docs/rpi-io-boards-revc-ext-layout.svg` is its layout drawing |
| `docs/rpi-io-boards-revc-review.md` | The rev C EXT board as ordered: both faces and copper, what every reference designator is for, the hand-laid tracks, copper under U3, the legends, the checks behind the order |
| `docs/rpi-io-boards-revb-review.md` | The rev B boards as generated: both faces and copper of each, what every reference designator is for, the hand-laid tracks, the checks done and open, how to order from OSH Park |
| `docs/rpi-io-boards-review.md` | The rev A boards as ordered: both faces and copper of each, what every reference designator is for, the checks done, how to order from OSH Park |
| `docs/rpi-io-boards-parts.md` | Parts to buy for the rev A boards, with maker part numbers, search descriptions, quantities and distributor links |
| `docs/rpi-io-boards-assembly.md` | Bench sheet for populating the I/O boards, with the bench records of every set proven (rev A, rev B INT with rev C EXT): order of work, per-board table of reference, invoiced part and location, handling notes, checks with rev A values, the bench card and Pi, the bench record, link cable, housing swap. `docs/rpi-io-boards-reva-tone-map.svg` is its meter drawing |
| `docs/rpi-io-boards-reva-install.md` | The 2026-09-26 cutover to the rev A boards and the new Pi on the clone card, as run: who did each step, freeze and clone, UCG reservation move, the plug map against the perfboard (24 VAC on J4.1/J4.2, `HPCOOL` to the J8 pigtail), meter checks, first-boot and 1-wire proofs, the pigtail fault, afterwards, rollback |
| `docs/new-pi-cutover.md` | Day-of procedure for fitting the new Pi and its I/O and 1-wire boards on the clone card: freeze and clone, card prep, UniFi reservation, plug wiring, channel and bus proof, rollback |
