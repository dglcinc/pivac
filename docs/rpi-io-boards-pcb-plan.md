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
| Grid | 23 × 30 holes, 2.54 mm, ⌀1.0 mm | 14 × 32 holes, 2.54 mm, ⌀1.0 mm |
| Fixed connectors | PSTD 0,65X0,65/40-2,54 (Pi header, terminal area A); 4 × PTSM 0,5/4-HH-2,5-THR (terminal area B) | PSTD 0,65X0,65/18-3IS-2,54 (power riser, terminal area A) |
| Restricted areas | upper band, lower band, vertical strip with bulges (housing contact, solder side) | upper band rows 8–9, lower band rows 25–26 |
| Circuit | 11 optocoupler channels, +14 V rail with 1N4007, 5-way link terminal | DS2482-100, 100 nF, three PTSM 3-way probe sockets, PTSM 5-way link header |
| Parts | 3 × LTV-847 DIP-16 in sockets, 12 × 4.7 kΩ, 1N4007, 4 × PTSM 4-way, 5-way 2.54 mm screw-terminal header | DS2482-100 SOIC-8, 100 nF, 3 × PTSM 0,5/3-HH-2,5-THR, 1 × PTSM 0,5/5-HH-2,5-THR |
| Joints | about 110 | about 25 |

Both drawings are in `~/OneDrive - DGLC/Claude/HVAC Manuals/` and both are marked *simplified
representation*, which is why §4 asks for the DXF.

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
| Board drawings 00914691 and 00913308 | **DXF** (2D) | Text-based vector geometry. The outline, hole grid, restricted areas and connector positions can be read to the hundredth of a millimetre and imported straight onto `Edge.Cuts` and a keep-out layer. The PDF is a raster to the tooling here, so positions would otherwise be scaled by eye off a 2:1 A3 sheet. |
| PTSM 0,5/4-HH-2,5-THR, PTSM 0,5/3-HH-2,5-THR, PTSM 0,5/5-HH-2,5-THR, PSTD 0,65X0,65/40-2,54 | **ECAD → KiCad** (`.kicad_sym` + `.kicad_mod`), from the Ultra Librarian or SamacSys link on the product page | Native symbol and footprint; nothing to transcribe. Stock KiCad carries Phoenix MC, MSTB and SPT families but not PTSM. |
| The same connectors, and the RPI-BC 107,6 housing halves | **STEP** (`.stp`) | 3D bodies for the fit check in the KiCad 3D viewer: connector height against the cover, plug entry against the housing opening. |
| PSTD 0,65X0,65/18-3IS-2,54 (EXT riser) | DXF or STEP only | The riser is unused by this build; its position is needed only so the new EXT board clears it. |

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
| 1. Fetch the DXF, KiCad and STEP files per §3.1 into `hardware/vendor/` | David | vendor files in the repo | an evening |
| 2. Measure the header and plug centres on the built INT board with calipers, as a check on the DXF | David | four numbers in this document | 15 min |
| 3. KiCad project per board: outline and restricted areas from DXF, connectors placed, schematic from the master map, BOM | Claude | `hardware/int-board/`, `hardware/ext-board/` | a day |
| 4. Layout and DRC; 3D fit check against the housing STEP | Claude, David reviews | Gerbers, drill files, assembly drawing, BOM CSV | half a day |
| 5. Order boards and parts | David | three of each board | 2 weeks elapsed |
| 6. Populate one of each; electrical check per `rpi-io-board-design.md` steps 7–8; DS2482 bench check per `ds18b20-bus-topology.md` §8 on the spare Pi | David | one proven pair | an evening |
| 7. Swap in the housing: pull plugs, exchange boards, replug; confirm every channel and all eight probes in Signal K | David | production on fabricated boards | 30 min, one restart of `pivac-gpio` and `pivac-1wire` |
| 8. Documentation: build docs become schematic, BOM and assembly notes; hole-by-hole sections retire; `docs/new-pi-cutover.md` and CLAUDE.md point at the KiCad files | Claude | PR | half a day |

Steps 3 and 4 need the files from step 1; step 2 is independent. Nothing in steps 1–6 touches
the running system.

## 7. Open questions

- Should the INT board also carry the second DS2482 footprint, so a single-board variant is
  possible later, or is the two-board rule firm? The design docs argue for two; this plan keeps
  two.
- Is a fifth PTSM plug position available on the housing's terminal opening for the twelfth
  channel, or does the twelfth channel share J4?
- The mounting of the boards in the housing: whether the perfboards are retained by the card
  guides alone, or by the header and riser as well. The STEP of the housing answers this; if the
  card guides alone retain them, the outline tolerance matters and OSH Park's routing tolerance
  should be checked against ±0.3 mm.
