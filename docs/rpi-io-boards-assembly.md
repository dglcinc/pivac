# Raspberry Pi I/O boards, rev A — assembly

Build flattest to tallest so each board rests on the bench while you solder from the back.
Do the EXT board first because its one surface-mount chip wants a bare board. Fit the Pi
socket last because once it is on, the INT board lies flat on neither face. Chips stay out
of their sockets until the unpowered check passes. Populate one of each board; the other
two of each are spares.

Tools: iron, solder, flush cutters, small pliers, meter with continuity and diode modes,
the spare Pi as a soldering jig and test host. Every part below is from the Mouser order
(shipped 2026-09-14, PDF in OneDrive) unless the notes say otherwise; the field plugs, probe plugs and Pi socket
can move over from the built boards.

## EXT board (38.5 × 85 mm, DS2482 1-wire master)

Component side up, probe headers at the top edge. U2, C2 and R1 are placed on the
silkscreen but stay empty.

| Ref | Part fitted | Where |
|---|---|---|
| U1 | Analog Devices DS2482S-100+ (SOIC-8) | under the probe headers |
| JP2 | solder jumper, three pads (copper on the board) | mid field, beside the U2 outline |
| JP1 | solder jumper, two pads (copper on the board) | near J1 |
| C1 | KEMET SMR5104J50J01L4 film, 100 nF 50 V, 5 mm pitch | beside U1 |
| H1, H2, H3 | Phoenix PTSM 0,5/3-HH-2,5-THR, from stock (not in the Mouser order) | top edge, entries over the edge |
| J1 | Phoenix PTSM 0,5/5-HH-2,5-THR white, 1814870 | against the riser field, entry facing the INT board |
| J2 | bare pads |  |

1. **U1.** Tack one corner pin, square the body to the silkscreen outline, then the other seven. Pin 1 dot to the silkscreen mark. Sets address 0x18.
2. **JP2.** Bridge the **centre pad to the left pad** (pad 1, DATA). That puts H3 on the shared bus. Left open, H3 floats. The right pad is the unfitted U2.
3. **JP1.** Leave open. Bridging it joins GPIO 4 to DATA for the software rollback only.
4. **C1.** No polarity. Seat it flat.
5. **H1, H2, H3.** Solder one pin, check the header sits flush and square to the edge, then the rest. H1 is the trunk: VCC · DATA · GND left to right.
6. **J1.** Same one-pin-first check. 3V3 · SDA · SCL · GPIO4 · GND.
7. **J2.** Nothing to fit; VCC, DATA, GND for a scope.

Bench check on the spare Pi before the swap, per `ds18b20-bus-topology.md` §8:
`i2cdetect -y 1` answers at 0x18, then a probe on H1 enumerates under
`/sys/bus/w1/devices/`. A chip that answers `i2cdetect` but logs `DS2482 reset failed`
has VCC or GND open: measure 3.3 V between chip pins 1 and 3 before anything else.

## INT board (59 × 85 mm, relay inputs and 24 VAC sense supply)

Component side up, field plugs at the top edge. The solder side faces the Pi, so every
tail on it is trimmed flush before the Pi socket goes on. J7 stays empty; J8, J9 and
TP1–TP3 are bare pads.

| Ref | Part fitted | Where |
|---|---|---|
| R1–R12 | Ohmite OK1235E-R52, 12 kΩ 1/4 W axial | four beside each DIP outline: R1–R4 at U1, R5–R8 at U2, R9–R12 at U3 |
| D1–D4 | Diotec 1N4007, DO-41 axial | one column, bottom right |
| F1 | Littelfuse 60R010XU PTC, 0.1 A 60 V | beside C1, between J4 and J6 |
| C1 | Vishay MAL202138101E3, 100 µF 63 V axial electrolytic, ⌀8 × 18 mm | between J4 and J6, lying flat |
| U1–U3 sockets | Adam Tech ICS-316-T, DIP-16 | column at x 10.5–28, one per row |
| J1–J4 | Phoenix PTSM 0,5/4-HH-2,5-THR white, 1814867 | top edge, entries over the edge |
| J6 | Phoenix PTSM 0,5/5-HH-2,5-THR white, 1814870 | right edge, inside the housing slot, entry facing the edge |
| trim | flush cutters | whole solder side |
| J5 | Phoenix PSTD 0,65X0,65/40-2,54 socket, 2202992 (Mouser 651-2202992, or freed from the built board) | **solder side**, at the Pi header position; soldered from the component side |
| U1–U3 | Lite-On LTV-847 | into the sockets |

1. **R1–R12.** Lie flat. No polarity.
2. **D1–D4.** Lie flat. **Band to the silkscreen bar.** A reversed diode reads as a dead board at power-up.
3. **F1.** Bend the leads and lay the disc flat; it must stay under 8 mm. No polarity.
4. **C1.** **Polarised:** the stripe and the shorter lead are negative (COM); match the + mark on the silkscreen.
5. **U1–U3 sockets.** Notch to the silkscreen. Two diagonal corner pins, check it sits flat, then the other fourteen. Chips stay out.
6. **J1–J4.** One pin first, check flush and square, then the rest. J1 ZV·DHW·BLR·COM, J2 CHIL·BOS1·BOS2·COM, J3 DEHUM·SCALA·HPHEAT·COM, J4 24VAC·24VAC·SP-D·COM. J2.1 (CHIL) is `HPCALL`; J4.3 (SP-D, BCM 19) is `DHWX`. **J4.2 carries no silkscreen label** (a rev A defect; only pins 1, 3 and 4 of J4 are marked), so J4 reads 24VAC · blank · SP-D · COM. The transformer's two wires go to J4.1 and J4.2. Neither is COM: the pair feeds the bridge, and COM is the bridge's negative output. A return landed on J4.4 shorts the transformer through one diode and the PTC on every negative half-cycle; the PTC took that for several minutes on 2026-09-25 and recovered.
7. **J6.** Same check. 3V3·SDA·SCL·GPIO4·GND, the link to the EXT board.
8. **trim.** Cut every tail flush. The Pi's Ethernet jack sits over the bottom-left field, and its USB shells are Pi ground while the rectifier nets are 35 V above COM.
9. **J5.** Seat the socket on the spare Pi's GPIO header, drop the board over it, solder all 40 pins. The Pi holds it square for the 16 mm stack. Pin 1 is the **top-right pad with the component side up and the plugs facing away.** Pins 1, 9, 25 and 39 are open on the board by design.
10. **U1–U3.** Only after the unpowered check below. Notch to the socket notch. U1 serves J1 and CHIL; U2 BOS1, BOS2, DEHUM, SCALA; U3 HPHEAT, SP-D, SP-C, SP-E.

## Checks

`docs/rpi-io-boards-reva-tone-map.svg` (generated by the `.gen.py` beside it from the KiCad
netlist) draws the board component side up, plugs at the top, header at the left, with what
every socket contact, plug position, header pin, J8 pad and test point tones to. Socket pins
count 1–8 along the bottom row from the left and 9–16 along the top row from the right, so 16
sits beside the notch. **Every continuity check is made with the board off the Pi.** On the
header, the SoC's protection diode from ground to each GPIO conducts under the meter's test
current, so every C contact tones to TP3 and the check tells nothing.

**Unpowered, no chips (INT).** Follow `rpi-io-board-design.md` step 7, with rev A's values
in place of the perfboard's: about 12 kΩ from each plug position to its channel's K-pin
socket contact (perfboard: 4.7 kΩ), a beep from each A-pin contact to TP1 (VS), a beep from
each E-pin contact to TP3 (Pi GND), and a beep from each C-pin contact to its Pi header
pin (ZV 11, DHW 13, BLR 15, CHIL 22, BOS1 31, BOS2 29, DEHUM 32, SCALA 16, HPHEAT 18,
SP-D 35, SP-C 33, SP-E 36; the J9 shadow pads carry none of these). TP2 (COM) must not
beep to TP3: COM is the sense return and never Pi ground.

**Powered, no chips (INT).** 24 VAC on J4.1 and J4.2: about 35 V DC between TP1 and TP2
(perfboard: 14 V; the first rev A board read 37.1 V from an unloaded transformer). Zero means
a reversed diode or an open PTC.

**Chips in (INT).** Step 8 of the same doc: board on the bench Pi, short each plug position to
COM at the plug, and `scripts/io-board-test.py` reads the channel. Its default map is rev A
(`--perfboard` selects the old board's); the SP-C and SP-E channels are shorted at the J8 pads.
Before trusting a channel that reads low at idle, read the same pin on the bare Pi: a pin that
stays low with nothing on the header is a dead pad on the Pi, not a board fault.

**EXT.** The bench check above.

**Link cable.** Five 22 AWG wires about 60 mm long with a Phoenix PTSM 0,5/5-P-2,5 plug
(1704858, white) on each end, 3V3 · SDA · SCL · GPIO4 · GND straight through.

**Bench Pi.** The bench card is Raspberry Pi OS Lite 64-bit (Trixie, 2026-09-15 image) with a
cloud-init first boot: hostname `pibench`, user `pi`, password `pivac-bench`, the M2's keys,
SSH and I2C on, `io-board-test.py` copied to the home directory; it boots any Pi 3, 4 or 5 and
takes a DHCP lease on Ethernet. Reach it as `pi@pibench.local` or by its lease on the UCG. The
Pi 4 with MAC `dc:a6:32:19:12:ee` (the DS18B20 calibration Pi) has **BCM 13, 16 and 25 dead**,
low under pull-up and pull-down with nothing on the header, so it cannot bench-test CHIL, SP-C
or SP-E. Use another Pi for those three or prove them at the swap.

**Bench record, INT and EXT board 1, 2026-09-25.** INT: 37.1 V DC on TP1–TP2; ZV, DHW, BLR,
BOS1, BOS2, DEHUM, SCALA, HPHEAT and SP-D each pulled their own pin low on a plug short and
released clean, with no neighbour dropping. CHIL, SP-C and SP-E are unproven on the bench
because of the Pi above; CHIL's proof is `HPCALL` reading 1 on the first call after the swap,
SP-C's is `HPCOOL` once wired. EXT: DS2482 at 0x18, instantiated with no reset failure, probe
`0516a36816ff` enumerated with clean CRCs on H1, H2 and H3, so JP2 is bridged right.

**Into the housing.** `rpi-io-boards-pcb-plan.md` §6 steps 6–8: freeze the services, swap
the pair, move the four field plugs and three probe plugs over, prove every channel and the
1-wire bus, then release. `HPCOOL` (BCM 13) has no header on rev A: wire it to `SP-C` on
the J8 pads.
