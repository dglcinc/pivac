# Raspberry Pi I/O Boards — Rev C Plan

**Status:** Plan. Nothing generated or ordered. Rev B is on order and is fitted first; rev C follows it on EXT only. · **Owner:** David

Rev C replaces every edge connector on the EXT board with the surface-mount PTSM header, mounted with its entry face flush with the board edge. The through-hole headers on rev A fold at their pins when a plug is levered, because one row of pins is all that holds them. The surface-mount header sits flat on the board and is held at four places. The rev B design is `docs/rpi-io-boards-revb-plan.md`; this document states only what rev C changes.

**Rule for the EXT board from rev C on: every edge connector is a PTSM 0,5/n-HH-2,5-SMD header, flush with the edge.** A new edge connector on EXT takes this part and the footprint of §3.

---

## 1. Scope

**In scope.** On EXT: H1 and H2 become 3-way surface-mount headers on the top edge, J3 becomes a 2-way surface-mount header on the bottom edge, and all three sit with the entry face on the board edge. H3 leaves the board with U2, C2 and JP2. The probe parts under the sockets move toward the upper rib to clear the header pads. A new footprint generator in `hardware/gen-boards.py` builds the surface-mount header.

**Out of scope.** The INT board stays at rev B. The power section, the GH link, J4, the tie slots and the title block on EXT keep their rev B nets and parts. No change to `pivac`, `config.yml`, InfluxDB or Signal K. The plugs in service carry over.

**Boundaries assumed.**

- The housing accepts a plug with the header's entry face on the board edge, 1.7 mm further in than rev B (David, 2026-09-27).
- Both ends of EXT are open, so the sockets may move along the top edge.
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

The board is 38.5 × 85 mm and the top edge carries two probe sockets. Three 3-way headers would need 39.3 mm over their anchors.

| Ref | Part | Centre x | Edge | Pins |
|---|---|---|---|---|
| H1 | 3-way, black | 7.57 | top, entry toward −y | VCC · DATA · GND |
| H2 | 3-way, black | 21.5 | top, entry toward −y | VCC · DATA · GND |
| J3 | 2-way, white | 6.75 | bottom, entry toward +y | 1 hot at x 8.0, 2 common at x 5.5 |

- H1 keeps its rev B centre. Its anchors span x 1.02 to 14.12.
- H2 moves 1.23 mm right of its rev B centre, which leaves 0.83 mm between its anchor and H1's.
- J3 moves 0.5 mm left of its rev B centre so its anchor pad clears the proto field at x 13.0.
- The header pads on the top edge end at y 9.8. C1, R1 and the parts beside them sit at y 10.4 to 11.0 on rev B and move to y 11.6 or beyond. The upper rib starts at y 18.11, so the row has 7.6 mm.
- J3's pads end 9.8 mm in from the bottom edge, at y 75.2. The proto field and the tie slots keep their rev B positions.
- The top edge right of x 28.6 is free.

## 5. Plugs

The PTSM `-P-` plugs in service fit the surface-mount header and carry over: the black 3-way 1778845 on the probe sockets and the white 2-way 1704853 on the 24 VAC entry.

The latching plug that mates with this header is Phoenix's `-PL-` series, which adds two side arms to the `-P-` plug and releases by hand:

| Use | Part | Order no. |
|---|---|---|
| J3, 24 VAC, 2-way white | PTSM 0,5/2-PL-2,5 WH | 1709457 |
| 2-way black | PTSM 0,5/2-PL-2,5 BK | 1709442 |
| H1, H2 probes, 3-way black | PTSM 0,5/3-PL-2,5 BK | 1709443 |

Phoenix's datasheets pair the two: the plug's derating curve is captioned "PTSM 0,5/...-PL-2,5 WH with PTSM 0,5/...-HH-2,5-SMD WH" (1709459, page 3), and the surface-mount header's datasheet lists 1709457 among its accessories (1814919). Neither shows the latch engaged. The header's side lugs are what the arms would catch: each side has a lug at y 2.1 to 3.4 standing 1.35 mm proud of the body from z 1 to 4, and the plug's arms reach 4.5 mm past its body. Rev B makes the 24 VAC plug white and the probe plugs black, so J3 takes 1709457. Availability is unconfirmed; the board is the same with either plug, so the choice can wait for the order.

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
2. Place H1, H2 and J3 per §4 and remove H3, U2, C2 and JP2 with their nets.
3. Move the probe row clear of the header pads and rerun `hardware/build.sh` until DRC is clean.
4. Check the footprint against the STEP model in KiCad's 3D viewer: pegs in holes, anchors on pads, face on the edge.
5. Print the top copper at 1:1 and lay a header on it before ordering.
6. Order the board and the headers, populate per §7 and the rev B plan, and bench-prove as rev B was.

## 9. Open questions

- Whether the `-PL-` latching plugs can be bought (§5).
- Whether INT follows. Four 4-way surface-mount headers need 62.4 mm against the 59 mm board, so INT needs its own arrangement, such as two 8-way headers at 25.6 mm each.
