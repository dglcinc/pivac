# DS18B20 Bus — Build Procedure

**Status:** Ready to build (EXT board + DS2482). Field-bus rules verified live on the Pi
(`10.0.0.82`, Pi 4 Model B, kernel `6.18.34+rpt-rpi-v8`). · **Owner:** David

Build procedure for the 1-wire side of the system: the **RPI-BC EXT-PCB HBUS SET** (Mouser
651-2202995) carrying the DS2482 converter, three 3-pin probe headers and a pluggable trunk
terminal; the field chain out to the eight probes; and the software switch from `w1-gpio` to
the DS2482. Design reasoning and the electrical background are in Appendix A.

---

## 1. How to read this document

**Holes are named `(column,row)`.** Hold the EXT board component side up with the "TOP"
marking upright — the TOP view of Phoenix drawing 00913308/02 (in
`~/OneDrive - DGLC/Claude/HVAC Manuals/`). Columns run 1–14 left to right, rows 1–32 top to
bottom. In this view the connector area lands at columns 13–14; that is the side you know as
the header side of the board as it sits in the housing.

**Three conductors everywhere.** The bus is always the same trio: **VCC** (3.3 V probe
power), **GND**, and **DATA** (the 1-wire line, called DQ in datasheets). On every header,
plug and cable in this document the order is VCC, DATA, GND.

**Faces and wire types** follow `docs/rpi-io-board-design.md` §1: components on the component
side, wires on the solder side; rails and one-hole stubs bare, everything else insulated
22 AWG solid; a wire never shares a hole with a pin — it lands on the copper ring beside the
pin's joint. "Ring (c,r)" below means exactly that.

## 2. What the finished system is

```
 Pi ──40-pin──► INT board ──four soldered wires──► EXT board ─► DS2482 ─► 1-wire bus
                (3V3 · GND · SDA · SCL — the I²C link)              │
                                                                    ├─► push terminal ──► TRUNK plug ──► field chain, 8 probes
                                                                    ├─► H1 (3-pin header — outdoor run, when restored)
                                                                    ├─► H2 (3-pin header — spare)
                                                                    └─► H3 (3-pin header — spare)
```

The DS2482 turns the Pi's I²C into 1-wire timing generated in hardware, with a driven rising
edge — which is what an eight-probe run in a mechanical room wants, and why the discrete
pull-up and the old GPIO 4 wiring come off the board. The **trunk plugs into the push
terminal**, so pulling one plug disconnects every probe from the Pi stack; the I²C link is
soldered and permanent. Sensors keep their `28-*` names, so pivac, the calibration offsets
and InfluxDB history are all untouched.

## 3. Parts

| Item | Part | Qty |
|---|---|---|
| 1-wire converter | **DS2482-100** (SOIC-8 on a DIP-8 adapter) | 1 |
| IC socket | DIP-8 | 1 |
| Trunk terminal | Phoenix **PTSM 0,5/3-HV-2,5-THR** print header (order no. 1778560 black / 1815277 white) | 1 |
| Trunk plug | Phoenix **PTSM 0,5/3-P-2,5** (order no. 1778845) | 1 |
| Probe headers | 3-position pin strips for the board's terminal area — the type the trunk uses today | 3 |
| Decoupling | 100 nF ceramic | 1 |
| Wire | insulated 22 AWG solid + a scrap of bare | — |

Removed, not added: the 2.2 kΩ pull-up and any series resistor — the DS2482 supplies its own
pull-ups and an external one fights it (Appendix A).

## 4. The EXT board's fixed features

### 4.1 The grid

14 columns × 32 rows of plated ⌀1.0 mm holes on a 2.54 mm pitch, isolated pads, no bus
strips. Three gaps in the grid: **column 12 has no holes in rows 10–22**, and columns 13–14
have none in rows 10–11 and 21–22. The gap column is useful: solder-side wires can cross it
freely, and nothing there can short.

### 4.2 The terminal area and its access pads

The 18-position terminal area is columns 13–14, rows 12–20 — two columns of nine, taking
3-position pin strips. Phoenix pre-routed access for each position:

- **Column-13 positions (the nine this build uses): access pads at (10,r) and (11,r)**, same
  row, electrically identical — use either. Verified against the drawing for rows 13–20;
  row 12 is checked with the meter in step 1.
- **Column-14 positions: not used in this build.** Their traces run to the pad groups at
  rows 8–9 and 23–24 (columns 10–14). The drawing is too dense to read those assignments
  reliably, so ring them out with a meter before ever using that half.

### 4.3 Keep-out areas (solder side)

| Area | Holes covered |
|---|---|
| Upper band | rows 7–8, full width |
| Lower band | rows 26–27, full width (pad edges of 25 and 27 graze it — keep joints flush there) |
| Right-edge margin | the hole-free strip beside column 14, rows 9–25 |

Everything this build places sits in rows 9–24, between the bands, so nothing crosses one.

## 5. Placement map

![EXT board placement map](ds18b20-ext-board-layout.svg)

*(Figure source: `docs/ds18b20-ext-board-layout.gen.py`.)*

### 5.1 DS2482 socket

DIP-8 socket at columns 5–8, rows 12–15, **notch DOWN** (pin 1 at bottom-right). The SOIC-8
sits on the adapter with its pin 1 on the adapter's pin 1 — check the adapter's marking.

| Hole | Pin | Name | Connects to |
|---|---|---|---|
| (8,15) | 1 | VCC | 3V3-in link from (8,16) |
| (8,14) | 2 | IO | the DATA net (wire W5) |
| (8,13) | 3 | GND | the GND net (wire W12) |
| (8,12) | 4 | SCL | SCL-in link from (8,11) |
| (5,12) | 5 | SDA | SDA-in link from (4,12) |
| (5,13) | 6 | PCTLZ | **nothing — leave open** |
| (5,14) | 7 | AD1 | GND (bare link + wire W13) |
| (5,15) | 8 | AD0 | GND (bare link to AD1) |

AD0/AD1 at ground set I²C address `0x18`, which the software step expects.

### 5.2 Trunk terminal

PTSM header pins into (4,18), (5,18), (6,18) = **VCC · DATA · GND** left to right. Label the
plug the same way — a reversed plug puts VCC on GND. The mechanical-room trunk lands in the
plug: VCC blue, DATA white/orange, GND orange + white/blue, per the cable table in §7.

### 5.3 Probe headers

Three 3-position strips in the column-13 terminal positions:

| Header | Pin holes | VCC · DATA · GND | Access pads (VCC / DATA / GND) | Use |
|---|---|---|---|---|
| **H1** | (13,12) (13,13) (13,14) | rows 12 · 13 · 14 | (10/11,12) · (10/11,13) · (10/11,14) | outdoor run, when restored |
| **H2** | (13,15) (13,16) (13,17) | rows 15 · 16 · 17 | (10/11,15) · (10/11,16) · (10/11,17) | spare |
| **H3** | (13,18) (13,19) (13,20) | rows 18 · 19 · 20 | (10/11,18) · (10/11,19) · (10/11,20) | spare / bench tap |

All three sit on the same bus as the trunk. An empty header adds nothing to the bus; a plug
only becomes a branch when a cable lands in it, so leave spares empty without concern.

### 5.4 The four-wire link from the INT board

Soldered permanently, routed between the two housings with strain relief at each entry. The
INT-board ends go into the access pads named in `docs/rpi-io-board-design.md` §4.2:

| Signal | INT board hole (Pi pin) | EXT board landing | Then |
|---|---|---|---|
| 3V3 | (5,2) — pin 1 | hole (8,16) | link ring (8,16) → ring (8,15) |
| GND | (5,6) — pin 9 | hole (10,14) | (this is H1's GND access pad — the GND net's feed point) |
| SDA | (5,3) — pin 3 | hole (4,12) | link ring (4,12) → ring (5,12) |
| SCL | (5,4) — pin 5 | hole (8,11) | link ring (8,11) → ring (8,12) |

### 5.5 Wires

Each access-pad pair gives one wire-in and one wire-out hole, so every net is a simple chain;
each hole takes exactly one wire end.

| Net | # | From | To |
|---|---|---|---|
| VCC | W1 | ring (8,16) | hole (10,12) |
| | W2 | hole (11,12) | hole (10,15) |
| | W3 | hole (11,15) | hole (10,18) |
| | W4 | hole (11,18) | ring (4,18) — terminal VCC |
| DATA | W5 | ring (8,14) — IO | hole (10,13) |
| | W6 | hole (11,13) | hole (10,16) |
| | W7 | hole (11,16) | hole (10,19) |
| | W8 | hole (11,19) | ring (5,18) — terminal DATA |
| GND | W9 | hole (11,14) | hole (10,17) |
| | W10 | hole (11,17) | hole (10,20) |
| | W11 | hole (11,20) | ring (6,18) — terminal GND |
| | W12 | ring (8,13) — GND pin | ring (10,14) |
| | W13 | ring (5,14) — AD1 | ring (10,17) |
| | bare | ring (5,14) | ring (5,15) — AD1 to AD0 |

Route the long vertical runs of W2/W3 just right of column 11, W6/W7 just left of column 10,
and W9/W10 through the empty column-12 gap — three separate lanes, no stacking. W13 runs
below the socket (row 16) and up to (10,17)'s ring. The 100 nF capacitor's legs land on the
rings of (11,12) and (11,14), body over the column-12 gap.

## 6. Build sequence

The bus is live today, so steps 2 onward take it down — do them in one sitting and expect the
30-minute freshness alerts if it runs long.

1. **Verify the maps, nothing soldered.** Adjacent free holes don't beep (no bus strips).
   Each column-13 position beeps to both its access pads — nine positions, (13,r)↔(10,r) and
   (13,r)↔(11,r) for r = 12…20 — and a deliberate wrong pair stays silent. Identify the
   DS2482's pins on the bench with the §5.1 table and the adapter's pin-1 mark.
2. **Strip the old arrangement.** Unplug the trunk, remove the 2.2 kΩ pull-up, the GPIO 4
   data wire and any series resistor from the board. Keep the pull-up in the spares box — it
   is the rollback part.
3. **Solder the fixed parts**, lowest first: the three probe-header strips, the DIP-8 socket
   (two diagonal pins, check flat, then the rest), the PTSM terminal. Chip stays out.
4. **Links, bare AD link, capacitor, then wires W1–W13** per §5.4–5.5, then the four
   link wires to the INT board.
5. **Check before the chip goes in.** Continuity: terminal VCC ↔ every VCC access pad and H
   VCC pin; same for DATA and GND. Silence between: VCC↔GND, VCC↔DATA, DATA↔GND, and every
   net ↔ PCTLZ (5,13). On the INT side: 3V3 arrives at socket pin 1's ring, and Pi ground at
   (10,14).
6. **Software, then chip.** Do §8's config edit and reboot with the socket still empty, then
   power off, seat the DS2482 (notch down), power up: `i2cdetect -y 1` shows `0x18`.
7. **Bring the bus up.** Instantiate per §8, plug the trunk in, and
   `cat /sys/bus/w1/devices/w1_bus_master1/w1_master_slave_count` reads **8**. All eight
   `28-*` names match the roster in CLAUDE.md, and Signal K values resume within one
   `pivac-1wire` cycle — no restart needed, the module re-scans every cycle.

## 7. The field bus

The rules, in build order — the reasons live in Appendix A:

1. **One trunk, no branches.** The cable leaves the trunk plug, visits each sensor location
   in physical order, and ends at the last one. Nothing branches at the board, no spur
   doubles back, nothing hangs open.
2. **A block at each location, not a hub at the Pi.** Four locations, four blocks: tees
   (`IN`, `OUT`), tank (`UBT`, `LBT`), loop A, loop B. Each block is three 4-way lever
   connectors — one per conductor — carrying trunk-in, trunk-out and its two probes. Add a
   **100 nF ceramic across VCC–GND at each block**.
3. **Trim every probe lead** to the shortest length that reaches its block. Coiled slack
   defeats the exercise.
4. **DATA and GND share one twisted pair; VCC rides in the same cable.** On CAT5e/6:
   white/orange = DATA, orange = GND, blue = VCC, white/blue = second GND. Green and brown
   pairs stay open at both ends; never put anything spare on DATA, and never pair DATA with
   VCC.
5. **Measure, don't estimate.** Multimeter in capacitance mode, far end open, DATA lifted at
   the board: DATA-to-GND across the installed cable. Under ~2 nF the DS2482 drives it with
   ease; the working record here is 1.75 nF measured, arithmetic in Appendix A.

```
   EXT board ═ trunk ═►│ BLOCK 1 │═►│ BLOCK 2 │═►│ BLOCK 3 │═►│ BLOCK 4 │ ends here
                       │  tees   │  │  tank   │  │ loop A  │  │ loop B  │
                          │  │        │  │        │  │        │  │
                         IN OUT     UBT LBT     A_SUP…     B_SUP…
```

Mechanical rules for anything in the utility room: every conductor in a screw or spring
terminal (no mid-air joints, no wire nuts), ferrules on stranded wire, strain relief at every
enclosure entry, each branch labelled with the probe name it serves
(`docs/PhoenixContact-BC-RPI-label.docx` convention).

## 8. Software

Facts already verified on this Pi: the kernel ships `ds2482.ko` (binds `ds2482` and
`ds2484`), its `active_pullup` defaults on, no device-tree overlay ships so the device is
instantiated over sysfs, and the live config file is `/boot/firmware/config.txt`
(`/boot/config.txt` is a do-not-edit stub). `/dev/i2c-20`/`21` are HDMI buses; the header
bus appears as `/dev/i2c-1`.

1. Edit `/boot/firmware/config.txt`: `dtparam=i2c_arm=on` (line 6), and comment out
   `dtoverlay=w1-gpio` under `[all]` (line 52) — two masters at once makes sensor ownership
   ambiguous. Reboot.
2. `sudo apt install -y i2c-tools`, then `i2cdetect -y 1` → device at `0x18`. Nothing there
   means AD0/AD1 aren't grounded or the chip isn't powered.
3. Instantiate: `sudo modprobe ds2482` then
   `echo ds2482 0x18 | sudo tee /sys/bus/i2c/devices/i2c-1/new_device` —
   `w1_bus_master1` reappears backed by the bridge, same `28-*` names.
4. Survive reboots: `echo ds2482 | sudo tee /etc/modules-load.d/ds2482.conf` and install
   `scripts/systemd/ds2482-init.service`:

```ini
[Unit]
Description=Instantiate the DS2482 1-Wire master on I2C
After=sysinit.target
Before=pivac-1wire.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'test -e /sys/bus/w1/devices/w1_bus_master1 || echo ds2482 0x18 > /sys/bus/i2c/devices/i2c-1/new_device'

[Install]
WantedBy=multi-user.target
```

```bash
sudo cp ~/github/pivac/scripts/systemd/ds2482-init.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now ds2482-init
```

Start ordering is a convenience: `pivac.OneWireTherm` re-scans the bus every cycle, so a
late-appearing master self-heals. No pivac code change, no `/etc/pivac/config.yml` edit — the
PR #122 calibration offsets key off the unchanged `28-*` names. With the DS2482 in,
`pivac/GPIO.py:17`'s vestigial `os.system('modprobe w1-gpio')` goes too.

## 9. Rollback

Uncomment `dtoverlay=w1-gpio`, refit the 2.2 kΩ pull-up from DATA to VCC on the EXT board,
and run a data wire from the INT board's GPIO 4 access pad — hole **(5,5)**, Pi pin 7 — to
the DATA net (land it on ring (10,13)). Reboot. `i2c_arm=on` and the module-load file are
harmless left in place.

---

## Appendix A — design decisions and electrical background

**Why the trunk is the pluggable part.** The DS2482 needs four conductors from the Pi (3V3,
GND, SDA, SCL), so a 3-pin disconnect cannot sit on the Pi side of it. Putting the plug on
the 1-wire side gets the converter live from day one and makes the disconnect the more useful
one: pulling it isolates the whole field network — every probe, every metre of mechanical-room
cable — from the Pi stack in one motion, and unplugging a 1-wire bus is clean (the kernel
keeps polling; the module logs a sensor-count change and recovers when it returns).

**Why a chain and not a star.** Every open-ended cable branch reflects the signal's edges
back at a delay set by its length. Four short branches kept the echoes clear of the moment
the master reads the line; eight put them on top of it. A chain has one line, one far end,
one echo. This is what took the bus from four healthy sensors to zero on 2026-08-22 — the
kernel log signature is `w1_search: max_slave_count 64 reached` followed by a count of 0
(phantom devices from corrupted address-search bits, not 64 sensors). The failure is silent
in pivac: the service stays `active`, only the freshness alerts report it.

**Distributed blocks are a chain; clustered blocks are a star.** All ports of a lever block
are one node, so blocks side-by-side at the Pi leave every probe lead a full-length branch.
One block *at each sensor*, trunk block to block, probe leads trimmed short — that is the
chain, and more serviceable than splices.

**The pull-up arithmetic, kept for diagnosis.** On `w1-gpio` the line rises through the
pull-up alone, and the master samples ~15 µs in, leaving ~9 µs of rise budget (~1.2 RC time
constants). Measured DQ–GND capacitance against that budget:

| Measured | 4.7 kΩ | 2.2 kΩ |
|---|---|---|
| 500 pF | 2.8 µs | 1.3 µs |
| 1.5 nF (this bus, measured) | 8.5 µs — marginal | 4.0 µs |
| 3 nF | 17 µs — fails | 7.9 µs — marginal |

The DS2482's driven edge removes the row entirely — and is why the discrete pull-up comes
off (the part has its own weak + active pull-up; an external resistor fights the active one),
and why no series damping resistor belongs in front of it either.

**Cable: pairing matters, category doesn't.** CAT5e and CAT6 both run ~50 pF/m; 1-wire at
~15 kbps cares only about capacitance and which conductor is DATA's neighbour. Jacketed
3-conductor (thermostat wire style) puts DATA between VCC and GND at ~112 pF/m — 2.2× worse —
which is what the 45.5 ft bus inventory closed on. Shielded cable trades pickup rejection for
added capacitance: plain UTP first; shielded only for intermittent CRC errors, drain grounded
at the board end only.

**Voltages must match end to end.** The probes run at 3.3 V, so DATA's high level must be
3.3 V — the DS18B20's limit is VDD + 0.3 V. The DS2482 powered from the Pi's 3.3 V keeps
that automatic. Moving the bus to 5 V (native 1-wire, more noise margin) is possible with the
bridge but means moving probe VCC to 5 V at the same time; never mix the rails. (The Arduino
bench rig runs 5 V throughout — correct there, wrong here.)

**The outdoor run gets its own bus when it returns.** A second DS2482 at address `0x19`
(AD0 high) in the same I²C link gives the outdoor cable — the longest and most exposed on the
system — a master of its own, so a fault out there cannot blank the mechanical-room probes.
H1 is reserved for it; sensors from every master appear flat under `/sys/bus/w1/devices/`,
so pivac needs nothing. Sequence it last, after the chain is proven, with spare calibrated
probes PA4/PA5 (offsets in `docs/ds18b20-PA1-5-calibration.md`). When it returns,
`environment.outside.temperature` gets a freshness rule under a **new UID** — its old UID
sits permanently in `sensor-freshness.yaml`'s `deleteRules:` block and cannot be revived.
`sentry-outdoor-divergence` needs no change.

**DS2484 and commercial boards.** The DS2484 adds tunable timing but the stock driver only
exposes `active_pullup`/`extra_config`, so the tuning is unreachable — the DS2482-100 is the
right part. Off-the-shelf alternatives if hand-soldering the SOIC ever annoys: AB Electronics
1 Wire Pi Plus, Sheepwalk RPI3. Fit ESD protection on the 1-wire port if the build lacks it —
a mechanical-room run is an antenna and the DS2482 is all that stands before the Pi.

**Per-branch damping resistors** (100 Ω in each branch's DATA at a hub, Maxim AN148) are the
mitigation for a star that cannot be re-cabled. A chain does not want them, and neither does
the DS2482's driven edge. Recorded so the option stays a decision, not a discovery.
