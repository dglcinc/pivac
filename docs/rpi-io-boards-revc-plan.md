# Raspberry Pi I/O Boards — Rev C Plan

**Status:** Plan. Nothing generated or ordered. Rev B is on order and is fitted first; rev C follows it on EXT only. · **Owner:** David

Rev C replaces every edge connector on the EXT board with the surface-mount PTSM header, mounted with its entry face flush with the board edge, and replaces the 5 V output header with the vertical header of the same family. The through-hole headers on rev A fold at their pins when a plug is levered, because one row of pins is all that holds them. The surface-mount header sits flat on the board and is held at four places. The rev B design is `docs/rpi-io-boards-revb-plan.md`; this document states only what rev C changes.

**Rule for the EXT board from rev C on: every edge connector is a PTSM 0,5/n-HH-2,5-SMD header, flush with the edge.** A new edge connector on EXT takes this part and the footprint of §3.

---

## 1. Scope

**In scope.** On EXT: H1 and H2 become 3-way surface-mount headers on the top edge, J3 becomes a 2-way surface-mount header on the bottom edge, and all three sit with the entry face on the board edge. J4 becomes a 2-way vertical surface-mount PTSM header. H3 leaves the board with U2, C2 and JP2, and the tie slots TS1 leave with the JST header they served. The probe parts under the sockets move toward the upper rib to clear the header pads. A new footprint generator in `hardware/gen-boards.py` builds the surface-mount header.

**Out of scope.** The INT board stays at rev B: the enclosure supports its plugs on both sides, so its headers do not fold. The link between the boards stays the JST GH of rev B, which is lower than a PTSM header. The power section and the GH link on EXT keep their rev B nets and parts; U3 and C4 move. No change to `pivac`, `config.yml`, InfluxDB or Signal K. The plugs in service carry over.

**Boundaries assumed.**

- The housing accepts a plug with the header's entry face on the board edge, 1.7 mm further in than rev B (David, 2026-09-27).
- Both ends of EXT are open, so the sockets may move along the top edge, and the openings pass a latching plug, which is 16.8 mm wide on a 3-way socket.
- Two probe sockets are enough (David, 2026-09-27). H3 was a spare, and `U2` is unfitted on rev A and rev B.

## 2. Why the through-hole header folds and this one does not

Measured from Phoenix's STEP model of the 4-way header (`pxc_1778780_02_01_PTSM-0-5-4-HH-2-5-SMD-R32_3D.stp`, in `~/OneDrive - DGLC/Claude/`), with the entry face at y = 0. The model agrees with the datasheet drawing on every dimension they share.

| Feature | Position | Holds against |
|---|---|---|
| Housing underside | flat on the board, y 0 to 7.5 | downward load |
| Two solder anchors | feet y 1.5 to 6.5, 1.65 wide, 4 mm tall | lifting and rolling |
| Two locating pegs | ⌀0.8, 0.7 deep, at y 2.85 | sliding and rotation |
| Signal leads | feet y 6.9 to 9.5, behind the body | lifting at the rear |

The hold-down points span 8 mm front to back and 15.6 mm side to side on the 4-way part. The through-hole header has one pin row 5.4 mm behind its face and no other fixing, so a levered plug turns the body about that row and bends the pins.

## 3. The header and its footprint

`a` is the pin span, 2.5 mm × (positions − 1). Footprint coordinates take the entry face as y = 0 and the centre of the pin row as x = 0, y increasing into the board.

| Item | Value |
|---|---|
| Body | (a + 4.2) wide, 7.5 deep, 5.0 tall |
| Width over the anchors | a + 8.1 |
| Depth with leads | 9.5 |
| Signal pads | 1.2 × 3.2, at x = pin, y 6.6 to 9.8 |
| Anchor pads | 2.2 × 5.6, centred x = ±(a/2 + 2.65), y 0.8 to 6.4 |
| Peg holes | ⌀1.1 unplated, at x = ±(a/2 + 1.1), y 2.85 |
| Pad pattern width | a + 7.5 |
| Rating | 6 A, 160 V, 26–20 AWG |

| Positions | Body width | Over the anchors | Pad pattern |
|---|---|---|---|
| 2 | 6.7 | 10.6 | 10.0 |
| 3 | 9.2 | 13.1 | 12.5 |
| 4 | 11.7 | 15.6 | 15.0 |

With the face on the edge, the anchor pads start 0.8 mm from the edge and the peg holes leave 2.3 mm of board in front of them.

## 4. EXT layout

`docs/rpi-io-boards-revc-ext-layout.svg` is the layout drawing. The board is 38.5 × 85 mm and the top edge carries two probe sockets. Three 3-way headers would need 39.3 mm over their anchors.

| Ref | Part | Centre x | Edge | Pins |
|---|---|---|---|---|
| H1 | 3-way, black | 10.5 | top, entry toward −y | VCC · DATA · GND |
| H2 | 3-way, black | 28.0 | top, entry toward −y | VCC · DATA · GND |
| J3 | 2-way, black | 8.0 | bottom, entry toward +y | 1 R (hot) at x 9.25, 2 C (common) at x 6.75 |
| J4 | 2-way vertical, white | body x 25.1 to 30.1 | pin row along y, centre y 70.8, entry upward, leads toward the right edge | 1 +5 V at y 69.55, 2 GND at y 72.05 |

- H1 and H2 stand 17.5 mm apart, centre to centre, and the pair is centred on the board's 19.25 mm centre line. Two latching plugs sit side by side with 0.7 mm between them and reach x 2.1 and x 36.4.
- Their anchors span x 3.95 to 17.05 and x 21.45 to 34.55.
- U1, C1, JP1 and R1 stand in one row on the line y 13.9, 2.5 mm apart, from x 1.6 to x 36.9, so an iron reaches every pad. The header pads end at y 9.8 and the nearest pad of the row is 2.0 mm below them; the upper rib starts at y 18.11.

| Ref | Centre x | Extent in x |
|---|---|---|
| U1 | 4.6 | 1.6 to 7.6 over the leads |
| C1 | 13.6 | 10.1 to 17.1; pads at 11.1 and 16.1 |
| JP1 | 21.1 | 19.6 to 22.6 |
| R1 | 30.78 | pads at 25.7 and 35.86 |

- The four reference legends sit on one baseline at y 17.55, each centred under its part.
- `V`, `D` and `G` stand under the signal pads of H1 and H2 in bold at the size of J3's `R` and `C`, 0.5 mm below the pads and clear of the header bodies.
- J3 sits at x 8.0 so a latching plug on it reaches x 0.9 on the left. Its anchor pads span x 3.0 to 13.0 and its signal pads end 9.8 mm in from the bottom edge, at y 75.2.
- J4 is turned 90° from its datasheet orientation, which a surface-mount part allows. Its pad pattern spans x 24.8 to 32.5 and y 65.8 to 75.8, so its signal pads stand 2.25 mm from J2's pads. The side that faces the legend has no solder joint: the anchors are at the top and bottom and the leads leave to the right. C4 moves 3.3 mm left, to x 20.0, which opens 3.55 mm between it and J4's anchor pads for J4's legend.
- U3 moves 2 mm right for access to J1: body x 13 to 35, pins at x 15.11 to 32.89, pin 1 left. It stands 5.4 mm from J1's courtyard and 3.5 mm from the room kept clear for J1's plug and a finger, against 3.4 and 1.5 mm on rev B, and 3.5 mm from the board's right edge.
- The title block sits midway between C3 and U3, at the same distance from the right edge as on rev B: ring centre (31.2, 41.7), text lines 1.4 mm lower than rev B's. That leaves 2.3 mm between C3 and the ring and 2.2 mm between the second line and U3.
- The proto field PF1 is 8 × 3, from x 15.54 to x 33.32 and y 78.14 to y 83.22. It starts one column right of rev B to clear J3's anchor pad and one row lower to clear J4's.

### 4.1 J3 and J4 take the same plug

Both are 2-way PTSM, so J3's plug fits J4. The 24 VAC plug seated in J4 puts 36 V peak across U3's output and C4; the Pi is not at risk, because its pigtail is then unplugged. Two things tell them apart (David, 2026-09-27: one person handles the plugs and the pigtail is short):

| | J3 | J4 |
|---|---|---|
| Header and plug colour | black | white |
| Silkscreen beside it | `24VAC input`, bold, above the pads; `R` beside pin 1 and `C` beside pin 2 at the far end of the pads, 1.3 mm clear of the header body so the 5 mm body does not hide them | `5VDC output only` and `to Pi`, bold, two lines turned 90° counter-clockwise to read upward, between C4 and J4, centred on J4 |
| Pin legends | `R` and `C`, bold | `+5` and `G`, bold, beside the leads in the 2.25 mm between J4's pads and J2 |
| Orientation | horizontal, at the bottom edge | vertical, mid board |

**Which leg is R.** The bridge rectifies either way round, U3 isolates the Pi, and the sense contacts are dry, so the board works with the two leads swapped. The legs are marked because F1 is in pin 1's leg: on a transformer whose common is bonded to ground, F1 limits a fault to ground only when the hot lead, R, is on pin 1.

A plug does not enter a header with more positions, so the 2-way plugs do not fit the probe sockets and the probe plugs do not fit J3 or J4: the header's floor ribs stand 1.02 mm high and a plug's nose rides 0.70 mm above the floor.

### 4.2 The vertical header

Measured from Phoenix's STEP model of 1778696 (`pxc_1778696_02_00_PTSM-0-5-2-HV-2-5-SMD-WH-R24_3D.stp`).

| Item | Value |
|---|---|
| Body | 6.7 × 5.0, 7.5 tall |
| Width over the anchors | 10.6 |
| Depth with leads | 7.1; the leads leave one long side by 2.1 |
| Pegs | ⌀0.8, 1.4 outside the outer pins, 0.4 in from the long side the leads leave by |
| Height with a plug seated | 18.4, inside the 30 mm the housing gives EXT |
| Latch window | in each side wall, 1.2 to 2.1 below the top face |

## 5. Plugs

The PTSM `-P-` plugs fit both headers: the black 3-way 1778845 on the probe sockets, the black 2-way 1778832 on the 24 VAC entry and the white 2-way 1704853 on the 5 V output. The pigtail is the rev B one, a USB-C plug on two bare 22 AWG leads, which push into the plug. It is 0.25 m long and nothing else holds it to the board: a plain plug keeps it in J4 by contact friction and a latching plug by its latch.

The latching plug is Phoenix's `-PL-` series, which adds two pivoting side arms to the `-P-` plug. Squeezing the outer ends of the arms releases it.

| Use | Part | Order no. |
|---|---|---|
| J3, 24 VAC, 2-way black | PTSM 0,5/2-PL-2,5 BK | 1709442 |
| J4, 5 V, 2-way white | PTSM 0,5/2-PL-2,5 WH | 1709457 |
| H1, H2 probes, 3-way black | PTSM 0,5/3-PL-2,5 BK | 1709443 |

**The latch engages this header.** Mating Phoenix's STEP models of the plug (`pxc_1709442_05_01_PTSM-0-5-2-PL-2-5-BK_3D.stp`) and the header, with the plug's nose on the bottom of the header's cavity at y 4.5:

| Feature | Plug | Header |
|---|---|---|
| Catch | a tooth on the inside of each arm tip, 0.53 deep, 0.72 long, 0.8 tall | a window through each side wall, y 1.2 to 2.1, z 1.6 to 2.65, in a wall 0.52 thick |
| Position when mated | tooth at y 1.28 to 2.00, z 1.85 to 2.65 | the window encloses it with 0.08 in front and 0.10 behind |
| Arm tip | ends at y 2.0 | the front lug starts at y 2.1 |

The tooth passes through the full thickness of the wall. The arms clear the solder anchors, whose plates start at y 2.7. Phoenix's datasheets agree: the plug's derating curve is captioned "PTSM 0,5/...-PL-2,5 WH with PTSM 0,5/...-HH-2,5-SMD WH" (1709459, page 3), and the header's datasheet lists 1709457 among its accessories (1814919).

| Plug envelope | Value |
|---|---|
| Width | a + 11.8: 14.3 on a 2-way, 16.8 on a 3-way |
| Length | 15.9, of which 11.4 stands outside the board edge |
| Height | 5.2 |

Availability is unconfirmed. The layout of §4 takes either plug, so the choice can wait for the order.

## 6. Parts list

Quantities are for one EXT board. Buy one spare of each header.

| Ref | Part | Qty | Digi-Key | Amazon |
|---|---|---|---|---|
| H1, H2 | Phoenix PTSM 0,5/3-HH-2,5-SMD R32, 1778777, black | 2 | [Phoenix page](https://www.phoenixcontact.com/en-us/products/pcb-header-ptsm-05-3-hh-25-smd-r32-1778777); search Digi-Key for 1778777 | [search](https://www.amazon.com/s?k=Phoenix+Contact+1778777) |
| J3 | Phoenix PTSM 0,5/2-HH-2,5-SMD R32, 1778764, black | 1 | [Phoenix page](https://www.phoenixcontact.com/en-pc/products/pcb-header-ptsm-05-2-hh-25-smd-r32-1778764); search Digi-Key for 1778764 | [search](https://www.amazon.com/s?k=Phoenix+Contact+1778764) |
| J4 | Phoenix PTSM 0,5/2-HV-2,5-SMD WH R24, 1778696, white | 1 | [Phoenix page](https://www.phoenixcontact.com/en-pc/products/pcb-header-ptsm-05-2-hv-25-smd-wh-r24-1778696); search Digi-Key for 1778696 | [search](https://www.amazon.com/s?k=Phoenix+Contact+1778696) |
| plugs | PTSM 0,5/3-P-2,5 1778845, 0,5/2-P-2,5 1778832 and 0,5/2-P-2,5 WH 1704853 | 0 | on hand from rev A and rev B | |
| latching plugs, optional | 1709443 for H1 and H2, 1709442 for J3, 1709457 for J4 | 2 + 1 + 1 | search Digi-Key for the order number | [1709443](https://www.amazon.com/s?k=Phoenix+Contact+1709443), [1709442](https://www.amazon.com/s?k=Phoenix+Contact+1709442), [1709457](https://www.amazon.com/s?k=Phoenix+Contact+1709457) |

The Digi-Key product pages would not open on 2026-09-27 and no Amazon listing was found, so stock and price are unchecked. Phoenix's packing unit of 600 applies to factory orders; distributors sell cut tape. Every other EXT part is the rev B part (`docs/rpi-io-boards-revb-plan.md` §7).

## 7. Soldering the header by hand

OSH Park boards come without a stencil, so the header is soldered with an iron. The body is LCP and rated for three reflow cycles.

1. Tin one anchor pad.
2. Seat the header with both pegs in their holes and the face on the board edge.
3. Reflow the tinned anchor while pressing the body flat.
4. Check that the body sits flat and square, then solder the second anchor.
5. Solder the signal leads from behind the body.
6. Pull on a seated plug in every direction; the body must not move.

## 8. Work plan

1. Add `ptsm_hh_smd(board, n)` to `hardware/gen-boards.py` from §3, with the peg holes unplated.
2. Add `ptsm_hv_smd(board, n)` from §4.2. Place H1, H2, J3 and J4 per §4, make PF1 8 × 3, and remove H3, U2, C2, JP2 and TS1.
3. Add the silkscreen legends of §4.1 in bold. J4's legend has 11.9 mm between the lower rib and the proto field, so its text height is the largest that fits 16 characters in that length, about 1 mm.
4. Move the probe row clear of the header pads and rerun `hardware/build.sh` until DRC is clean.
5. Check the footprints against the STEP models in KiCad's 3D viewer: pegs in holes, anchors on pads, face on the edge.
6. Print the top copper at 1:1 and lay a header on it before ordering.
7. Order the board and the headers, populate per §7 and the rev B plan, and bench-prove as rev B was.

## 9. Open questions

- Whether the `-PL-` latching plugs can be bought (§5).
