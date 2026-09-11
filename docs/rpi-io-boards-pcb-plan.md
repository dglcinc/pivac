# Raspberry Pi I/O Boards on Fabricated PCBs — Plan

**Status:** Draft under refinement. · **Owner:** David

Plan for replacing the two hand-wired Phoenix Contact perfboards in the RPI-BC 107,6 housing
with fabricated printed circuit boards of the same outline, carrying the same circuits. The
relay-input board is specified in `docs/rpi-io-board-design.md` and the 1-wire board in
`docs/ds18b20-bus-topology.md`; this document does not repeat their reasoning. Both boards are
built and in service, so this is a repeatability project: a board anyone can order and populate
in an hour replaces two 600-line hand-wiring procedures.

---

## 1. Scope

**In scope.** Two KiCad designs, one per board, with the outlines, thicknesses and restricted
areas of the Phoenix drawings, so they drop into the housing in place of the perfboards. The
same circuits, the same BCM pins, the same PTSM plugs at the same positions, and the same 5-way
link cable between the boards, so every field wire and the link cable move across by unplugging
and replugging. Footprints, unpopulated, for the additions already planned in the design docs.
A prototyping field of plated holes on each board so a bodge is still possible. Fabrication by
a board house; assembly by hand.

**Out of scope.** No change to `pivac`, `config.yml`, InfluxDB or Signal K: the BCM map is
preserved, so nothing downstream notices the swap. No consolidation of the two boards into one:
the probe sockets belong at the EXT board's end of the housing, and the relay wiring stays away
from the 1-wire bus (`docs/rpi-io-board-design.md` Appendix A). No assembly service. No change
to the label; `docs/PhoenixContact-BC-RPI-label.gen.py` describes plug positions, which do not
move.

## 2. The two boards

| | INT board (Pi side) | EXT board (1-wire side) |
|---|---|---|
| Phoenix part | RPI-BC INT-PCB SET, 2202994 | RPI-BC EXT-PCB HBUS SET, 2202995 |
| Drawing | 00914691/00 (`phoenix contact pcb.pdf`) | 00913308/02 (`pxc_2202995_01_02_…_2D.pdf`) |
| Outline | 85 ±0.3 × 59 ±0.3 mm | 85 ±0.3 × 38.5 ±0.3 mm |
| Thickness | 1.6 ±0.2 mm | 1.6 ±0.2 mm |
| Grid | 23 × 30 holes, 2.54 mm, ⌀1.0 mm, ⌀1.6 mm pads | 14 × 33 holes, 2.54 mm, ⌀1.0 mm, ⌀1.6 mm pads |
| Fixed connectors | PSTD 0,65X0,65/40-2,54 (Pi header, terminal area A); 4 × PTSM 0,5/4-HH-2,5-THR (terminal area B) | PSTD 0,65X0,65/18-3IS-2,54 (power riser, terminal area A) |
| Restricted areas | upper band, lower band, vertical strip with bulges (housing contact, solder side) | upper band rows 8–9, lower band rows 25–26 |
| Circuit | 11 optocoupler channels, +14 V rail with 1N4007, 5-way link terminal | DS2482-100, 100 nF, three PTSM 3-way probe sockets, PTSM 5-way link header |
| Parts | 3 × LTV-847 DIP-16 in sockets, 12 × 4.7 kΩ, 1N4007, 4 × PTSM 4-way, 5-way 2.54 mm screw-terminal header | DS2482-100 SOIC-8, 100 nF, 3 × PTSM 0,5/3-HH-2,5-THR, 1 × PTSM 0,5/5-HH-2,5-THR |
| Joints | about 110 | about 25 |

Both drawings are in `~/OneDrive - DGLC/Claude/HVAC Manuals/` and both are marked *simplified
representation*. The STEP models in `hardware/vendor/` are the authority; Appendix A holds the
geometry read from them.

## 3. Design inputs

A KiCad design is a schematic, a set of footprints and a board file. The footprint is what the
board house builds from: it carries the drill diameter, pad shape, pitch and courtyard for each
part, and the fabricated board has holes only where a footprint puts them. This is why the PTSM
and PSTD footprints matter even with hand assembly. PTSM is 2.5 mm pitch on a 2.54 mm grid; the
perfboard absorbs the 0.12 mm drift in an oversized hole, but a fabricated footprint places
each hole exactly, and the fit check against the housing needs the connector's 3D body.

### 3.1 Files to fetch from Phoenix

Phoenix offers each product's downloads in about two dozen formats. These are the ones that
serve, and what each is for:

| Item | Format | Why this one |
|---|---|---|
| The two boards, 2202994 and 2202995 | **STEP AP214** (`.stp`), the only CAD format Phoenix offers for them; in `hardware/vendor/` | Text-based solid model. Every hole is a cylinder and the restricted areas are a 0.02 mm solid on the solder face, so the outline, hole centres, connector positions and keep-outs all read to the hundredth of a millimetre. `hardware/step-geometry.py` extracts them in the build docs' frame; Appendix A is its output. |
| PTSM 0,5/4-HH-2,5-THR, PTSM 0,5/3-HH-2,5-THR, PTSM 0,5/5-HH-2,5-THR, PSTD 0,65X0,65/40-2,54 | **ECAD → KiCad** (`.kicad_sym` + `.kicad_mod`), from the Ultra Librarian or SamacSys link on the product page | Native symbol and footprint; nothing to transcribe. Stock KiCad carries Phoenix MC, MSTB and SPT families but not PTSM. |
| The same connectors, and the RPI-BC 107,6 housing halves | **STEP** (`.stp`) | 3D bodies for the fit check in the KiCad 3D viewer: connector height against the cover, plug entry against the housing opening. |
| PSTD 0,65X0,65/18-3IS-2,54 (EXT riser) | STEP only | The riser is unused by this build; its position is needed only so the new EXT board clears it. |

Put the files in `hardware/vendor/` in this repo. STEP files run to a few megabytes each and
are fine in git at this count.

### 3.2 What already exists

- Schematic: `docs/rpi-io-board-schematic.svg` and the channel master map in
  `docs/rpi-io-board-design.md` §2.1. Schematic capture is transcription.
- BOM: the parts tables in both design docs (§2 above).
- Net-to-pin map: the GPIO access-pad table in `docs/rpi-io-board-design.md` §4.2 and the
  plug table in §4.3.
- Test procedure: steps 7 and 8 of the same document, which apply unchanged to a fabricated
  board.

## 4. Layout

### 4.1 INT board

Everything the perfboard fixes stays fixed: the Pi header at terminal area A, the four PTSM
plugs at terminal area B in the order J1 · J2 · J3 · J4, position 4 of each plug as COM, and
the +14 V entry at J4.1. The three optocouplers sit between the plugs and the header as they do
now. With copper doing the routing there are no rails, stubs, bridges or keep-out crossings to
plan; the solder-side restricted areas still apply to pin tails and vias, so the parts sit
between the bands as before and traces cross the bands on the inner face of the board where the
housing does not touch.

Bring every one of the 40 header pins to a labelled pad, as the Phoenix board does. The
unassigned GPIOs (16, 18, 20, 21), the SPI block (7–11), the serial console (14, 15) and the
ID EEPROM pair (0, 1) are then reachable without a wire to the socket. GPIO 26 gets a pad and a
silkscreen mark that it is dead on this Pi.

Provisions, placed but not populated:

- **Twelfth channel.** IC-B channel 4 is wired to a plug position and a GPIO pad (GPIO 16) so a
  fifth plug or a re-assignment is a solder job.
- **24 VAC supply.** DB107 bridge and 100 µF/50 V capacitor at the J4 entry, in series with the
  1N4007 position, so the rectified-panel-supply upgrade in Appendix A is two parts and twelve
  resistor swaps. The resistor footprints take 1/2 W bodies.
- **Prototyping field.** A block of plated 2.54 mm holes, at least 6 × 8, in the free area below
  the lower band, with a 3V3 and a GND pad beside it. This is what keeps the board repairable in
  the field.
- **Test points.** COM, +14 V and Pi GND on labelled pads for the meter.

### 4.2 EXT board

The DS2482 sits directly on the board in SOIC-8, no adapter. The three probe sockets stay at the
short-end opening and the 5-way link header at its present end, so the link cable and the CAT6
trunk plug in unchanged. The riser field is left clear.

Provisions, placed but not populated:

- **Second DS2482 at 0x19** with its own probe socket, for the outdoor run
  (`docs/ds18b20-bus-topology.md` Appendix A). The AD0/AD1 straps are solder jumpers so either
  chip can take either address.
- **Rollback pull-up.** A 0805 footprint between DATA and VCC and a solder jumper from GPIO 4
  (link position 4) to DATA, so the `w1-gpio` fallback is two solder joints instead of a rewire.
- **Prototyping field**, smaller, in the lower field.

### 4.3 Decisions to make in the schematic

- The 5-way link on the INT board is a 2.54 mm screw-terminal header today and a PTSM 5-way on
  the EXT board. Making both ends PTSM 0,5/5 puts one plug type on the whole assembly and one
  spare in the drawer.
- The optocouplers stay socketed. A socket is the only part on the INT board that needs
  attention beyond a through-hole joint, and it keeps the chip-swap fault path.
- Silkscreen carries the channel names, plug numbers, position 1 of the link header, the COM
  warning and the board revision. The label generator stays as it is.

## 5. Fabrication

| Vendor | Bare boards, both designs | Assembly | Turnaround | Notes |
|---|---|---|---|---|
| **OSH Park** | INT 7.8 in² at $5/in² is about $39 for three; EXT 5.1 in² about $26 for three | none | ships in 9–12 days; 5 business days at $10/in² | US-made, free US shipping, no customs. Three copies is the spare count wanted. |
| JLCPCB | about $2–5 per design for five, plus $10–30 shipping | through-hole hand-solder $3.50 plus $0.017 per joint, parts from the LCSC library or consigned | fab 2–3 days; shipping 4 days by DHL or 2–3 weeks economy | Cheapest boards. Assembly is only cheap if LCSC substitutes are accepted for the PTSM connectors. |
| PCBWay | about $5 per design for five to ten, plus shipping | quoted; sources from Digi-Key and Mouser, so genuine PTSM parts | 3–4 weeks | The turnkey route that keeps the Phoenix connectors, at roughly ten times the self-assembled cost. |

Order bare boards from OSH Park and assemble by hand. The joint count makes assembly service
pointless: 30 through-hole parts into printed footprints is under an hour, and the socketed
optocouplers are the only parts a service would handle differently. Two-layer, 1.6 mm, 1 oz
copper, HASL finish; nothing here needs more.

Component sourcing stays as in the build docs: PTSM headers and plugs, PSTD header, LTV-847,
DS2482-100, passives from Digi-Key or Mouser. One order covers three boards of each.

## 6. Work plan

| Step | Who | Output | Effort |
|---|---|---|---|
| 1. Fetch the STEP and KiCad files per §3.1 into `hardware/vendor/` | David | vendor files in the repo | an evening |
| 2. Count the EXT board's rows and check the INT board's column 3 against Appendix A | David | two answers in §7 | 10 min |
| 3. KiCad project per board: outline, holes and restricted areas from Appendix A, connectors placed, schematic from the master map, BOM | Claude | `hardware/int-board/`, `hardware/ext-board/` | a day |
| 4. Layout and DRC; 3D fit check against the housing STEP | Claude, David reviews | Gerbers, drill files, assembly drawing, BOM CSV | half a day |
| 5. Order boards and parts | David | three of each board | 2 weeks elapsed |
| 6. Populate one of each; electrical check per `rpi-io-board-design.md` steps 7–8; DS2482 bench check per `ds18b20-bus-topology.md` §8 on the spare Pi | David | one proven pair | an evening |
| 7. Swap in the housing: pull plugs, exchange boards, replug; confirm every channel and all eight probes in Signal K | David | production on fabricated boards | 30 min, one restart of `pivac-gpio` and `pivac-1wire` |
| 8. Documentation: build docs become schematic, BOM and assembly notes; hole-by-hole sections retire; `docs/new-pi-cutover.md` and CLAUDE.md point at the KiCad files | Claude | PR | half a day |

Steps 3 and 4 need the files from step 1; step 2 is independent. Nothing in steps 1–6 touches
the running system.

## 7. Open questions

- The EXT model has 33 rows of holes, with row 1 sitting 1.16 mm from its edge and row 33
  2.56 mm from the other; `docs/ds18b20-bus-topology.md` counts 32. The band rows agree with the
  model when row 1 is the close-edge row, so the doc is short one row at the far end. Confirm
  by counting on the board.
- The INT model has no holes in column 3, rows 1–21, where `docs/rpi-io-board-design.md` §4.2
  places an access pad for every even header pin. Either the model omits the fan-out pads or the
  pads are surface features; the build used column 4 for the wired even pins, so nothing in
  service depends on it. Check the board.

- Should the INT board also carry the second DS2482 footprint, so a single-board variant is
  possible later, or is the two-board rule firm? The design docs argue for two; this plan keeps
  two.
- Is a fifth PTSM plug position available on the housing's terminal opening for the twelfth
  channel, or does the twelfth channel share J4?
- The mounting of the boards in the housing: whether the perfboards are retained by the card
  guides alone, or by the header and riser as well. The STEP of the housing answers this; if the
  card guides alone retain them, the outline tolerance matters and OSH Park's routing tolerance
  should be checked against ±0.3 mm.

## Appendix A — geometry from the Phoenix STEP models

Output of `hardware/step-geometry.py` over `hardware/vendor/*.stp`, in the build docs' frame:
column 1 left, row 1 top, component side toward the viewer, origin at the board's top-left
corner, y increasing downward as in KiCad. The INT model is mirrored in x relative to this frame
(doc column = 24 − model column); the EXT model is not. Both models put the solder face at
z = 0, the component face at z = 1.6, and the restricted areas as a 0.02 mm solid on the solder
face, which is where the housing ribs bear on the board.

### A.1 INT board, 59 × 85 mm

| Feature | Position |
|---|---|
| Grid column c | x = 1.56 + (c − 1) × 2.54, c = 1…23 (1.56 to 57.44) |
| Grid row r | y = 8.78 + (r − 1) × 2.54, r = 1…30 (8.78 to 82.44) |
| Grid holes absent | columns 1–3 rows 1–21; column 1 rows 27–30; column 2 row 30; row 1 columns 4–21; column 22 row 30 |
| Pi header, 2 × 20 | columns at x = 2.23 and 4.77; rows at y = 8.37 + (k − 1) × 2.54, k = 1…20 (8.37 to 56.63). Pin 1 is the top pad of the x = 4.77 column. The header sits 0.67 mm right of and 0.41 mm above grid columns 1–2 rows 1–20. |
| PTSM plug pins, 16 | y = 6.95; ⌀1.1 hole, ⌀1.95 pad; positions at 2.5 mm pitch in four groups 11.7 mm apart: J1 x = 9.35, 11.85, 14.35, 16.85; J2 21.05…28.55; J3 32.75…40.25; J4 44.45…51.95 |
| Upper restricted band | y 18.11–22.31, x 12.99–59.00 (grid rows 5–6 from column 6) |
| Lower restricted band | y 61.29–65.49, x 6.64–59.00 (grid rows 22–23 from column 3) |
| Vertical restricted strip | x 48.85–50.75, y 22.31–61.29 (grid column 20, rows 6–22), with ⌀3.26 bulges centred at (49.80, 26.91), (49.80, 37.83), (49.80, 45.77) and (49.80, 56.69) |

The restricted solid is relieved around every grid pad inside it (⌀1.6 clearances), so the
pads exist there and the housing bears between them; a pin tail in one still fouls the rib.

### A.2 EXT board, 38.5 × 85 mm

| Feature | Position |
|---|---|
| Grid column c | x = 2.49 + (c − 1) × 2.54, c = 1…14 (2.49 to 35.51) |
| Grid row r | y = 1.16 + (r − 1) × 2.54, r = 1…33 (1.16 to 82.44) |
| Grid holes absent | column 1 rows 1, 11, 12, 22, 23, 33; column 2 rows 11, 12, 22, 23; column 3 rows 11–23; column 13 rows 1 and 33 |
| Riser pin field | grid columns 1–2, rows 13–21 (the 18 positions of the PSTD 0,65X0,65/18-3IS-2,54), with pre-wired traces to columns 4–5 |
| Upper restricted band | y 18.11–22.31, full width (grid rows 8–9) |
| Lower restricted band | y 61.29–65.49, full width (grid rows 25–26) |

The two bands sit at the same y on both boards, so the housing ribs are one pair of features
that both boards must clear; a new board of either outline keeps them at these positions.

