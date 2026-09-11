# Raspberry Pi I/O Boards on Fabricated PCBs — Plan

**Status:** First complete draft of both boards generated, routed and DRC-clean (`hardware/`). Open questions in §7 gate the order. · **Owner:** David

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
same BCM pins, the same PTSM plugs at the same positions, and a 5-way link between the boards
on a PTSM 0,5/5 header at each end, so every field wire and the link cable move across by
unplugging and replugging. The sense supply comes from the panel's 24 VAC instead of the 14 V
wall wart. Copper does all the wiring; the link cable is the only wire left. Footprints, unpopulated, for the additions already planned in the design docs.
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

`hardware/gen-boards.py` places every part and assigns every net; `hardware/route.py` routes
with Freerouting; `hardware/build.sh` runs both, the DRC and the renders. The renders
(`hardware/*-board/*-top.png`, `*-bottom.png`) are the quickest review.

### 4.1 INT board

Fixed by the housing: the four PTSM plugs at the Phoenix pin positions along the top edge,
entry facing the edge; the Pi socket on the solder side at the header position. The three
LTV-847 sockets sit in a column at x 10.5–28 between the housing bands, one per row, and each
row's four LED resistors stand beside its socket. The 24 VAC section is in the bottom field:
four 1N4007 flat as the bridge, a ⌀10 mm 220 µF capacitor, and the two link headers at the
bottom edge with their entries facing it. The PTC fuse, the MOV position and three test points
(VS, COM, GND) are on the right-hand strip past the housing's vertical rib; the spare channel
outputs and a 9 × 4 prototyping field fill the rest of the bottom right.

**Header breakout.** A shadow column of pads 2.54 mm inside the header's inner column gives one
labelled pad per header row: SCL, GPIO4, GND, GPIO18, SDA, 5V, 3V3, GPIO10, 9, 11, 7, 8, GND,
GND, GPIO20, GPIO21 (rows 1–2 sit under the J1 body and rows 16 and 18 have no free pin). The
outer-column grounds are tied by a pre-routed bus along the board edge, since the router cannot
pass tracks through the column; header pins 9, 25 and 39 (also GND) are left unconnected, as
are the serial console, the ID EEPROM pair and the channel pins already used.

**24 VAC supply.** J4.1 is 24 VAC hot and J4.2 24 VAC common, through a 0.1 A PTC and into a
full-wave bridge; the DC negative is `COM`, the sense return on position 4 of every plug, and
it never meets Pi ground. At 25.9 VAC the rail is about 35 V, so the LED resistors are 12 kΩ
1/4 W: 2.8 mA per channel, the same current the 14 V build ran, 0.1 W per resistor. The bridge
carries at most 12 × 2.8 mA. A MOV position across the AC input is placed but not fitted.
J4.3 remains the tenth channel (`SP-D`); channels 11 and 12 end on pads (`J8`) with `COM`.

**Channel map.** J1: ZV, DHW, BLR. J2: CHIL, BOS1, BOS2. J3: DEHUM, SCALA, HPHEAT. J4: 24 VAC,
24 VAC, SP-D. BCM pins are unchanged from the build doc, so nothing downstream moves.

### 4.2 EXT board

The three PTSM 3-way probe sockets at row 2 with their entries over the row-1 edge, as built.
U1 (DS2482-100, 0x18) and its 100 nF sit under the sockets; a second DS2482 (U2, 0x19) with
its own decoupling is placed but not fitted in the mid field, and a three-pad solder jumper
`JP2` sends H3's DATA either to the shared bus (default) or to U2. `JP1` bridges GPIO4 to DATA
and `R1` (2k2, not fitted) is the pull-up, together the `w1-gpio` rollback. The 5-way link
header is at row 18 with its entry from the row-19 side, as built. The lower field is an
11 × 6 prototyping grid with VCC, DATA and GND pads beside it; the riser field is a rule area
with no pads.

### 4.3 Powering the Pi from the 24 VAC bus

Feasible, with four conditions. The converter must be isolated: a non-isolated buck would tie
the Pi's ground to the bridge negative, which is `COM`, and the optocoupler isolation would be
gone. The rectified bus peaks near 37 V, so the converter must be a 4:1 part rated 18–75 V
(9–36 V parts sit on the limit); the Murata UEI15-050-Q48 and Traco TEN 15-4811WIN classes fit,
at 1" × 1" or 1" × 0.8" and about $40–60. The panel transformer must have the VA to spare: a
headless Pi 4 with the Arduino on USB draws 5–8 W, about 10 VA at the transformer, on top of
the thermostats, zone valves and relays already on it; a 40 VA transformer may not. And the
`PivacPower` Shelly plug loses its purpose, since the Pi would no longer be on a mains cord to
cycle remotely. The transformers are 75 VA, so
the budget is not the obstacle. Neither board has room for a 1" × 1" footprint without moving
the EXT link header or reworking the INT bottom field, so the provision in this draft is the
unfitted 4-way power link `J7` (VS, COM, +5V, GND), which carries raw DC out to a converter
and 5 V back to the header pins. An off-board 24 VAC-to-USB-C adapter is the zero-design
alternative and keeps the Pi's own input protection. Until one is chosen the Pi keeps its
USB-C supply; nothing else in the design depends on it.

**Parts that exist.** No maker sells an isolated 24 VAC-in, 5 V-out supply; the low-voltage AC
input is the rare part. Three routes were found (2026-09-11):

| Part | Input | Output | Isolated | Price | Verdict |
|---|---|---|---|---|---|
| Mean Well DDR-15L-5 | 18–75 VDC | 5 V 3 A, trims 4.5–5.5 V | 4 kV | about $16, Digi-Key | The pick. DIN rail, 17.5 mm wide. Needs a rectifier ahead of it: a 2 A bridge and 1000 µF 50 V, either on a DIN terminal or the INT board's own bridge with its capacitor enlarged. |
| PowerStream PST-AC24DC5 | 10–28 VAC | 5 V 5 A | no | $29.75 | Takes 24 VAC directly, but its output negative sits a diode drop from the transformer common, and so would the Pi's ground and `COM`; the isolation the board exists for is lost. |
| sCharge ACDC-24V-5V-3A | 16–28 VAC | 5 V 3 A on USB-C | not stated, assume no | €21, EU shop | Same objection, and no US stock. |

With the DDR-15L-5, feed the Pi through a USB-C cable with bare ends into the converter's
output terminals, trimmed to 5.15 V for cable drop, so the Pi keeps its own input protection;
the board's `J7` power link is the alternative for feeding the header pins directly.

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
| 3. KiCad board per design: outline, holes and restricted areas from Appendix A, connectors placed, nets from the master map, routed — done; the schematic sheet and BOM export follow | Claude | `hardware/int-board/`, `hardware/ext-board/` | done |
| 4. Review the renders; 3D fit check against the housing STEP; Gerbers | Claude, David reviews | Gerbers, drill files, assembly drawing, BOM CSV | half a day |
| 5. Order boards and parts | David | three of each board | 2 weeks elapsed |
| 6. Populate one of each; electrical check per `rpi-io-board-design.md` steps 7–8; DS2482 bench check per `ds18b20-bus-topology.md` §8 on the spare Pi | David | one proven pair | an evening |
| 7. Swap in the housing: pull plugs, exchange boards, replug; confirm every channel and all eight probes in Signal K | David | production on fabricated boards | 30 min, one restart of `pivac-gpio` and `pivac-1wire` |
| 8. Documentation: build docs become schematic, BOM and assembly notes; hole-by-hole sections retire; `docs/new-pi-cutover.md` and CLAUDE.md point at the KiCad files | Claude | PR | half a day |

Steps 3 and 4 need the files from step 1; step 2 is independent. Nothing in steps 1–6 touches
the running system.

## 7. Open questions

- **Header numbering: verified.** On the built board, component side up, plugs away, pin 1 is
  the top-right pad of the socket (David, 2026-09-11), which is how the board file numbers it.
- **Link plug clearance.** The EXT link is where the build put it, with the same PTSM plug, so
  that end is proven. The INT link header is new: at the bottom edge with its entry facing the
  edge, the Pi's USB end. The DEV-KIT STEP (`hardware/vendor/pxc_2202874_…_3D.stp`) lays its
  five parts out side by side rather than assembled, so it does not answer this; a trial with a
  spare PTSM plug held at that spot on the built board does.
- **Component height.** The tallest parts are the ⌀10 capacitor (12.5 mm) and the DIP sockets
  with chips (about 8 mm). The clearance between the INT board's component side and the cover
  is unmeasured.
- **Transformer.** 75 VA units; David will pick one with 10 VA to spare if the Pi is to be
  powered from the bus.

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

