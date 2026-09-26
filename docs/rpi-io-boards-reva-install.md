# Rev A boards into the housing — plug wiring and label

Bench sheet for swapping the perfboard pair for the rev A INT and EXT boards. The boards are
fully proven (all twelve channels on the new bench Pi, 2026-09-26; `rpi-io-boards-assembly.md`).
The Pi in the housing stays, and so do every channel's BCM pin and Signal K path, so nothing
downstream moves. What changes is J4, the sense supply, and where `HPCOOL` lands.

## 1. What changes

| Item | Perfboard (in the housing now) | Rev A |
|---|---|---|
| Sense supply | 12 V wall wart (14.7 V DC) on J4.1 (+) and J4.4 (−) | 24 VAC class 2 transformer on J4.1 and J4.2; the board rectifies it (about 35 V DC on TP1–TP2) |
| `HPCOOL` (BCM 13) | J4.2 | J8 pigtail, position 1 (SP-C); rev A has no plug position left for it |
| J4.2 | `HPCOOL` | second transformer wire; **no silkscreen label** on rev A, J4 reads 24VAC · blank · SP-D · COM |
| J4.4 | wall wart − | nothing, or a relay common (it is COM, the same net as J1.4, J2.4, J3.4) |
| J1–J3 | | position for position unchanged |
| `HPHEAT`, `DHWX` | J3.3, J4.3 | unchanged |
| Pi power | USB-C through the `PivacPower` Shelly | unchanged |
| 1-wire | EXT perfboard, H1 trunk plug | rev A EXT board, same H1 plug, same 5-way link cable |

The transformer's two wires are the AC pair into the bridge; **neither is COM**. A return landed
on J4.4 shorts the transformer through one diode and the PTC on every negative half-cycle (the
PTC took that for several minutes on 2026-09-25 and recovered). The transformer plugs into the
`PivacPower` outlet so the board loses and regains power with the Pi.

## 2. Plug map, position by position

Positions are counted left to right on the footprint in the board's top view, whatever the plug
body prints. Silkscreen names that differ from the config name are in brackets.

| Position | Wire tagged | BCM | Phys | Action |
|---|---|---|---|---|
| J1.1 | ZV | 17 | 11 | replug |
| J1.2 | DHW | 27 | 13 | replug |
| J1.3 | BLR | 22 | 15 | replug |
| J1.4 | COM | | | replug |
| J2.1 | HPCALL (CHIL) | 25 | 22 | replug |
| J2.2 | BOS1 | 6 | 31 | replug |
| J2.3 | BOS2 | 5 | 29 | replug |
| J2.4 | COM | | | replug |
| J3.1 | DEHUM | 12 | 32 | replug |
| J3.2 | SCALA | 23 | 16 | replug |
| J3.3 | HPHEAT | 24 | 18 | replug |
| J3.4 | COM | | | replug |
| J4.1 | 24 VAC (24VAC) | | | **new**: transformer wire 1; the wall wart + comes out |
| J4.2 | 24 VAC (unlabelled) | | | **new**: transformer wire 2; `HPCOOL` comes out |
| J4.3 | DHWX (SP-D) | 19 | 35 | replug |
| J4.4 | COM | | | **empty** unless a common is grouped here; the wall wart − comes out |

### J8 pigtail (PTSM-3 header in the EXT proto field, wired to the INT board's J8 pads)

| Position | Wire tagged | BCM | Phys | Action |
|---|---|---|---|---|
| 1 | HPCOOL (SP-C) | 13 | 33 | **move** from the perfboard's J4.2 |
| 2 | SP-E | 16 | 36 | spare, empty |
| 3 | COM | | | the `HPCOOL` relay's common, if it is not already on a J1–J3 COM |

Every COM is one net (the bridge's negative), so one common may serve all the relays and land
on any position 4 or on pigtail 3. Strain-relieve the pigtail and every cable at the housing
entry. Ferrules on stranded conductors; 22 AWG solid goes in bare. Anything still landed that is
not in these tables is a retired run: coil and tag it, do not land it.

## 3. Order of work

1. Freeze: `sudo systemctl stop pivac-gpio pivac-1wire`, then the clone (`sd-clone.service`
   or `rpi-clone` by hand) so a bad hour is one card swap away.
2. Power off: the CDP control-power breaker (the relay coils and the 24 VAC), then the
   `PivacPower` Shelly (the Pi, the wall wart and the transformer). Confirm 0 V on the wart
   leads and the transformer secondary before touching a plug.
3. Pull the four PTSM plugs and the H1 plug from the perfboards. Unplug the link cable. Lift
   the Pi off the INT perfboard; lift the EXT perfboard from its slot.
4. Seat the Pi on the rev A INT board's socket (all 40 pins; the Pi holds the stack square),
   drop the pair into the housing, EXT board into its slot with H1–H3 at the short-end opening,
   link cable J6 to the EXT link header, 3V3 · SDA · SCL · GPIO4 · GND straight through.
5. Rewire the plugs per §2: J1–J3 as they are; J4.1 and J4.2 take the transformer, `HPCOOL`
   moves to pigtail 1, J4.4 empties. Land the transformer **last**.
6. Meter checks, plugs in, everything unpowered:
   - each channel position to its plug's COM: open, or the relay's contact resistance if that
     relay is closed; never a dead short from a relay that should be open;
   - any COM to Pi ground (a header ground pad or a USB shell): **open**; a beep is a common
     still on Pi ground;
   - J4.1 to J4.2: open with the transformer not landed; J4.1 or J4.2 to J4.4: open.
7. Land the transformer, power the `PivacPower` outlet, read about 35 V DC between TP1 (VS)
   and TP2 (COM). Zero is a reversed diode or an open PTC; 37 V unloaded is normal.
8. Plug H1: VCC · DATA · GND left to right in the plug, which reads GND · DATA · VCC from the
   front with the board solder side out. H2 and H3 stay empty.
9. Fit the label under the clear cover. Power the CDP control breaker.
10. `sudo systemctl start pivac-gpio pivac-1wire` and prove:
    - the 1-wire bus: eight probes with clean CRCs (`ls /sys/bus/w1/devices/`, then
      `environment.inside.hvac.*` fresh in Signal K);
    - every relay path under `electrical.ac.switch.utility.*.statenum` publishing; `HPCALL`
      reading 1 on the first call after the swap, `HPHEAT` or `HPCOOL` reading 1 for whichever
      mode the HZ-432 is in, `DHWX` on the next refused DHW call;
    - Sentry `decodeMargin` still 40–60 and `registrationScore` above 0.6, since work in the
      boiler room bumps the camera.

## 4. Label

`docs/PhoenixContact-BC-RPI-label.gen.py` carries the rows; run it and print the docx from
Word. The rev A rows are: J1 ZV · DHW · BLR · COM, J2 HPCALL · BOS1 · BOS2 · COM, J3 DEHUM ·
SCALA · HPHEAT · COM, J4 24VAC · 24VAC · DHWX · COM, then the J8 pigtail HPCOOL · SP-E · COM,
then H1–H3 and LINK, then the Pi's `eth0` MAC `2c:cf:67:80:55:00`, which does not change. The
label uses the config names (`HPCALL`, `DHWX`, `HPCOOL`); the silkscreen says CHIL, SP-D and
SP-C for the same positions, and this sheet is the cross-reference. The empty rectangle on the
page is the label's bounding box, so the rows carry no spacers and no words beyond the name.
