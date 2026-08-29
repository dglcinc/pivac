# Raspberry Pi I/O Board — Relay Monitoring Inputs

**Status:** Design, for the rebuild of the RPI-BC interface board. · **Owner:** David

Covers the relay-monitoring input stage on the Phoenix Contact **RPI-BC INT-PCB SET**
(Mouser 651-2202994) inside the RPI-BC DIN housing: how many channels the terminals allow, why
the inputs are optoisolated rather than resistor-conditioned, the circuit, and the GPIO map.

Covers the 24 V supply for the input stage in §3.1 and the board side of the DS2482 1-wire
bridge in §8. The 1-wire bus itself, including the DS2482 procedure, is a separate document,
`docs/ds18b20-bus-topology.md`.

---

## 1. What sets the channel count

Four 4-position PTSM connectors give sixteen positions. One per connector carries that group's
field common, leaving **12 monitored channels** — seven in service and five spare.

**A single shared common would give fifteen channels and is the wrong trade.** These are pluggable
connectors, so putting the only common on one of them means unplugging that connector disables
every channel on the board, including the eleven wired elsewhere. Servicing one group would take
the whole thing down. A shared return also converges every channel's current on one contact, so a
degrading connection there presents as all fifteen channels misbehaving at once, which is a far
harder fault to chase than three going dead together.

Five spare against seven in service already covers the known expansion — restoring the leak-pan
input displaced by `CHIL`, and a stage-2 `Y2` sense for the master bedroom. Three more channels
bought at the cost of unpluggability is not worth it.

Electrically either choice is fine; a group's three LEDs draw about 15 mA through a contact rated
4 A. The argument is entirely about service and diagnosis.

The Pi could carry 21 inputs, so the terminals still bind first. A later expansion is a connector
problem, never a pin problem.

## 2. Why optoisolation rather than a resistor network

**GPIO 26 is dead** — the pad is shorted to ground and cannot be driven high even as an output,
diagnosed 2026-07-01 and attributed to the 2026-06-23 power event. That is the failure mode this
stage has to stop, and no arrangement of pull-ups prevents it. A rebuild is the moment to fix it.

A resistor-only input also forces a choice with no good answer. The series resistor that limits
fault current and the pull-up that sets the idle level form a divider, so they cannot both be
1 kΩ: a closed contact would sit at 1.65 V against an input-low threshold near 0.8–1.0 V and the
channel would read permanently high. Sizing them correctly, at roughly ten to one, then trades
away the other property that matters.

| Arrangement | Closed level | Wetting current | Survives a field fault |
|---|---|---|---|
| 1 kΩ series, internal ~50 kΩ pull-up | 65 mV | 65 µA — too low | limits to ~24 mA at 24 V |
| 1 kΩ pull-up, no series | 0 V | 3.3 mA | no |
| 1 kΩ series, 10 kΩ pull-up | 0.3 V | 0.3 mA — marginal | yes |
| **Optocoupler** | **~0.2 V** | **4.8 mA** | **yes, absolutely** |

Wetting current is the quiet one. Dry contacts that only ever pass tens of microamps grow oxide
films and begin reading intermittently, which presents as a failing sensor rather than as a wiring
choice made years earlier.

Isolation also removes the shared ground between the Pi and the control panel, so no field wiring
can raise the Pi's reference.

## 3. The circuit

One channel, repeated twelve times. The optocoupler replaces the GPIO-side resistors entirely; the
only resistor left is on the field side, setting LED current.

```
   FIELD SIDE (isolated)                 |            PI SIDE
                                         |
  +24 VDC ──[ 4.7 kΩ ]──┐                |          3.3 V
                        │                |            │
                     ┌──┴──┐             |      [ internal ~50 kΩ pull-up ]
                     │  ▼  │  LED        |            │
                     │ ─┴─ │             |            ├──────────────► GPIO
                     └──┬──┘             |            │
                        │                |          ┌─┴─┐
             CDP relay ─┴─ contact       |          │ ／│  phototransistor
                        │                |          └─┬─┘
  24 V common ──────────┘                |            │
                                         |          Pi GND
        connector pin 4                  |
```

Relay closed → LED lit → phototransistor conducts → GPIO reads LOW.

**Polarity already matches.** `pivac/GPIO.py` computes
`presult = GPIO.input(pin) == (pullmode == "pulldown")`, so under the configured
`pullmode: "pullup"` a LOW pin reports as active. No `config.yml` change, and no InfluxDB
measurement is orphaned.

**The Pi-side pull-up can stay internal.** The phototransistor sinks milliamps against the roughly
66 µA the internal pull-up sources, and the GPIO node is now a short trace rather than a long field
wire, so the weak pull-up's noise susceptibility no longer applies. An external 10 kΩ and a 100 nF
to ground are optional belt-and-braces.

**Connector pin 4 is the 24 V common, not Pi ground.** Bonding it to Pi ground destroys the
isolation this stage exists for. Label it `24V COM`, never `GND`.

### 3.1 Powering the input stage

The panel's 24 V is **AC**, from the same transformer that energises the relay coils, and that
decides the supply question. The LTV-847's LED reverse-breaks down near 5–6 V, so 24 VAC puts
about 34 V peak across it on every negative half-cycle and a bare quad optocoupler fails quickly.

**Rectify the existing 24 VAC at the board.** One bridge rectifier and one smoothing capacitor at
the 24 V input serve all twelve channels — two passive components on the same perfboard as the
optocouplers, claiming no DIN slot and adding no device that can fail. Rectified 24 VAC smooths to
roughly 32.5 V, so keep 4.7 kΩ but specify it **1/2 W**: it then passes 6.7 mA and dissipates
0.21 W, and the extra current is useful wetting current.

The capacitor is not optional. Unsmoothed, the LEDs go dark near each zero crossing and
`pivac.GPIO` samples instantaneously, so channels would read inactive at random. Size it for all
twelve channels closed — 80 mA held through a ~2 ms trough within 5 V of ripple wants about 32 µF,
so **100 µF at 50 V** is comfortable.

Do not fit per-channel AC-input optocouplers instead. They chop at line frequency, which puts the
same sampling problem back on every channel and needs an RC filter on each to fix.

**A separate DIN-rail 24 VDC supply is the alternative**, and it buys one thing: it decouples
monitoring from control power. Sharing the coil transformer means a control-power failure also
removes the ability to report it — every channel reads inactive, indistinguishable from an idle
system. That ambiguity is narrow in practice, because the boiler and chiller stop running, loop
temperatures drift, and `CHIL` never asserts on a hot day, all of which are already alerted on. The
load is 58 mA, about 1.4 W, so any supply is oversized; on a regulated 24.0 V the resistor goes
back to 4.7 kΩ at 1/4 W and 4.85 mA.

**Feed 24 V once, at the board.** The resistor and the LED are board-mounted, so no supply
conductor goes out to the relays. Field wiring keeps the topology it already has: one conductor per
channel from the board to that relay's N/O pole, and one common daisy-chained along the string.
Only the common changes character — it is now the transformer common returning to connector pin 4,
where today it is Pi board ground.

The four group commons do not need four runs back to the transformer. They need to be four
separate conductors *from board to field*, so unplugging J2 cannot disturb J1; at the panel end
they all land on one bus. **A Phoenix Contact ST 1,5 QUATTRO is four internally bridged
positions**, so one block carries the transformer feed plus three group commons, and a second
bridged to it takes the fourth with three positions spare. That is one additional feed-through,
not four.

Two failure modes follow from the change. A channel conductor shorted to the 24 V common lights
that LED and reads permanently **active** — a false "on" rather than a false "off", which is the
safer direction for a monitoring input but worth labelling for. And a channel conductor shorted to
chassis or to Pi ground now does nothing at all, which is the entire point of the stage.

## 4. Parts

| Item | Part | Notes |
|---|---|---|
| Optocoupler | **LTV-847** (or PC847), quad, DIP-16 | 3 packages cover 12 channels. Through-hole, suits perfboard. `LTV-817`/`PC817` DIP-4 if singles are preferred. |
| LED resistor | 4.7 kΩ, 1/4 W, 1% metal film | one per channel |
| Optional filter | 100 nF ceramic, GPIO to Pi GND | noise and contact bounce |
| Bridge rectifier | **DB107**, DIP-4 through hole, 1 A / 1000 V | one, at the 24 V input — see §3.1 |
| Smoothing capacitor | **100 µF, 50 V** radial electrolytic, 105 °C | one, across the rectified feed |

Channel-to-channel isolation inside the quad package is absent, which is fine here because every
channel already shares the same 24 V common. Only the field-to-Pi barrier matters.

Sizing, at 24 VDC with an LED forward drop near 1.2 V:

- On rectified 24 VAC (~32.5 V), 4.7 kΩ → **6.7 mA**, dissipating 0.21 W, so a **1/2 W** part.
- On a regulated 24 VDC supply, 4.7 kΩ → **4.85 mA**, dissipating 0.11 W, comfortable in 1/4 W.
- At a worst-case current transfer ratio of 50 %, collector current is about 2.4 mA against the
  66 µA the pull-up needs — roughly 36× margin, so saturation is not in question.
- Running the LED near 5 mA rather than 20 mA also slows the LED ageing that erodes transfer ratio
  over a decade of continuous duty.
- For more wetting current use 2.2 kΩ, which gives 10.4 mA but dissipates 0.24 W and therefore
  needs a **1/2 W** resistor.

**If any input is live 24 VAC rather than a dry contact**, that channel needs a bridge rectifier
ahead of the LED, or an AC-input optocoupler such as the **LTV-814** whose bidirectional LED
accepts either polarity. An AC-input part chops at line frequency, so filter it or let the poll
interval average it. The CDP relays provide dry contacts, so this applies only if the scheme
changes.

## 5. GPIO map

Reserved and unavailable: **GPIO 2 and 3**, spent on the DS2482's I²C (§8), **GPIO 0 and 1** (pins 27/28) for
the HAT ID EEPROM, **GPIO 26 dead permanently**, and **GPIO 14/15 kept as a serial console** —
the recovery path on a headless DIN-mounted Pi when the network drops, which has happened here.
**GPIO 4 is deliberately left unassigned**, even though the DS2482 frees it. Rollback to
`w1-gpio` needs the pin, so a relay channel there would make this board depend on the migration
succeeding. Leaving it out keeps the board correct in both states; promote it to a spare only
once the bridge has run through a heating season.

`dtparam=spi=off` and the commented-out I²S line leave BCM 7–11 and 18–21 as plain GPIO. Leave
both settings alone.

The seven existing channels keep their pins, so no field wiring moves and no measurement history
is orphaned. Channels are grouped by what they watch rather than by pin order, so a connector can
be unplugged without splitting a system.

| Connector | Pin 1 | Pin 2 | Pin 3 | Pin 4 |
|---|---|---|---|---|
| **J1** — boiler / DHW | `ZV` — BCM 17 | `DHW` — BCM 27 | `BLR` — BCM 22 | **24 V COM** |
| **J2** — cooling | `CHIL` — BCM 25 | `BOS1` — BCM 6 | `BOS2` — BCM 5 | **24 V COM** |
| **J3** — mixed | `DEHUM` — BCM 12 | spare — BCM 23 | spare — BCM 24 | **24 V COM** |
| **J4** — expansion | spare — BCM 18 | spare — BCM 13 | spare — BCM 19 | **24 V COM** |

J2 puts the three cooling sources together, matching the zone-to-source map in
`docs/cdp-chiller-rework-plan.md` §3, so a cooling question is answered from one connector.

**BCM 7–11 are left entirely unspent.** That is the SPI block, and keeping it contiguous means SPI
can be enabled later for an ADC or a display without disturbing a relay channel. BCM 19 was the
cancelled YOFF rewire and is free; its `config.yml` entry stays commented out.

## 6. Build notes

The durability rules are the same as the 1-wire enclosure work in
`docs/ds18b20-bus-topology.md` §6.2: ferrules on stranded conductors, strain relief at the
housing entry, no mid-air solder joints, and every channel labelled with the name it publishes
under so the board matches `docs/PhoenixContact-BC-RPI-label.docx`.

**Check the wire gauge against the terminals.** PTSM 0,5 accepts **24–20 AWG**, 0.5 mm² nominal.
18 AWG is 0.82 mm² and will not land in them, so any 18 AWG field run has to transition to smaller
wire before the board.

**Vestigial line to remove with this build.** `pivac/GPIO.py:17` runs
`os.system('modprobe w1-gpio')` at import, a leftover from when the GPIO and 1-wire modules shared
setup. It is harmless — without the device-tree overlay the module instantiates no master — but it
is actively misleading once the DS2482 owns the bus, so it goes when §8 lands.

## 7. The extension board, and why relay wiring stays off it

The **RPI-BC EXT-PCB HBUS SET** (Mouser 651-2202995) in the adjacent housing carries the 1-wire
bus on 3-position headers, and it can host GPIO channels beyond the twelve here. Do that only if
twelve is genuinely exhausted.

**Keep switched 24 V field wiring away from the 1-wire bus.** DQ is a slow open-drain line with a
passive pull-up and no differential rejection, and it is the bus that has already collapsed once.
Relay field wiring switches inductive loads, so bundling the two out of the same housing invites
exactly the pickup the twisted-pair guidance in `docs/ds18b20-bus-topology.md` §5 exists to
prevent. Optoisolation protects the *Pi*; it does nothing about two cables sharing a tray.

If the extension board does take relay channels, put them at the opposite end from the 1-wire
headers and bring their field wiring out of a separate entry. The DS2482, its pull-up and its
decoupling want that board space anyway, and they belong beside the 1-wire terminals rather than
across the housing from them.

Twelve channels against seven in service, with the leak-pan input and a `Y2` sense as the known
additions, means this should not come up. Recorded so the option is a decision rather than a
discovery.

## 8. The DS2482 1-wire bridge belongs in this rebuild

The parts are on hand, and fitting the bridge during the board rebuild buys one round of downtime
instead of two. The full procedure — enabling I²C, instantiating over sysfs, pinning it with a
systemd unit, and rollback — is `docs/ds18b20-bus-topology.md` §7. What follows is only what the
board build has to get right.

**Mount it at the Pi, inside this housing.** I²C is a short-range bus and must never carry the
mechanical-room run; the long cable stays on the 1-Wire side, which is the whole reason for the
part. Tie AD0 and AD1 to GND for address `0x18`.

| DS2482 pin | Goes to |
|---|---|
| VDD | 3.3 V, physical pin 1 |
| GND | physical pin 9 |
| SDA | GPIO 2, physical pin 3 |
| SCL | GPIO 3, physical pin 5 |
| IO | trunk DQ |

**Two things come off the board when it goes in.** The discrete **2.2 kΩ** 1-Wire pull-up — the
DS2482 supplies its own weak pull-up plus an active one, and an external resistor fights both —
and any driver-side series damping resistor, whose only job is softening a weakly driven edge and
which therefore works against the part's sole contribution. Per-branch damping at a distribution
block would survive a master swap, but this bus is a chain and wants none.

**Keep the DQ rail at 3.3 V.** `w1-gpio` pinned that for you because GPIO 4 is not 5 V tolerant;
the bridge does not, and a master driving DQ to 5 V into probes powered from 3.3 V exceeds their
VDD + 0.3 V absolute maximum. The 1-Wire side *can* move to 5 V for noise margin once the Pi only
ever sees I²C, but the probes' VDD has to move at the same time. Do not mix the rails.

**GPIO 4 still stays unassigned**, even though the bridge frees it. Rollback to `w1-gpio` needs it,
and a relay channel sitting on that pin would make this board depend on the migration succeeding.
Promote it to a spare only once the bridge has run through a heating season.

**This is the section §7's warning is really about.** The 24 V feed of §3.1 is new switched wiring
entering the same enclosure as a slow open-drain line with a passive pull-up and no differential
rejection — the bus that has already collapsed once. Optoisolation protects the *Pi*; it does
nothing about two cables sharing a tray. Bring the 24 V and the relay field wiring in through a
separate entry from the 1-wire trunk, and put the DS2482 and its decoupling beside the 1-wire
terminals rather than across the housing from them.
