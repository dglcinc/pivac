# Raspberry Pi I/O Boards — Rev C Plan

**Status:** Plan. Nothing generated or ordered. Rev B is on order and is fitted first; rev C follows it on EXT only. · **Owner:** David

Rev C replaces every edge connector on the EXT board with the surface-mount PTSM header, mounted with its entry face flush with the board edge. The through-hole headers on rev A fold at their pins when a plug is levered, because one row of pins is all that holds them. The surface-mount header sits flat on the board and is held at four places. The rev B design is `docs/rpi-io-boards-revb-plan.md`; this document states only what rev C changes.

**Rule for the EXT board from rev C on: every edge connector is a PTSM 0,5/n-HH-2,5-SMD header, flush with the edge.** A new edge connector on EXT takes this part and the footprint of §3.

---

## 1. Scope

**In scope.** On EXT: H1 and H2 become 3-way surface-mount headers on the top edge, J3 becomes a 2-way surface-mount header on the bottom edge, and all three sit with the entry face on the board edge. H3 leaves the board with U2, C2 and JP2. The probe parts under the sockets move toward the upper rib to clear the header pads. A new footprint generator in `hardware/gen-boards.py` builds the surface-mount header.

**Out of scope.** The INT board stays at rev B: the enclosure supports its plugs on both sides, so its headers do not fold. The link between the boards stays the JST GH of rev B, which is lower than a PTSM header. The power section, the GH link, J4, the tie slots and the title block on EXT keep their rev B nets and parts. No change to `pivac`, `config.yml`, InfluxDB or Signal K. The plugs in service carry over.

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
| H1 | 3-way, black | 9.0 | top, entry toward −y | VCC · DATA · GND |
| H2 | 3-way, black | 26.5 | top, entry toward −y | VCC · DATA · GND |
| J3 | 2-way, white | 8.0 | bottom, entry toward +y | 1 hot at x 9.25, 2 common at x 6.75 |

- H1 and H2 stand 17.5 mm apart, centre to centre, so two latching plugs sit side by side with 0.7 mm between them. Their anchors span x 2.45 to 15.55 and x 19.95 to 33.05.
- A latching plug on H1 reaches x 0.6 and one on H2 reaches x 34.9, both inside the board's width.
- J3 sits at x 8.0 so a latching plug on it reaches x 0.9 on the left. Its anchor pads span x 3.0 to 13.0.
- The proto field PF1 becomes 5 × 4 and starts at x 15.54, one column right of rev B, which clears J3's anchor pad and the tie slots.
- The header pads on the top edge end at y 9.8. C1, R1 and the parts beside them sit at y 10.4 to 11.0 on rev B and move to y 11.6 or beyond. The upper rib starts at y 18.11, so the row has 7.6 mm.
- J3's pads end 9.8 mm in from the bottom edge, at y 75.2. The tie slots keep their rev B position.

## 5. Plugs

The PTSM `-P-` plugs in service fit the surface-mount header and carry over: the black 3-way 1778845 on the probe sockets and the white 2-way 1704853 on the 24 VAC entry.

The latching plug is Phoenix's `-PL-` series, which adds two pivoting side arms to the `-P-` plug. Squeezing the outer ends of the arms releases it.

| Use | Part | Order no. |
|---|---|---|
| J3, 24 VAC, 2-way white | PTSM 0,5/2-PL-2,5 WH | 1709457 |
| 2-way black | PTSM 0,5/2-PL-2,5 BK | 1709442 |
| H1, H2 probes, 3-way black | PTSM 0,5/3-PL-2,5 BK | 1709443 |

Rev B makes the 24 VAC plug white and the probe plugs black, so J3 takes 1709457.

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
| J3 | Phoenix PTSM 0,5/2-HH-2,5-SMD WH R32, 1708004, white | 1 | [Phoenix page](https://www.phoenixcontact.com/en-us/products/pcb-header-ptsm-05-2-hh-25-smd-wh-r32-1708004); search Digi-Key for 1708004 | [search](https://www.amazon.com/s?k=Phoenix+Contact+1708004) |
| plugs | PTSM 0,5/3-P-2,5 1778845 and 0,5/2-P-2,5 WH 1704853 | 0 | the ones in service move over | |
| latching plugs, optional | 1709443 for H1 and H2, 1709457 for J3 | 2 + 1 | search Digi-Key for the order number | [1709443](https://www.amazon.com/s?k=Phoenix+Contact+1709443), [1709457](https://www.amazon.com/s?k=Phoenix+Contact+1709457) |

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
2. Place H1, H2 and J3 per §4, make PF1 5 × 4, and remove H3, U2, C2 and JP2 with their nets.
3. Move the probe row clear of the header pads and rerun `hardware/build.sh` until DRC is clean.
4. Check the footprint against the STEP model in KiCad's 3D viewer: pegs in holes, anchors on pads, face on the edge.
5. Print the top copper at 1:1 and lay a header on it before ordering.
6. Order the board and the headers, populate per §7 and the rev B plan, and bench-prove as rev B was.

## 9. J4 as a PTSM header, under consideration

J4 is the 5.1 V output to the Pi's USB-C pigtail, a JST B2B-XH-A on rev B. The candidate is the vertical surface-mount header of the same family, PTSM 0,5/2-HV-2,5-SMD WH R24, 1778696, measured from Phoenix's STEP model (`pxc_1778696_02_00_PTSM-0-5-2-HV-2-5-SMD-WH-R24_3D.stp`).

| Item | PTSM HV, 2-way | JST XH, 2-way |
|---|---|---|
| Footprint | 10.6 × 7.1 | 7.5 × 5.75 |
| Height of the header | 7.5 | 7.0 |
| Height with a plug seated | 18.4 | 9.8 |
| Fixing | two anchors, two pegs, two leads | two through-hole pins |
| Rating | 6 A | 3 A |
| Plug | the same `-P-` and `-PL-` plugs as J3 | crimped XH housing |

- The body is 6.7 × 5.0, the anchors make it 10.6 wide, and the leads leave one long side by 2.1 mm.
- The pegs are ⌀0.8 at 1.4 mm outside the outer pins and 0.4 mm from the long side opposite the leads.
- The side walls carry the same latch window as the horizontal header, 1.2 to 2.1 mm below the top face, so the latching plug fits.
- The housing gives EXT 30 mm, so the 18.4 mm standing plug fits.
- At J4's place the header sits at centre x 29.0 with its body at y 66.0 to 71.0 and its leads toward the tie slots. C4 moves 1.6 mm left to clear the anchor pad.
- The tie slots TS1 go with this change. They exist to keep the pigtail's weight off J4's two through-hole pins; the PTSM header is held by its anchors and pegs, and a latching plug holds the cable in it. With a plain plug the cable is held by contact friction alone, so the slots go only with a latching plug on J4.
- Without the slots the proto field can grow from 5 × 4 to 8 × 4, from x 15.54 to x 33.32.

**J3's plug would fit J4.** Both would be 2-way PTSM, and the rev B design relies on J3's plug not fitting J4. The 24 VAC plug seated in J4 puts 36 V peak across U3's output and C4. The Pi is not at risk, because its pigtail is then unplugged. A plug does not enter a header with more positions: the header's floor ribs stand 1.02 mm high and the plug's nose rides 0.70 mm above the floor, so the models interfere by 0.3 mm.

| Option | How it prevents the wrong plug | Cost |
|---|---|---|
| 4-way J4, +5 V on two positions and GND on two | the 2-way and 3-way plugs do not fit | 15.6 mm wide, so J2 moves to the free top-right corner and C4 moves 4 mm left |
| 2-way J4 in the other colour from J3 | by eye only | none |
| J4 stays JST XH | different family | none |

## 10. Open questions

- Whether the `-PL-` latching plugs can be bought (§5).
- Whether J4 becomes a PTSM header, and with how many positions (§9).
